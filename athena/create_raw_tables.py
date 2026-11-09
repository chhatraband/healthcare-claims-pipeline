"""Phase 3: create Athena raw tables over the S3 files, then reconcile counts to the answer key."""
import time
from decimal import Decimal
from pathlib import Path

import boto3
from botocore.config import Config                       # NEW: retry and timeout settings

# ---------- SETTINGS ----------
PROFILE = "claims"
REGION = "us-east-2"
BUCKET = "chhatraband-claims-pipeline"
WORKGROUP = "primary"
DB = "claims_raw"
COLUMNS_DIR = Path("data/raw/csv")
SQL_DIR = Path("athena")

# table name -> where its columns come from, where its files live, is it partitioned?
TABLES = {
    "raw_beneficiary": {"columns_from": "beneficiary_2008", "location": "raw/beneficiary/", "partitioned": True},
    "raw_inpatient":   {"columns_from": "inpatient",        "location": "raw/inpatient/",   "partitioned": False},
    "raw_outpatient":  {"columns_from": "outpatient",       "location": "raw/outpatient/",  "partitioned": False},
}

# reconciliation: (check name, SQL, expected value from the answer key)
CHECKS = [
    ("beneficiary 2008 rows", f"SELECT COUNT(*) FROM {DB}.raw_beneficiary WHERE year = '2008'", "116352"),
    ("beneficiary 2009 rows", f"SELECT COUNT(*) FROM {DB}.raw_beneficiary WHERE year = '2009'", "114538"),
    ("inpatient rows",        f"SELECT COUNT(*) FROM {DB}.raw_inpatient",  "66773"),
    ("outpatient rows",       f"SELECT COUNT(*) FROM {DB}.raw_outpatient", "790790"),
    ("inpatient total paid",  f"SELECT SUM(TRY_CAST(clm_pmt_amt AS DECIMAL(18,2))) FROM {DB}.raw_inpatient",  "639260180.00"),
    ("outpatient total paid", f"SELECT SUM(TRY_CAST(clm_pmt_amt AS DECIMAL(18,2))) FROM {DB}.raw_outpatient", "224524710.00"),
]


# ---------- RUN ONE SQL STATEMENT AND WAIT FOR IT ----------
def run(athena, sql):
    qid = athena.start_query_execution(QueryString=sql, WorkGroup=WORKGROUP)["QueryExecutionId"]
    print("    waiting", end="", flush=True)
    while True:
        status = athena.get_query_execution(QueryExecutionId=qid)["QueryExecution"]["Status"]
        if status["State"] in ("SUCCEEDED", "FAILED", "CANCELLED"):
            break
        print(".", end="", flush=True)                    # NEW: one dot per second = still working
        time.sleep(1)
    print(f" {status['State']}")
    if status["State"] != "SUCCEEDED":
        raise RuntimeError(f"{status['State']}: {status.get('StateChangeReason')}\nSQL: {sql[:300]}")
    return qid


def scalar(athena, sql):
    """Run a query that returns one value and give back that value as text."""
    qid = run(athena, sql)
    rows = athena.get_query_results(QueryExecutionId=qid)["ResultSet"]["Rows"]
    return rows[1]["Data"][0].get("VarCharValue")        # row 0 is the header row


# ---------- BUILD THE CREATE TABLE STATEMENT FROM THE REAL HEADER ----------
def build_ddl(table, cfg):
    names = (COLUMNS_DIR / cfg["columns_from"] / "columns.txt").read_text(encoding="utf-8").split("\n")
    columns = ",\n".join(f"  `{n.strip().lower()}` STRING" for n in names if n.strip())
    partition = "PARTITIONED BY (`year` STRING)\n" if cfg["partitioned"] else ""
    return (
        f"CREATE EXTERNAL TABLE {DB}.{table} (\n{columns}\n)\n"
        f"{partition}"
        "ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.OpenCSVSerde'\n"
        "WITH SERDEPROPERTIES ('separatorChar' = ',', 'quoteChar' = '\"')\n"
        f"LOCATION 's3://{BUCKET}/{cfg['location']}'\n"
        "TBLPROPERTIES ('skip.header.line.count' = '1')"
    )


def main():
    # NEW: retry network blips up to 10 times, and never wait forever on a dead connection
    retry_config = Config(retries={"max_attempts": 10, "mode": "standard"},
                          connect_timeout=10, read_timeout=60)
    athena = boto3.Session(profile_name=PROFILE, region_name=REGION).client("athena", config=retry_config)

    print(f"Creating database {DB} ...")
    run(athena, f"CREATE DATABASE IF NOT EXISTS {DB}")

    for table, cfg in TABLES.items():
        ddl = build_ddl(table, cfg)
        (SQL_DIR / f"{table}.sql").write_text(ddl + ";\n", encoding="utf-8")   # keep the SQL in GitHub
        print(f"Creating {DB}.{table} ...")
        run(athena, f"DROP TABLE IF EXISTS {DB}.{table}")   # removes the label only, never the S3 files
        run(athena, ddl)
        if cfg["partitioned"]:
            run(athena, f"MSCK REPAIR TABLE {DB}.{table}")   # finds the year=2008 / year=2009 folders

    print("\nReconciling with the answer key:")
    all_ok = True
    for name, sql, expected in CHECKS:
        actual = scalar(athena, sql)
        ok = actual is not None and Decimal(actual) == Decimal(expected)
        all_ok = all_ok and ok
        print(f"  {'OK  ' if ok else 'FAIL'}  {name:24} expected {expected:>14}   got {actual}")

    print("\nALL CHECKS PASSED" if all_ok else "\nSOME CHECKS FAILED - look at the FAIL lines")


if __name__ == "__main__":
    main()