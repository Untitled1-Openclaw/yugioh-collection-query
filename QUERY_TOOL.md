# Query Tool Reference

`query_collection.py` is a stdlib-only, read-only CLI for querying an OpenYugi collection, card database, deck directory, and movement history.

## Purpose

The tool is built for local analysis and automation:

- human-readable output by default
- JSON output for scripts, agents, and downstream processing
- read-only access to OpenYugi data sources
- no external Python dependencies

## Default Data Sources

Unless overridden, the tool reads:

- collection: `/home/username1/Yu-Gi-Oh-Card-Tracker/data/collections/Main.json`
- card database: `/home/username1/Yu-Gi-Oh-Card-Tracker/data/db/card_db.json`
- decks: `/home/username1/Yu-Gi-Oh-Card-Tracker/data/decks/`
- transactions: `/home/username1/Yu-Gi-Oh-Card-Tracker/data/transactions/`
- fallback movement history: `/home/username1/Yu-Gi-Oh-Card-Tracker/data/changelogs/`

It does not modify tracker files.

## Global Syntax

```bash
python3 query_collection.py [global-options] <command> [command-options]
```

### Global Options

| Option | Description |
| --- | --- |
| `--collection PATH` | Path to the collection JSON file |
| `--card-db PATH` | Path to `card_db.json` |
| `--transactions PATH` | Path to a transactions directory or file; changelogs are used as fallback when the default transaction path is missing |
| `--decks-dir PATH` | Path to a deck directory or `.ydk` file |
| `--json` | Emit JSON instead of text |

## Commands

### `summary`

Shows collection totals and grouped statistics for the currently matched records.

Common uses:

- get total copies and entry counts
- inspect counts by rarity, language, condition, edition, and set code
- narrow the summary with the standard filter set

Example:

```bash
python3 query_collection.py summary
python3 query_collection.py summary --language DE
```

### `cards`

Aggregates the collection to one row per owned card name.

Output includes:

- total quantity
- card ID and resolved card ID
- variant count
- set codes
- owned rarities
- languages
- conditions

Example:

```bash
python3 query_collection.py cards --name "Blue-Eyes" --limit 10
```

### `entries`

Lists raw inventory rows for precise variant-level inspection.

Use this when you need exact entry data such as:

- set code
- rarity
- storage location
- purchase metadata
- edition and language per entry

Example:

```bash
python3 query_collection.py entries --set-code RA02-EN072 --limit 10
```

### `resolve`

Maps collection cards to the canonical records in `card_db.json`.

Useful for:

- verifying database resolution
- confirming canonical IDs
- preparing structured outputs for other tools

Example:

```bash
python3 query_collection.py resolve --name "Pot of Extravagance"
python3 query_collection.py resolve --quantity 3 --limit 10 --json
```

### `details`

Joins owned cards with card database metadata.

Output can include:

- effect text
- monster type, attribute, race, level, ATK, and DEF
- archetype
- owned set codes and rarities
- market price fields when present

Example:

```bash
python3 query_collection.py details --name "Dark Magician"
python3 query_collection.py details --quantity 3 --limit 5
```

### `movements`

Lists matching movement records from transactions or changelog files.

The tool scans recursively and handles JSON, NDJSON, and `.log` files that contain JSON records.

Example:

```bash
python3 query_collection.py movements --limit 10
python3 query_collection.py movements --name "Traptrix Mantis" --action ADD REMOVE
```

### `movement-summary`

Builds a summary view over matching movement records.

Summary includes:

- total movement count
- latest timestamp
- actions breakdown
- top cards
- source files

Example:

```bash
python3 query_collection.py movement-summary --source scan_temp.log
```

### `decks`

Lists available `.ydk` decks from the configured deck directory.

Example:

```bash
python3 query_collection.py decks --limit 20
```

### `deck`

Inspects a specific `.ydk` deck and compares it against owned copies in the collection.

Behavior:

- accepts a deck name or filename
- prefers exact case-insensitive deck name matches
- falls back to unique substring matches
- resolves alternate-art image IDs back to base card IDs using `card_db.json`
- reports missing owned copies for required cards

Example:

```bash
python3 query_collection.py deck "Purrely"
python3 query_collection.py deck "ABC 2017 (1).ydk" --json
```

## Standard Filters

These filters apply to `summary`, `cards`, `entries`, `resolve`, `details`, `movements`, and `movement-summary` unless noted otherwise.

| Option | Description |
| --- | --- |
| `--name TEXT` | Filter by card name |
| `--card-id INT` | Filter by card ID |
| `--set-code TEXT` | Filter by set code |
| `--rarity TEXT` | Filter by rarity |
| `--condition TEXT` | Filter by condition |
| `--language TEXT` | Filter by language |
| `--storage-location TEXT` | Filter by storage location |
| `--first-edition true|false` | Filter by first edition status |
| `--exact` | Use exact matching instead of case-insensitive substring matching |

### Quantity Filters

Available on `resolve` and `details`:

| Option | Description |
| --- | --- |
| `--quantity INT` | Exact owned quantity |
| `--min-quantity INT` | Minimum owned quantity |
| `--max-quantity INT` | Maximum owned quantity |

### Movement-Specific Filters

Available on `movements` and `movement-summary`:

| Option | Description |
| --- | --- |
| `--action ADD REMOVE UPDATE BATCH` | Filter by one or more action types |
| `--source TEXT` | Filter by source file name or path |

### Deck-Specific Input

`deck` takes one required positional argument:

| Argument | Description |
| --- | --- |
| `deck_name` | Deck name or `.ydk` filename to inspect |

## Matching Behavior

- Text filters are case-insensitive substring matches by default.
- `--exact` changes text filters to exact case-insensitive matching.
- `--first-edition` accepts `true`, `false`, `yes`, `no`, `1`, `0`, `1st`, and `unlimited`.

## JSON Output

Every command supports JSON output with `--json`.

Examples:

```bash
python3 query_collection.py summary --json
python3 query_collection.py resolve --name "Blue-Eyes" --json
python3 query_collection.py deck "Purrely" --json
```

## Representative Examples

```bash
python3 query_collection.py summary
python3 query_collection.py cards --limit 20
python3 query_collection.py entries --set-code RA02-EN072 --limit 10
python3 query_collection.py details --quantity 3 --limit 5
python3 query_collection.py decks --limit 10
python3 query_collection.py movements --limit 5
```

## OpenYugi Notes

- This repository is intended to sit alongside an OpenYugi installation.
- The CLI assumes the tracker data model and directory structure used by OpenYugi.
- If your local paths differ, pass explicit overrides with the global flags.

OpenYugi repository:

- <https://github.com/DJ-Cat-N-Cheese/Yu-Gi-Oh-Card-Tracker>
