"""Phase 2: upload the raw CMS CSV files to S3 (the landing zone)."""
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

# ---------- SETTINGS ----------
PROFILE = "claims"                              # the limited IAM user from Phase 0
REGION = "us-east-2"
BUCKET = "chhatraband-claims-pipeline"
CSVS = Path("data/raw/csv")

# local folder  ->  S3 folder (called a "prefix" in S3)
DESTINATIONS = {
    "beneficiary_2008": "raw/beneficiary/year=2008/",
    "beneficiary_2009": "raw/beneficiary/year=2009/",
    "inpatient":        "raw/inpatient/",
    "outpatient":       "raw/outpatient/",
}


# ---------- IS THIS FILE ALREADY IN S3? ----------
def already_uploaded(s3, key, size):
    try:
        head = s3.head_object(Bucket=BUCKET, Key=key)     # ask S3 about the file, without downloading it
    except ClientError as e:
        if e.response["Error"]["Code"] in ("404", "NoSuchKey", "NotFound"):
            return False                                 # not there yet
        raise                                            # any other error: stop and show it
    return head["ContentLength"] == size                 # same size = same file


# ---------- UPLOAD EVERYTHING ----------
def main():
    session = boto3.Session(profile_name=PROFILE, region_name=REGION)
    s3 = session.client("s3")

    uploaded = 0
    for folder, prefix in DESTINATIONS.items():
        csv_path = next((CSVS / folder).glob("*.csv"))   # the one CSV in that folder
        key = prefix + csv_path.name                     # full path inside the bucket
        size = csv_path.stat().st_size

        if already_uploaded(s3, key, size):
            print(f"  skip    s3://{BUCKET}/{key}")
            continue

        print(f"  upload  {csv_path.name} ({size / 1_000_000:.1f} MB)")
        s3.upload_file(str(csv_path), BUCKET, key)       # big files are split into parts automatically
        uploaded += 1

    print(f"\nUploaded {uploaded} new file(s).\n")
    print(f"Now in s3://{BUCKET}/raw/ :")
    response = s3.list_objects_v2(Bucket=BUCKET, Prefix="raw/")
    for obj in response.get("Contents", []):
        print(f"  {obj['Size'] / 1_000_000:8.1f} MB   {obj['Key']}")


if __name__ == "__main__":
    main()

    