# Example Commands

## Collection Overview

```bash
python3 query_collection.py summary
python3 query_collection.py summary --json
python3 query_collection.py cards --limit 10
python3 query_collection.py entries --set-code RA02-EN072 --limit 10
```

## Card Resolution and Details

```bash
python3 query_collection.py resolve --name "Blue-Eyes White Dragon"
python3 query_collection.py resolve --quantity 3 --limit 10
python3 query_collection.py details --name "Dark Magician"
python3 query_collection.py details --quantity 3 --limit 5 --json
```

## Deck Queries

```bash
python3 query_collection.py decks --limit 10
python3 query_collection.py deck "Purrely"
python3 query_collection.py deck "ABC 2017 (1).ydk"
```

## Movement History

```bash
python3 query_collection.py movements --limit 10
python3 query_collection.py movements --name "Traptrix Mantis" --limit 5
python3 query_collection.py movement-summary --action ADD REMOVE
python3 query_collection.py movement-summary --source scan_temp.log
```

## Alternate Paths

```bash
python3 query_collection.py --collection /opt/openyugi/data/collections/Main.json summary
python3 query_collection.py --card-db /opt/openyugi/data/db/card_db.json details --name Purrely
python3 query_collection.py --decks-dir /opt/openyugi/data/decks deck "My Deck"
python3 query_collection.py --transactions /opt/openyugi/data/transactions movements --limit 20
```
