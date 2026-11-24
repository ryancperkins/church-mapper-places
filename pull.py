#!/usr/bin/env python3
"""Pull every religious place in the United States from Overture Maps, one
gzipped CSV per state, plus a manifest.

Reads Overture's public bucket with DuckDB. No account, no key. The newest
release is found by listing the bucket, or name one.

    python3 -m pip install duckdb
    python3 pull.py --release latest --out data

Writes data/<release>/churches-<st>.csv.gz for every state and DC, a
manifest.json with row counts and checksums, a NOTICE with the licenses, and
data/RELEASE holding the release name, which the workflow uses as the tag.
"""
import argparse
import csv
import gzip
import hashlib
import json
import pathlib
import re
import sys
import time
import urllib.request
from datetime import datetime, timezone

try:
    import duckdb
except ImportError:
    sys.exit("duckdb is needed: python3 -m pip install duckdb")

BUCKET = "overturemaps-us-west-2"
LISTING = f"https://{BUCKET}.s3.us-west-2.amazonaws.com/?list-type=2&prefix=release/&delimiter=/"
STATES = (
    "AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY"
).split()
COLUMNS = ["id", "name", "hierarchy", "street", "locality", "region", "postcode", "lon", "lat", "confidence", "source"]


def latest_release():
    with urllib.request.urlopen(LISTING, timeout=60) as r:
        xml = r.read().decode("utf-8")
    names = re.findall(r"<Prefix>release/([^<]+)/</Prefix>", xml)
    names = [n for n in names if re.match(r"^\d{4}-\d{2}-\d{2}\.\d+$", n)]
    if not names:
        sys.exit("no releases found in the bucket listing")
    return max(names)


def pull(release, out):
    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs; SET s3_region='us-west-2';")
    src = f"s3://{BUCKET}/release/{release}/theme=places/type=place/*"
    regions = ", ".join(f"'US-{s}'" for s in STATES)
    t0 = time.time()
    rows = con.execute(f"""
        SELECT id, names.primary AS name,
               array_to_string(taxonomy.hierarchy, '>') AS hierarchy,
               addresses[1].freeform AS street, addresses[1].locality AS locality,
               addresses[1].region AS region, addresses[1].postcode AS postcode,
               bbox.xmin AS lon, bbox.ymin AS lat, confidence,
               sources[1].dataset AS source
        FROM read_parquet('{src}', filename=true, hive_partitioning=1)
        WHERE bbox.xmin BETWEEN -180 AND -64 AND bbox.ymin BETWEEN 17 AND 72
          AND (list_contains(taxonomy.hierarchy, 'place_of_worship')
               OR list_contains(taxonomy.hierarchy, 'religious_organization')
               OR list_contains(taxonomy.hierarchy, 'church')
               OR list_contains(taxonomy.hierarchy, 'church_cathedral'))
          AND addresses[1].region IN ({regions})
    """).fetchall()
    print(f"pulled {len(rows)} rows in {time.time() - t0:.0f}s", flush=True)
    by_state = {}
    for r in rows:
        by_state.setdefault(r[5][-2:].lower(), []).append(r)
    folder = pathlib.Path(out) / release
    folder.mkdir(parents=True, exist_ok=True)
    manifest = {
        "release": release,
        "source": "Overture Maps Foundation, places theme",
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "columns": COLUMNS,
        "states": {},
    }
    for st in sorted(by_state):
        path = folder / f"churches-{st}.csv.gz"
        with gzip.open(path, "wt", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(COLUMNS)
            w.writerows(sorted(by_state[st], key=lambda r: (str(r[4] or ""), str(r[1] or ""))))
        manifest["states"][st] = {
            "file": path.name,
            "rows": len(by_state[st]),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    (folder / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (folder / "NOTICE").write_text(pathlib.Path(__file__).with_name("NOTICE").read_text().replace("{release}", release))
    (pathlib.Path(out) / "RELEASE").write_text(release + "\n")
    print(f"wrote {len(by_state)} state files to {folder}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--release", default="latest")
    ap.add_argument("--out", default="data")
    a = ap.parse_args()
    release = latest_release() if a.release == "latest" else a.release
    print("release", release, flush=True)
    pull(release, a.out)


if __name__ == "__main__":
    main()
