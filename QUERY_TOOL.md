# Collection Query Tool

`query_collection.py` is a stdlib-only, read-only CLI for querying the local collection plus OpenYugi tracker data.

It reads:

- `collections/Main.json` by default
- `/home/username1/Yu-Gi-Oh-Card-Tracker/data/db/card_db.json`
- `/home/username1/Yu-Gi-Oh-Card-Tracker/data/transactions/` if it exists
- fallback movement history from `/home/username1/Yu-Gi-Oh-Card-Tracker/data/changelogs/`

It never writes back to OpenYugi files.

## Typical usage

```bash
python3 query_collection.py summary
python3 query_collection.py cards --limit 20
python3 query_collection.py entries --set-code RA02-EN072
python3 query_collection.py resolve --name Purrely
python3 query_collection.py details --name "Purrely Pretty Memory"
python3 query_collection.py details --quantity 3
python3 query_collection.py movements --limit 5
python3 query_collection.py movements --name "Purrely Pretty Memory"
python3 query_collection.py movement-summary --name "Blue-Eyes"
```

## Commands

- `summary`: overall counts and grouped totals
- `cards`: cards you have with total copies per card
- `entries`: raw inventory rows, useful for precise filtering
- `resolve`: show collection cards with resolved `card_id` mapping from `card_db.json`
- `details`: join owned cards to `card_db.json` and show effect/type/stats
- `movements`: list card movements from transaction/changelog files
- `movement-summary`: summarize matching movement history

## Filters

All collection commands support:

- `--name`
- `--card-id`
- `--set-code`
- `--rarity`
- `--condition`
- `--language`
- `--storage-location`
- `--first-edition true|false`
- `--exact`

`resolve` and `details` also support owned-quantity filters:

- `--quantity`
- `--min-quantity`
- `--max-quantity`

`movements` and `movement-summary` also support:

- `--action ADD REMOVE UPDATE BATCH`
- `--source`

Default matching is case-insensitive substring matching. Add `--exact` for exact value matching.

## Unified queries

Examples that bridge the collection and card DB:

```bash
python3 query_collection.py details --quantity 3
python3 query_collection.py details --name "Blue-Eyes White Dragon"
python3 query_collection.py details --set-code RA02-EN072 --json
```

These commands let an agent answer questions like:

- "What is the effect of the card I have 3 copies of?"
- "What type is the Purrely card in my collection?"
- "Which `card_id` does this collection entry map to?"

## Movement history

The tool scans recursively and handles nested files plus mixed naming conventions, as long as files are JSON, NDJSON, or `.log` files containing JSON records.

Examples:

```bash
python3 query_collection.py movements --limit 5
python3 query_collection.py movements --name "Purrely Pretty Memory" --limit 10
python3 query_collection.py movements --card-id 29599813
python3 query_collection.py movements --action UPDATE --storage-location "Dueling Mirrors Tin #1"
python3 query_collection.py movement-summary --source Main.json.log
```

## Alternate paths

Override any default source path when needed:

```bash
python3 query_collection.py --collection /path/to/Main.json cards
python3 query_collection.py --card-db /path/to/card_db.json details --name Purrely
python3 query_collection.py --transactions /path/to/history-dir movements --limit 20
```

## Agent integration

For Yugi-Watch, call the script directly and choose output mode based on the task:

- Human answer: plain text output
- Downstream processing: add `--json`

Examples:

```bash
python3 query_collection.py summary --json
python3 query_collection.py resolve --name "Blue-Eyes" --json
python3 query_collection.py details --quantity 3 --json
python3 query_collection.py movements --name "Purrely Pretty Memory" --json
```
