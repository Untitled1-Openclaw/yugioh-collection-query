# Yu-Gi-Oh! Collection Query Tool

<p align="center">
  <strong>Read-only CLI queries for OpenYugi collections, decks, and movement history.</strong>
</p>

<p align="center">
  Query your local Yu-Gi-Oh! collection with clean terminal output or JSON for automation.
</p>

<p align="center">
  <img alt="Python 3.10+" src="https://img.shields.io/badge/python-3.10%2B-blue.svg">
  <img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-green.svg">
  <img alt="Dependencies: stdlib only" src="https://img.shields.io/badge/dependencies-stdlib%20only-lightgrey.svg">
  <img alt="Status: Presentation Ready" src="https://img.shields.io/badge/status-presentation%20ready-brightgreen.svg">
</p>

## Overview

`query_collection.py` is a professional, stdlib-only command-line tool for exploring data from an [OpenYugi](https://github.com/DJ-Cat-N-Cheese/Yu-Gi-Oh-Card-Tracker) installation.

It is designed for:

- fast local collection lookups
- deck inspection from `.ydk` files
- card database joins for names, effects, stats, and IDs
- movement history queries from transactions or changelog files
- automation workflows that need structured JSON output

The tool is read-only. It never writes back to your OpenYugi data.

## Features

- Query collection summaries, cards, and raw inventory entries
- Filter by name, card ID, set code, rarity, language, condition, storage location, and edition
- Resolve collection entries against `card_db.json`
- Join owned cards to database metadata, including effect text and stats
- Inspect `.ydk` deck files from the OpenYugi deck directory
- Resolve alternate-art deck image IDs back to base card IDs
- Audit collection movement history from transactions or changelog logs
- Emit either human-readable output or JSON
- Run without third-party dependencies

## OpenYugi Integration

By default, the tool reads directly from a local OpenYugi tracker installation:

- `data/collections/Main.json`
- `data/db/card_db.json`
- `data/decks/`
- `data/transactions/`
- fallback movement history from `data/changelogs/`

Default tracker root:

```text
/home/username1/Yu-Gi-Oh-Card-Tracker
```

You can override every path with CLI flags when working against another installation or exported data set.

OpenYugi project links:

- Project repository: <https://github.com/DJ-Cat-N-Cheese/Yu-Gi-Oh-Card-Tracker>
- Tracker integration target referenced by this repo: <https://github.com/DJ-Cat-N-Cheese/Yu-Gi-Oh-Card-Tracker>

## Installation

### Requirements

- Python 3.10 or newer
- Local access to an OpenYugi data directory or exported collection files

### Run directly

No package installation is required.

```bash
cd yugioh-collection-query
python3 query_collection.py --help
```

## Quick Start

```bash
# Collection overview
python3 query_collection.py summary

# Top matching cards in the collection
python3 query_collection.py cards --name "Blue-Eyes" --limit 10

# Raw inventory rows for exact variant filtering
python3 query_collection.py entries --set-code RA02-EN072

# Resolve owned cards to canonical database IDs
python3 query_collection.py resolve --name "Pot of Extravagance"

# Join owned cards with effect text and stats
python3 query_collection.py details --quantity 3 --limit 5

# List available OpenYugi decks
python3 query_collection.py decks --limit 10

# Inspect a specific .ydk deck
python3 query_collection.py deck "Purrely"

# Review recent collection movements
python3 query_collection.py movements --limit 10

# Machine-readable output for scripts and agents
python3 query_collection.py summary --json
```

Additional examples are available in the [`examples/`](./examples/) directory.

## Command Reference

| Command | Purpose | Common flags |
| --- | --- | --- |
| `summary` | Show collection totals and grouped statistics | `--name`, `--set-code`, `--rarity`, `--language`, `--condition`, `--storage-location`, `--first-edition`, `--exact` |
| `cards` | Aggregate owned cards by name and total quantity | Summary filters + `--limit` |
| `entries` | Show raw inventory entry rows | Summary filters + `--limit` |
| `resolve` | Resolve owned cards against `card_db.json` | Summary filters + `--quantity`, `--min-quantity`, `--max-quantity`, `--limit` |
| `details` | Join owned cards with card DB details and effect text | Summary filters + quantity filters + `--limit` |
| `movements` | Query transaction or changelog history | Summary filters + `--action`, `--source`, `--limit` |
| `movement-summary` | Summarize matching movement history | Summary filters + `--action`, `--source` |
| `decks` | List `.ydk` deck files | `--limit` |
| `deck` | Inspect one deck and compare required cards against owned copies | `deck_name` |

Global flags:

- `--collection`: override the collection JSON path
- `--card-db`: override the card database JSON path
- `--transactions`: override the movement history directory or file
- `--decks-dir`: override the deck directory or file
- `--json`: emit JSON instead of text

## Usage Notes

- Matching is case-insensitive by default.
- Use `--exact` for exact text matching.
- `resolve` and `details` support quantity-based filtering.
- `movements` and `movement-summary` support action filters: `ADD`, `REMOVE`, `UPDATE`, `BATCH`.
- `deck` accepts either a deck name or a `.ydk` filename.

## Example Output

```text
$ python3 query_collection.py summary
Collection: Main
Card records: 5260
Unique card names: 5260
Resolved card IDs: 5260
Unique variants: 7874
Entry rows: 9395
Total copies: 11277
```

```text
$ python3 query_collection.py decks --limit 3
ABC 2017 (1) | file=ABC 2017 (1).ydk | main=42 | extra=15 | side=0 | total=57
ABC 2017 | file=ABC 2017.ydk | main=42 | extra=15 | side=0 | total=57
ABC-D-Z | file=ABC-D-Z.ydk | main=50 | extra=15 | side=0 | total=65
```

For a fuller walkthrough, see [`QUERY_TOOL.md`](./QUERY_TOOL.md).

## Repository Layout

```text
.
├── query_collection.py
├── README.md
├── QUERY_TOOL.md
├── examples/
└── .github/
```

## Contributing

Contributions are welcome for documentation, query ergonomics, and output quality improvements.

Recommended workflow:

1. Open an issue or describe the change clearly in your pull request.
2. Keep the tool read-only and dependency-light unless there is a strong reason not to.
3. Update documentation and examples whenever behavior changes.
4. Verify command help and representative queries before submitting.

A pull request template is included in [`pull_request_template.md`](./.github/pull_request_template.md).

## License

This project is licensed under the MIT License. See [`LICENSE`](./LICENSE).
