# Church Mapper places

Every religious place in the United States that Overture Maps knows, one gzipped
CSV per state, published here as a GitHub release each month. Church Mapper
fetches its state's file to match a church by name and town, as a second
opinion beside the geocode of its address, so a wrong pin gets caught before
anyone sees it.

The data is open. Overture Maps Foundation publishes its places theme under
permissive licenses that vary by the source of each record; `NOTICE` lists
them and the `source` column names the source for every row. Nothing here is
from OpenStreetMap.

## Files

A release is tagged with Overture's own release name, such as `2026-11-18.0`,
and holds:

- `churches-tx.csv.gz` and one file per state and the District of Columbia,
  sorted by town then name.
- `manifest.json` with the release name, the columns, and a row count and
  SHA-256 checksum per state.
- `NOTICE`, the license notice to keep with the data.

The newest release is always at a stable address, for example
`https://github.com/ryancperkins/church-mapper-places/releases/latest/download/churches-tx.csv.gz`.

## Columns

`id` is Overture's GERS id, stable across releases. `name` is the primary
name. `hierarchy` is Overture's category path, which tells a church from a
religious organization. `street`, `locality`, `region` and `postcode` are the
first address Overture holds; `region` is an ISO code such as `US-TX`.
`lon` and `lat` are the point, in decimal degrees. `confidence` is Overture's
0 to 1 measure of whether the place exists, not of where it is, and it is not
comparable across sources. `source` is the dataset the record came from.

## How it is made

`pull.py` reads Overture's public bucket with DuckDB, no account needed, takes
the rows whose category is a place of worship or a religious organization and
whose address is in a United States state, and writes the files. The workflow
in `.github/workflows/publish.yml` runs it on the fifth of each month against
the newest Overture release and publishes the result as a release here. Run it
by hand from the Actions tab to publish sooner, or name a release:

```bash
python3 -m pip install duckdb
python3 pull.py --release latest --out data
```

## Known limits

Overture's confidence number measures existence, not position. Duplicates
happen, often a short name and a long name for the same church at the same
address. Many Methodist churches still carry "United Methodist" in their name.
Rural coverage is good but not complete; on one conference's roster of 402
churches, 334 were found by name. Treat a row as an opinion to be checked
against the address, which is what Church Mapper does.
