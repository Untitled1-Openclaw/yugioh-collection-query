# Yu-Gi-Oh! Collection Query Tool

A read-only CLI tool for querying Yu-Gi-Oh! card collection data.

## Features

- Query your card collection by name, rarity, set, condition, language, and more
- Get collection summaries and statistics
- Resolve card names to database IDs
- View card details and effects from the card database
- Track card movement history from changelogs
- Export results as JSON for automation

## Requirements

- Python 3.x (standard library only, no dependencies)

## Usage

```bash
# Collection summary
python3 query_collection.py summary

# List cards with filters
python3 query_collection.py cards --rarity "Secret Rare"
python3 query_collection.py cards --language DE --limit 20

# Find entries matching criteria
python3 query_collection.py entries --set-code RA02-EN072 --condition "Near Mint"

# Get card details from database
python3 query_collection.py details --name "Dark Magician"
python3 query_collection.py details --quantity 3 --limit 10

# Resolve card names to IDs
python3 query_collection.py resolve --name "Pot of Extravagance"

# View card movement history
python3 query_collection.py movements --name "Blue-Eyes White Dragon" --limit 5
python3 query_collection.py movement-summary --name "Ash Blossom"
```

## Data Sources

The tool reads from your Yu-Gi-Oh! Card Tracker installation:

- `collections/Main.json` - Your card collection
- `data/db/card_db.json` - Card database with effects and details
- `data/changelogs/` - Transaction/movement history

## Configuration

Set the `--collection` flag if your collection file is not at the default path:

```bash
python3 query_collection.py summary --collection /path/to/your/collection.json
```

## License

MIT
