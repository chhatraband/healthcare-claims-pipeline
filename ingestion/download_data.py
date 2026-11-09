"""Phase 1: download CMS DE-SynPUF Sample 1 files, unzip them, and write an answer key."""
import csv
import zipfile
from decimal import Decimal
from pathlib import Path

import requests

# ---------- WHERE THE FILES ARE ----------
BASE = ("https://www.cms.gov/research-statistics-data-and-systems/"
        "downloadable-public-use-files/synpufs/downloads/")

FILES = {
    "beneficiary_2008": BASE + "de1_0_2008_beneficiary_summary_file_sample_1.zip",
    "beneficiary_2009": BASE + "de1_0_2009_beneficiary_summary_file_sample_1.zip",
    # beneficiary_2010 is NOT available for Sample 1: the CMS page links to a Sample 20 file
    # by mistake, and the Sample 1 address returns 404 (checked Nov 2026).
    # Decision: member-based KPIs (PMPM, admits per 1,000) use 2008-2009 only.
    "inpatient":        BASE + "de1_0_2008_to_2010_inpatient_claims_sample_1.zip",
    "outpatient":       BASE + "de1_0_2008_to_2010_outpatient_claims_sample_1.zip",
}

# ---------- WHERE THEY GO ON THE LAPTOP ----------
RAW = Path("data/raw")
ZIPS = RAW / "zips"
CSVS = RAW / "csv"
HEADERS = {"User-Agent": "Mozilla/5.0 (learning project: healthcare-claims-pipeline)"}


# ---------- STEP A: DOWNLOAD ONE FILE ----------
def download(name, url):
    target = ZIPS / f"{name}.zip"
    if target.exists():                                   # already have it -> skip
        print(f"  skip   {name} (already downloaded)")
        return target

    print(f"  get    {name} ...")
    response = requests.get(url, headers=HEADERS, timeout=300)
    response.raise_for_status()                           # stop on 404, 403, ...
    if not response.content.startswith(b"PK"):            # every zip file starts with "PK"
        raise ValueError("the server did not return a zip file - check the URL")

    target.write_bytes(response.content)
    print(f"         {len(response.content) / 1_000_000:.1f} MB")
    return target


# ---------- STEP B: UNZIP ONE FILE ----------
def unzip(name, zip_path):
    out_dir = CSVS / name
    if not any(out_dir.glob("*.csv")):                    # not unzipped yet
        out_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path) as z:
            z.extractall(out_dir)

    csv_files = list(out_dir.glob("*.csv"))
    if len(csv_files) != 1:
        raise ValueError(f"expected 1 CSV inside the zip, found {len(csv_files)}")
    return csv_files[0]


# ---------- STEP C: COUNT WHAT'S INSIDE ----------
def profile(name, csv_path):
    rows = 0
    members = set()
    claims = set()
    claim_segments = set()
    paid = Decimal("0")
    first_date = None
    last_date = None

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)                        # each row becomes a dict by column name
        columns = reader.fieldnames
        for row in reader:
            rows += 1
            members.add(row["DESYNPUF_ID"])               # the member ID in every file
            if "CLM_ID" in row:                           # only claims files have CLM_ID
                claims.add(row["CLM_ID"])
                claim_segments.add((row["CLM_ID"], row.get("SEGMENT", "")))
                paid += Decimal(row["CLM_PMT_AMT"] or "0")
                d = row["CLM_FROM_DT"]
                if d:
                    if first_date is None or d < first_date:
                        first_date = d
                    if last_date is None or d > last_date:
                        last_date = d

    (csv_path.parent / "columns.txt").write_text("\n".join(columns), encoding="utf-8")

    lines = [
        f"[{name}]",
        f"  file:                     {csv_path.name}",
        f"  columns:                  {len(columns)}",
        f"  rows:                     {rows:,}",
        f"  unique members:           {len(members):,}",
    ]
    if claims:
        lines += [
            f"  unique CLM_ID:            {len(claims):,}",
            f"  unique CLM_ID + SEGMENT:  {len(claim_segments):,}",
            f"  total CLM_PMT_AMT:        ${paid:,.2f}",
            f"  CLM_FROM_DT range:        {first_date} to {last_date}",
        ]
    return lines


# ---------- RUN EVERYTHING ----------
def main():
    ZIPS.mkdir(parents=True, exist_ok=True)
    CSVS.mkdir(parents=True, exist_ok=True)

    report = ["========== CLAIMS ANSWER KEY ==========",
              "Source: CMS DE-SynPUF Sample 1 (synthetic Medicare data)", ""]
    failed = []

    for name, url in FILES.items():
        try:
            zip_path = download(name, url)
            csv_path = unzip(name, zip_path)
            print(f"  count  {name} ...")
            report += profile(name, csv_path) + [""]
        except Exception as e:                            # one failure doesn't stop the rest
            print(f"  FAILED {name}: {e}")
            failed.append(name)

    text = "\n".join(report)
    print("\n" + text)
    (RAW / "answer_key.txt").write_text(text, encoding="utf-8")

    if failed:
        print("FAILED:", ", ".join(failed))


if __name__ == "__main__":
    main()