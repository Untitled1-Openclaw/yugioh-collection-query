#!/usr/bin/env python3
"""Query a Yu-Gi-Oh collection export and related OpenYugi data.

Designed for agent use:
- human-readable text output by default
- JSON output when downstream automation needs structured data
- stdlib only
- read-only access to external OpenYugi JSON/log data
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


WORKSPACE_ROOT = Path(__file__).resolve().parent
TRACKER_ROOT = Path("/home/username1/Yu-Gi-Oh-Card-Tracker")
DEFAULT_COLLECTION = TRACKER_ROOT / "data" / "collections" / "Main.json"
DEFAULT_CARD_DB = TRACKER_ROOT / "data" / "db" / "card_db.json"
DEFAULT_DECKS_DIR = TRACKER_ROOT / "data" / "decks"
DEFAULT_TRANSACTIONS = TRACKER_ROOT / "data" / "transactions"
FALLBACK_TRANSACTION_ROOTS = (
    TRACKER_ROOT / "data" / "transactions",
    TRACKER_ROOT / "data" / "changelogs",
)
TRANSACTION_SUFFIXES = {".json", ".log", ".ndjson"}
DECK_SUFFIX = ".ydk"


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_collection(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"Collection file must contain an object: {path}")
    return payload


def load_card_db(path: Path) -> list[dict[str, Any]]:
    payload = load_json(path)
    if not isinstance(payload, list):
        raise ValueError(f"Card DB must contain a list: {path}")
    return [record for record in payload if isinstance(record, dict)]


def normalize_bool(value: str | None) -> bool | None:
    if value is None:
        return None
    lowered = value.strip().lower()
    if lowered in {"true", "t", "yes", "y", "1", "first", "1st"}:
        return True
    if lowered in {"false", "f", "no", "n", "0", "unlimited"}:
        return False
    raise ValueError(f"Invalid boolean value: {value}")


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).casefold().strip()
    text = text.replace('"', "").replace("'", "")
    return " ".join(text.split())


def normalize_action(value: Any) -> str:
    return str(value or "").strip().upper()


def format_timestamp(timestamp: Any) -> str | None:
    if timestamp is None:
        return None
    try:
        return datetime.fromtimestamp(float(timestamp), tz=UTC).isoformat()
    except (TypeError, ValueError, OSError):
        return None


def build_card_indexes(card_db: list[dict[str, Any]]) -> dict[str, Any]:
    by_id: dict[int, dict[str, Any]] = {}
    by_name: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_variant: dict[str, dict[str, Any]] = {}
    by_set_code: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_image_id: dict[int, dict[str, Any]] = {}
    alt_art_map: dict[int, int] = {}

    for record in card_db:
        card_id = record.get("id")
        if isinstance(card_id, int):
            by_id[card_id] = record

        for image in record.get("card_images") or []:
            if not isinstance(image, dict):
                continue
            image_id = image.get("id")
            if not isinstance(image_id, int):
                continue
            by_image_id[image_id] = record
            if isinstance(card_id, int) and image_id != card_id:
                alt_art_map[image_id] = card_id

        name_key = normalize_text(record.get("name"))
        if name_key:
            by_name[name_key].append(record)

        for card_set in record.get("card_sets") or []:
            if not isinstance(card_set, dict):
                continue
            variant_id = card_set.get("variant_id")
            if variant_id:
                by_variant[str(variant_id)] = record
            set_code = card_set.get("set_code")
            if set_code:
                by_set_code[normalize_text(set_code)].append(record)

    return {
        "by_id": by_id,
        "by_name": by_name,
        "by_variant": by_variant,
        "by_set_code": by_set_code,
        "by_image_id": by_image_id,
        "alt_art_map": alt_art_map,
    }


def resolve_deck_card(
    deck_card_id: int,
    indexes: dict[str, Any],
) -> tuple[dict[str, Any] | None, int | None, bool]:
    record = indexes["by_id"].get(deck_card_id)
    if record is not None:
        return record, deck_card_id, False

    record = indexes["by_image_id"].get(deck_card_id)
    if record is None:
        return None, None, False

    base_id = record.get("id")
    return record, base_id if isinstance(base_id, int) else None, True


def resolve_card_record(
    card_id: Any,
    name: Any,
    variant_id: Any,
    set_code: Any,
    indexes: dict[str, Any],
) -> dict[str, Any] | None:
    if isinstance(card_id, int) and card_id in indexes["by_id"]:
        return indexes["by_id"][card_id]

    if variant_id:
        record = indexes["by_variant"].get(str(variant_id))
        if record is not None:
            return record

    name_key = normalize_text(name)
    if name_key:
        matches = indexes["by_name"].get(name_key, [])
        if len(matches) == 1:
            return matches[0]

        if set_code:
            target_set = normalize_text(set_code)
            for record in matches:
                for card_set in record.get("card_sets") or []:
                    if normalize_text(card_set.get("set_code")) == target_set:
                        return record

        if matches:
            return matches[0]

    if set_code:
        matches = indexes["by_set_code"].get(normalize_text(set_code), [])
        if len(matches) == 1:
            return matches[0]

    return None


def flatten_entries(collection: dict[str, Any], card_indexes: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for card in collection.get("cards", []):
        for variant in card.get("variants", []):
            resolved = None
            if card_indexes is not None:
                resolved = resolve_card_record(
                    card.get("card_id"),
                    card.get("name"),
                    variant.get("variant_id"),
                    variant.get("set_code"),
                    card_indexes,
                )
            resolved_card_id = card.get("card_id")
            if resolved is not None and isinstance(resolved.get("id"), int):
                resolved_card_id = resolved["id"]

            for entry in variant.get("entries", []):
                rows.append(
                    {
                        "collection_name": collection.get("name"),
                        "collection_description": collection.get("description"),
                        "card_id": card.get("card_id"),
                        "resolved_card_id": resolved_card_id,
                        "db_resolved": resolved is not None,
                        "name": card.get("name"),
                        "variant_id": variant.get("variant_id"),
                        "set_code": variant.get("set_code"),
                        "rarity": variant.get("rarity"),
                        "image_id": variant.get("image_id"),
                        "condition": entry.get("condition"),
                        "language": entry.get("language"),
                        "first_edition": entry.get("first_edition"),
                        "quantity": entry.get("quantity", 0),
                        "storage_location": entry.get("storage_location"),
                        "purchase_price": entry.get("purchase_price"),
                        "market_value": entry.get("market_value"),
                        "purchase_date": entry.get("purchase_date"),
                    }
                )
    return rows


def text_match(value: Any, expected: str | None, exact: bool) -> bool:
    if expected is None:
        return True
    haystack = "" if value is None else str(value)
    if exact:
        return haystack.casefold() == expected.casefold()
    return expected.casefold() in haystack.casefold()


def quantity_match(total: int, args: argparse.Namespace) -> bool:
    if getattr(args, "quantity", None) is not None and total != args.quantity:
        return False
    if getattr(args, "min_quantity", None) is not None and total < args.min_quantity:
        return False
    if getattr(args, "max_quantity", None) is not None and total > args.max_quantity:
        return False
    return True


def filter_rows(rows: list[dict[str, Any]], args: argparse.Namespace) -> list[dict[str, Any]]:
    filtered: list[dict[str, Any]] = []
    for row in rows:
        resolved_card_id = row.get("resolved_card_id", row.get("card_id"))
        card_id_filter = getattr(args, "card_id", None)
        if card_id_filter is not None and resolved_card_id != card_id_filter and row["card_id"] != card_id_filter:
            continue
        exact = bool(getattr(args, "exact", False))
        if not text_match(row["name"], getattr(args, "name", None), exact):
            continue
        if not text_match(row["set_code"], getattr(args, "set_code", None), exact):
            continue
        if not text_match(row["rarity"], getattr(args, "rarity", None), exact):
            continue
        if not text_match(row["condition"], getattr(args, "condition", None), exact):
            continue
        if not text_match(row["language"], getattr(args, "language", None), exact):
            continue
        if not text_match(row["storage_location"], getattr(args, "storage_location", None), exact):
            continue
        first_edition = getattr(args, "first_edition", None)
        if first_edition is not None and row["first_edition"] != first_edition:
            continue
        filtered.append(row)
    return filtered


def aggregate_cards(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for row in rows:
        resolved_card_id = row.get("resolved_card_id", row.get("card_id"))
        card = grouped.setdefault(
            row["name"],
            {
                "card_id": row["card_id"],
                "resolved_card_id": resolved_card_id,
                "db_resolved": bool(row.get("db_resolved")),
                "name": row["name"],
                "total_quantity": 0,
                "variant_count": set(),
                "set_codes": set(),
                "rarities": set(),
                "languages": set(),
                "conditions": set(),
            },
        )
        card["total_quantity"] += row["quantity"]
        card["variant_count"].add(row["variant_id"])
        card["db_resolved"] = card["db_resolved"] or bool(row.get("db_resolved"))
        if row["set_code"]:
            card["set_codes"].add(row["set_code"])
        if row["rarity"]:
            card["rarities"].add(row["rarity"])
        if row["language"]:
            card["languages"].add(row["language"])
        if row["condition"]:
            card["conditions"].add(row["condition"])

    cards = []
    for card in grouped.values():
        cards.append(
            {
                "card_id": card["card_id"],
                "resolved_card_id": card["resolved_card_id"],
                "db_resolved": card["db_resolved"],
                "name": card["name"],
                "total_quantity": card["total_quantity"],
                "variant_count": len(card["variant_count"]),
                "set_codes": sorted(card["set_codes"]),
                "rarities": sorted(card["rarities"]),
                "languages": sorted(card["languages"]),
                "conditions": sorted(card["conditions"]),
            }
        )

    return sorted(cards, key=lambda item: (-item["total_quantity"], item["name"]))


def summarize(collection: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    rarity_counts: Counter[str] = Counter()
    set_counts: Counter[str] = Counter()
    language_counts: Counter[str] = Counter()
    condition_counts: Counter[str] = Counter()
    first_edition_counts: Counter[str] = Counter()
    cards_with_quantity: defaultdict[str, int] = defaultdict(int)
    unique_variants: set[str] = set()
    resolved_ids: set[int] = set()

    for row in rows:
        qty = row["quantity"]
        cards_with_quantity[row["name"]] += qty
        resolved_card_id = row.get("resolved_card_id")
        if isinstance(resolved_card_id, int):
            resolved_ids.add(resolved_card_id)
        if row["variant_id"]:
            unique_variants.add(row["variant_id"])
        if row["rarity"]:
            rarity_counts[row["rarity"]] += qty
        if row["set_code"]:
            set_counts[row["set_code"]] += qty
        if row["language"]:
            language_counts[row["language"]] += qty
        if row["condition"]:
            condition_counts[row["condition"]] += qty
        edition_key = "First Edition" if row["first_edition"] else "Unlimited/Other"
        first_edition_counts[edition_key] += qty

    top_cards = sorted(cards_with_quantity.items(), key=lambda item: (-item[1], item[0]))[:10]

    return {
        "collection_name": collection.get("name"),
        "description": collection.get("description"),
        "card_records": len(collection.get("cards", [])),
        "entry_rows": len(rows),
        "unique_card_names": len(cards_with_quantity),
        "resolved_card_ids": len(resolved_ids),
        "unique_variants": len(unique_variants),
        "total_quantity": sum(row["quantity"] for row in rows),
        "quantity_by_rarity": dict(rarity_counts.most_common()),
        "quantity_by_set_code": dict(set_counts.most_common(15)),
        "quantity_by_language": dict(language_counts.most_common()),
        "quantity_by_condition": dict(condition_counts.most_common()),
        "quantity_by_edition": dict(first_edition_counts.most_common()),
        "top_cards": [{"name": name, "quantity": quantity} for name, quantity in top_cards],
    }


def discover_transaction_files(path: Path) -> list[Path]:
    search_roots: list[Path] = []
    if path.exists():
        search_roots.append(path)
    elif path.name == "transactions":
        for candidate in FALLBACK_TRANSACTION_ROOTS:
            if candidate.exists():
                search_roots.append(candidate)
    elif path.parent.exists():
        search_roots.append(path.parent)

    discovered: set[Path] = set()
    for root in search_roots:
        if root.is_file() and root.suffix.lower() in TRANSACTION_SUFFIXES:
            discovered.add(root)
            continue
        if not root.is_dir():
            continue
        for candidate in root.rglob("*"):
            if candidate.is_file() and candidate.suffix.lower() in TRANSACTION_SUFFIXES:
                discovered.add(candidate)
    return sorted(discovered)


def parse_transaction_file(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []

    records: list[dict[str, Any]] = []
    lines = [line for line in text.splitlines() if line.strip()]
    if lines:
        ndjson_ok = True
        for line in lines:
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                ndjson_ok = False
                break
            if isinstance(payload, dict):
                records.append(payload)
        if ndjson_ok:
            return records

    payload = json.loads(text)
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        return [payload]
    return []


def transaction_matches_card(transaction: dict[str, Any], args: argparse.Namespace) -> bool:
    card_id = transaction.get("resolved_card_id", transaction.get("card_id"))
    if args.card_id is not None and card_id != args.card_id:
        return False
    if not text_match(transaction.get("name"), args.name, args.exact):
        return False
    if not text_match(transaction.get("set_code"), args.set_code, args.exact):
        return False
    if not text_match(transaction.get("rarity"), args.rarity, args.exact):
        return False
    if not text_match(transaction.get("storage_location"), args.storage_location, args.exact):
        return False
    if not text_match(transaction.get("source_file"), args.source, args.exact):
        return False
    actions = getattr(args, "action", None)
    if actions and transaction.get("action") not in set(actions):
        return False
    return True


def normalize_transaction_entry(
    raw: dict[str, Any],
    source_file: Path,
    card_indexes: dict[str, Any] | None,
    parent: dict[str, Any] | None = None,
) -> dict[str, Any]:
    card_data = raw.get("card_data")
    if not isinstance(card_data, dict):
        card_data = {}

    resolved = None
    if card_indexes is not None:
        resolved = resolve_card_record(
            card_data.get("card_id"),
            card_data.get("name"),
            card_data.get("variant_id"),
            card_data.get("set_code"),
            card_indexes,
        )

    resolved_card_id = card_data.get("card_id")
    if resolved is not None and isinstance(resolved.get("id"), int):
        resolved_card_id = resolved["id"]

    return {
        "action": normalize_action(raw.get("action")),
        "quantity": raw.get("quantity", 0),
        "type": raw.get("type") or (parent or {}).get("type"),
        "entry_id": raw.get("id"),
        "batch_id": (parent or {}).get("id"),
        "batch_description": (parent or {}).get("description"),
        "timestamp": raw.get("timestamp", (parent or {}).get("timestamp")),
        "timestamp_iso": format_timestamp(raw.get("timestamp", (parent or {}).get("timestamp"))),
        "source_file": str(source_file),
        "card_id": card_data.get("card_id"),
        "resolved_card_id": resolved_card_id,
        "db_resolved": resolved is not None,
        "name": card_data.get("name"),
        "variant_id": card_data.get("variant_id"),
        "set_code": card_data.get("set_code"),
        "rarity": card_data.get("rarity"),
        "image_id": card_data.get("image_id"),
        "language": card_data.get("language"),
        "condition": card_data.get("condition"),
        "first_edition": card_data.get("first_edition"),
        "storage_location": card_data.get("storage_location"),
        "target_zone": card_data.get("target_zone"),
        "old_data": raw.get("old_data"),
    }


def load_transactions(path: Path, card_indexes: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for file_path in discover_transaction_files(path):
        for raw in parse_transaction_file(file_path):
            action = normalize_action(raw.get("action"))
            if action == "BATCH" and isinstance(raw.get("changes"), list):
                for change in raw["changes"]:
                    if isinstance(change, dict):
                        rows.append(normalize_transaction_entry(change, file_path, card_indexes, parent=raw))
                continue
            if isinstance(raw, dict):
                rows.append(normalize_transaction_entry(raw, file_path, card_indexes))

    rows.sort(key=lambda row: (row.get("timestamp") or 0, row.get("entry_id") or 0), reverse=True)
    return rows


def summarize_movements(rows: list[dict[str, Any]]) -> dict[str, Any]:
    action_counts: Counter[str] = Counter()
    card_counts: Counter[str] = Counter()
    source_counts: Counter[str] = Counter()

    for row in rows:
        action_counts[row["action"]] += 1
        if row.get("name"):
            card_counts[row["name"]] += 1
        source_counts[row["source_file"]] += 1

    return {
        "movement_count": len(rows),
        "actions": dict(action_counts.most_common()),
        "top_cards": [{"name": name, "movements": count} for name, count in card_counts.most_common(10)],
        "sources": dict(source_counts.most_common(10)),
        "latest_timestamp": rows[0].get("timestamp_iso") if rows else None,
    }


def build_card_details(cards: list[dict[str, Any]], card_indexes: dict[str, Any]) -> list[dict[str, Any]]:
    details: list[dict[str, Any]] = []
    for card in cards:
        record = resolve_card_record(
            card.get("resolved_card_id") or card.get("card_id"),
            card.get("name"),
            None,
            card.get("set_codes", [None])[0],
            card_indexes,
        )
        if record is None:
            continue
        prices = (record.get("card_prices") or [{}])[0]
        details.append(
            {
                "name": card["name"],
                "owned_quantity": card["total_quantity"],
                "card_id": record.get("id"),
                "type": record.get("type"),
                "frame_type": record.get("frameType"),
                "desc": record.get("desc"),
                "attribute": record.get("attribute"),
                "race": record.get("race"),
                "archetype": record.get("archetype"),
                "atk": record.get("atk"),
                "def": record.get("def"),
                "level": record.get("level"),
                "linkval": record.get("linkval"),
                "set_codes": card.get("set_codes", []),
                "rarities": card.get("rarities", []),
                "tcgplayer_price": prices.get("tcgplayer_price"),
                "cardmarket_price": prices.get("cardmarket_price"),
            }
        )
    return sorted(details, key=lambda item: (-item["owned_quantity"], item["name"]))


def build_owned_quantity_map(cards: list[dict[str, Any]]) -> dict[int, int]:
    owned_map: dict[int, int] = {}
    for card in cards:
        resolved_card_id = card.get("resolved_card_id")
        if isinstance(resolved_card_id, int):
            owned_map[resolved_card_id] = card["total_quantity"]
    return owned_map


def discover_deck_files(path: Path) -> list[Path]:
    if path.is_file() and path.suffix.lower() == DECK_SUFFIX:
        return [path]
    if not path.exists() or not path.is_dir():
        return []
    return sorted(candidate for candidate in path.rglob(f"*{DECK_SUFFIX}") if candidate.is_file())


def parse_ydk_file(path: Path) -> dict[str, Any]:
    deck = {
        "name": path.stem,
        "filename": path.name,
        "path": str(path),
        "main": [],
        "extra": [],
        "side": [],
    }
    current_section = "main"

    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith("#"):
                lowered = line.lower()
                if "main" in lowered:
                    current_section = "main"
                elif "extra" in lowered:
                    current_section = "extra"
                elif "side" in lowered:
                    current_section = "side"
                continue
            if line.startswith("!"):
                if "side" in line.lower():
                    current_section = "side"
                continue
            if not line.isdigit():
                continue
            deck[current_section].append(int(line))

    return deck


def list_decks(path: Path) -> list[dict[str, Any]]:
    decks = []
    for deck_path in discover_deck_files(path):
        parsed = parse_ydk_file(deck_path)
        decks.append(
            {
                "name": parsed["name"],
                "filename": parsed["filename"],
                "path": parsed["path"],
                "main_count": len(parsed["main"]),
                "extra_count": len(parsed["extra"]),
                "side_count": len(parsed["side"]),
                "total_count": len(parsed["main"]) + len(parsed["extra"]) + len(parsed["side"]),
            }
        )
    return decks


def resolve_deck_name(decks: list[dict[str, Any]], target: str) -> dict[str, Any]:
    normalized_target = normalize_text(target)
    exact_matches = [
        deck
        for deck in decks
        if normalize_text(deck["name"]) == normalized_target
        or normalize_text(deck["filename"]) == normalized_target
    ]
    if len(exact_matches) == 1:
        return exact_matches[0]
    if len(exact_matches) > 1:
        matches = ", ".join(deck["filename"] for deck in exact_matches[:10])
        raise ValueError(f"Deck name is ambiguous: {matches}")

    fuzzy_matches = [
        deck
        for deck in decks
        if normalized_target in normalize_text(deck["name"])
        or normalized_target in normalize_text(deck["filename"])
    ]
    if len(fuzzy_matches) == 1:
        return fuzzy_matches[0]
    if not fuzzy_matches:
        raise FileNotFoundError(f"No deck matched: {target}")

    matches = ", ".join(deck["filename"] for deck in fuzzy_matches[:10])
    raise ValueError(f"Deck name is ambiguous: {matches}")


def summarize_deck_section(
    section_name: str,
    card_ids: list[int],
    card_indexes: dict[str, Any],
    owned_map: dict[int, int],
) -> tuple[list[dict[str, Any]], Counter[int]]:
    grouped: dict[int, dict[str, Any]] = {}
    base_requirements: Counter[int] = Counter()

    for deck_card_id in card_ids:
        record, base_id, is_alt_art = resolve_deck_card(deck_card_id, card_indexes)
        key = deck_card_id
        item = grouped.setdefault(
            key,
            {
                "section": section_name,
                "deck_card_id": deck_card_id,
                "resolved_card_id": base_id,
                "name": record.get("name") if record else None,
                "known": record is not None,
                "is_alt_art": is_alt_art,
                "artstyle_offset": deck_card_id - base_id if is_alt_art and isinstance(base_id, int) else 0,
                "quantity": 0,
                "owned_quantity": owned_map.get(base_id, 0) if isinstance(base_id, int) else 0,
                "type": record.get("type") if record else None,
            },
        )
        item["quantity"] += 1
        if isinstance(base_id, int):
            base_requirements[base_id] += 1

    rows = sorted(
        grouped.values(),
        key=lambda item: (
            item["name"] is None,
            normalize_text(item["name"] or str(item["deck_card_id"])),
            item["deck_card_id"],
        ),
    )
    return rows, base_requirements


def build_deck_report(
    deck: dict[str, Any],
    card_indexes: dict[str, Any],
    owned_map: dict[int, int],
) -> dict[str, Any]:
    sections: dict[str, list[dict[str, Any]]] = {}
    required_by_base: Counter[int] = Counter()
    unknown_ids: list[int] = []

    for section_name in ("main", "extra", "side"):
        rows, requirements = summarize_deck_section(section_name, deck[section_name], card_indexes, owned_map)
        sections[section_name] = rows
        required_by_base.update(requirements)
        unknown_ids.extend(item["deck_card_id"] for item in rows if not item["known"])

    missing_cards: list[dict[str, Any]] = []
    for base_id, required_quantity in sorted(required_by_base.items(), key=lambda item: (-item[1], item[0])):
        record = card_indexes["by_id"].get(base_id)
        owned_quantity = owned_map.get(base_id, 0)
        if owned_quantity >= required_quantity:
            continue
        missing_cards.append(
            {
                "card_id": base_id,
                "name": record.get("name") if record else None,
                "required_quantity": required_quantity,
                "owned_quantity": owned_quantity,
                "missing_quantity": required_quantity - owned_quantity,
            }
        )

    return {
        "name": deck["name"],
        "filename": deck["filename"],
        "path": deck["path"],
        "main_count": len(deck["main"]),
        "extra_count": len(deck["extra"]),
        "side_count": len(deck["side"]),
        "total_count": len(deck["main"]) + len(deck["extra"]) + len(deck["side"]),
        "sections": sections,
        "unknown_ids": sorted(set(unknown_ids)),
        "missing_cards": missing_cards,
    }


def render_summary(summary: dict[str, Any]) -> str:
    lines = [
        f"Collection: {summary['collection_name']}",
        f"Card records: {summary['card_records']}",
        f"Unique card names: {summary['unique_card_names']}",
        f"Resolved card IDs: {summary['resolved_card_ids']}",
        f"Unique variants: {summary['unique_variants']}",
        f"Entry rows: {summary['entry_rows']}",
        f"Total copies: {summary['total_quantity']}",
        "",
        "Top cards by copies:",
    ]
    for item in summary["top_cards"]:
        lines.append(f"- {item['name']}: {item['quantity']}")

    def add_section(title: str, data: dict[str, Any]) -> None:
        lines.append("")
        lines.append(f"{title}:")
        for key, value in data.items():
            lines.append(f"- {key}: {value}")

    add_section("Copies by rarity", summary["quantity_by_rarity"])
    add_section("Copies by language", summary["quantity_by_language"])
    add_section("Copies by condition", summary["quantity_by_condition"])
    add_section("Copies by edition", summary["quantity_by_edition"])
    add_section("Top set codes", summary["quantity_by_set_code"])
    return "\n".join(lines)


def render_cards(cards: list[dict[str, Any]], limit: int | None) -> str:
    if limit is not None:
        cards = cards[:limit]
    if not cards:
        return "No cards matched."
    lines = []
    for card in cards:
        resolved_label = card["resolved_card_id"] if card["resolved_card_id"] is not None else "?"
        lines.append(
            f"{card['name']} | qty={card['total_quantity']} | card_id={resolved_label} | "
            f"variants={card['variant_count']} | sets={','.join(card['set_codes']) or '-'} | "
            f"rarities={','.join(card['rarities']) or '-'}"
        )
    return "\n".join(lines)


def render_entries(rows: list[dict[str, Any]], limit: int | None) -> str:
    if limit is not None:
        rows = rows[:limit]
    if not rows:
        return "No entries matched."
    lines = []
    for row in rows:
        edition = "1st" if row["first_edition"] else "Unlimited/Other"
        resolved_label = row["resolved_card_id"] if row["resolved_card_id"] is not None else "?"
        lines.append(
            f"{row['name']} | qty={row['quantity']} | card_id={resolved_label} | set={row['set_code']} | "
            f"rarity={row['rarity']} | condition={row['condition']} | language={row['language']} | "
            f"edition={edition} | location={row['storage_location'] or '-'}"
        )
    return "\n".join(lines)


def render_resolved(cards: list[dict[str, Any]], limit: int | None) -> str:
    if limit is not None:
        cards = cards[:limit]
    if not cards:
        return "No cards matched."
    return "\n".join(
        f"{card['name']} | collection_card_id={card['card_id']} | resolved_card_id={card['resolved_card_id']} | "
        f"qty={card['total_quantity']} | resolved={'yes' if card['db_resolved'] else 'no'}"
        for card in cards
    )


def render_details(details: list[dict[str, Any]], limit: int | None) -> str:
    if limit is not None:
        details = details[:limit]
    if not details:
        return "No card details matched."

    lines: list[str] = []
    for item in details:
        stats = []
        if item.get("attribute"):
            stats.append(item["attribute"])
        if item.get("race"):
            stats.append(item["race"])
        if item.get("level") is not None:
            stats.append(f"Level {item['level']}")
        if item.get("linkval") is not None:
            stats.append(f"Link {item['linkval']}")
        if item.get("atk") is not None:
            stats.append(f"ATK {item['atk']}")
        if item.get("def") is not None:
            stats.append(f"DEF {item['def']}")

        lines.append(
            f"{item['name']} | qty={item['owned_quantity']} | card_id={item['card_id']} | "
            f"type={item['type']} | {' | '.join(stats) if stats else '-'}"
        )
        if item.get("archetype"):
            lines.append(f"  archetype: {item['archetype']}")
        if item.get("set_codes"):
            lines.append(f"  owned sets: {', '.join(item['set_codes'])}")
        if item.get("rarities"):
            lines.append(f"  owned rarities: {', '.join(item['rarities'])}")
        prices = []
        if item.get("tcgplayer_price") not in {None, ""}:
            prices.append(f"TCGPlayer {item['tcgplayer_price']}")
        if item.get("cardmarket_price") not in {None, ""}:
            prices.append(f"Cardmarket {item['cardmarket_price']}")
        if prices:
            lines.append(f"  prices: {', '.join(prices)}")
        if item.get("desc"):
            lines.append(f"  effect: {item['desc']}")
    return "\n".join(lines)


def render_movements(rows: list[dict[str, Any]], limit: int | None) -> str:
    if limit is not None:
        rows = rows[:limit]
    if not rows:
        return "No movements matched."

    lines = []
    for row in rows:
        label = row["name"] or f"card_id={row['resolved_card_id'] or row['card_id'] or '?'}"
        extra = []
        if row.get("set_code"):
            extra.append(f"set={row['set_code']}")
        if row.get("storage_location") is not None:
            extra.append(f"location={row['storage_location'] or '-'}")
        if row.get("target_zone"):
            extra.append(f"zone={row['target_zone']}")
        if row.get("batch_description"):
            extra.append(f"batch={row['batch_description']}")
        stamp = row.get("timestamp_iso") or str(row.get("timestamp") or "?")
        lines.append(
            f"{stamp} | {row['action']} | {label} | qty={row['quantity']} | "
            f"file={Path(row['source_file']).name}" + (f" | {' | '.join(extra)}" if extra else "")
        )
    return "\n".join(lines)


def render_movement_summary(summary: dict[str, Any]) -> str:
    lines = [
        f"Movements: {summary['movement_count']}",
        f"Latest movement: {summary['latest_timestamp'] or '-'}",
        "",
        "Actions:",
    ]
    for action, count in summary["actions"].items():
        lines.append(f"- {action}: {count}")
    lines.append("")
    lines.append("Top cards:")
    for item in summary["top_cards"]:
        lines.append(f"- {item['name']}: {item['movements']}")
    lines.append("")
    lines.append("Sources:")
    for source, count in summary["sources"].items():
        lines.append(f"- {Path(source).name}: {count}")
    return "\n".join(lines)


def render_deck_list(decks: list[dict[str, Any]], limit: int | None) -> str:
    if limit is not None:
        decks = decks[:limit]
    if not decks:
        return "No decks found."
    return "\n".join(
        f"{deck['name']} | file={deck['filename']} | main={deck['main_count']} | "
        f"extra={deck['extra_count']} | side={deck['side_count']} | total={deck['total_count']}"
        for deck in decks
    )


def render_deck_report(report: dict[str, Any]) -> str:
    lines = [
        f"Deck: {report['name']}",
        f"File: {report['filename']}",
        f"Main: {report['main_count']} | Extra: {report['extra_count']} | Side: {report['side_count']} | Total: {report['total_count']}",
    ]

    if report["unknown_ids"]:
        lines.append(f"Unknown IDs: {', '.join(str(card_id) for card_id in report['unknown_ids'])}")

    if report["missing_cards"]:
        missing_total = sum(item["missing_quantity"] for item in report["missing_cards"])
        lines.append(f"Missing owned copies: {missing_total}")
    else:
        lines.append("Missing owned copies: 0")

    for section_name in ("main", "extra", "side"):
        rows = report["sections"][section_name]
        lines.append("")
        lines.append(f"{section_name.title()} Deck:")
        if not rows:
            lines.append("- empty")
            continue
        for item in rows:
            if not item["known"]:
                lines.append(f"- {item['quantity']}x UNKNOWN | deck_id={item['deck_card_id']}")
                continue
            art_label = ""
            if item["is_alt_art"]:
                offset = item["artstyle_offset"]
                art_label = f" | art=alt({offset:+d})" if offset else " | art=alt"
            lines.append(
                f"- {item['quantity']}x {item['name']} | deck_id={item['deck_card_id']} | "
                f"base_id={item['resolved_card_id']} | owned={item['owned_quantity']}{art_label}"
            )

    if report["missing_cards"]:
        lines.append("")
        lines.append("Missing from collection:")
        for item in report["missing_cards"]:
            label = item["name"] or f"card_id={item['card_id']}"
            lines.append(
                f"- {label} | card_id={item['card_id']} | required={item['required_quantity']} | "
                f"owned={item['owned_quantity']} | missing={item['missing_quantity']}"
            )

    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--collection",
        default=str(DEFAULT_COLLECTION),
        help=f"Path to collection JSON (default: {DEFAULT_COLLECTION})",
    )
    parser.add_argument(
        "--card-db",
        default=str(DEFAULT_CARD_DB),
        help=f"Path to card database JSON (default: {DEFAULT_CARD_DB})",
    )
    parser.add_argument(
        "--transactions",
        default=str(DEFAULT_TRANSACTIONS),
        help=(
            "Path to transaction directory/file. If the default transactions path is missing, "
            "the tool falls back to tracker changelogs."
        ),
    )
    parser.add_argument(
        "--decks-dir",
        default=str(DEFAULT_DECKS_DIR),
        help=f"Path to deck directory/file (default: {DEFAULT_DECKS_DIR})",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text")

    subparsers = parser.add_subparsers(dest="command", required=True)

    summary_parser = subparsers.add_parser("summary", help="Show collection summary statistics")
    add_json_flag(summary_parser)
    add_filters(summary_parser)

    cards_parser = subparsers.add_parser("cards", help="List cards and total copies")
    add_json_flag(cards_parser)
    add_filters(cards_parser)
    cards_parser.add_argument("--limit", type=int, default=50, help="Maximum results to show")

    entries_parser = subparsers.add_parser("entries", help="List matching inventory entries")
    add_json_flag(entries_parser)
    add_filters(entries_parser)
    entries_parser.add_argument("--limit", type=int, default=50, help="Maximum results to show")

    resolve_parser = subparsers.add_parser("resolve", help="Resolve collection cards against card_db.json")
    add_json_flag(resolve_parser)
    add_filters(resolve_parser)
    add_quantity_filters(resolve_parser)
    resolve_parser.add_argument("--limit", type=int, default=50, help="Maximum results to show")

    details_parser = subparsers.add_parser(
        "details",
        help="Join owned cards with card_db.json details, including effects",
    )
    add_json_flag(details_parser)
    add_filters(details_parser)
    add_quantity_filters(details_parser)
    details_parser.add_argument("--limit", type=int, default=20, help="Maximum results to show")

    movements_parser = subparsers.add_parser(
        "movements",
        help="Query card movement history from transaction/changelog files",
    )
    add_json_flag(movements_parser)
    add_filters(movements_parser)
    movements_parser.add_argument("--limit", type=int, default=20, help="Maximum results to show")
    movements_parser.add_argument(
        "--action",
        nargs="+",
        choices=["ADD", "REMOVE", "UPDATE", "BATCH"],
        help="Filter by action(s)",
    )
    movements_parser.add_argument("--source", help="Filter by source filename/path")

    movement_summary_parser = subparsers.add_parser(
        "movement-summary",
        help="Summarize card movement history from transaction/changelog files",
    )
    add_json_flag(movement_summary_parser)
    add_filters(movement_summary_parser)
    movement_summary_parser.add_argument(
        "--action",
        nargs="+",
        choices=["ADD", "REMOVE", "UPDATE", "BATCH"],
        help="Filter by action(s)",
    )
    movement_summary_parser.add_argument("--source", help="Filter by source filename/path")

    decks_parser = subparsers.add_parser("decks", help="List available .ydk decks")
    add_json_flag(decks_parser)
    decks_parser.add_argument("--limit", type=int, default=100, help="Maximum results to show")

    deck_parser = subparsers.add_parser("deck", help="Show cards in a specific .ydk deck")
    add_json_flag(deck_parser)
    deck_parser.add_argument("deck_name", help="Deck name or filename to inspect")

    return parser


def add_filters(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--name", help="Filter by card name")
    parser.add_argument("--card-id", type=int, help="Filter by card ID")
    parser.add_argument("--set-code", help="Filter by set code")
    parser.add_argument("--rarity", help="Filter by rarity")
    parser.add_argument("--condition", help="Filter by condition")
    parser.add_argument("--language", help="Filter by language")
    parser.add_argument("--storage-location", help="Filter by storage location")
    parser.add_argument(
        "--first-edition",
        type=normalize_bool,
        help="Filter by first edition status: true/false",
    )
    parser.add_argument(
        "--exact",
        action="store_true",
        help="Use exact matching instead of case-insensitive substring matching",
    )


def add_json_flag(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--json",
        action="store_true",
        default=argparse.SUPPRESS,
        help="Emit JSON instead of text",
    )


def add_quantity_filters(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--quantity", type=int, help="Filter by exact owned quantity")
    parser.add_argument("--min-quantity", type=int, help="Filter by minimum owned quantity")
    parser.add_argument("--max-quantity", type=int, help="Filter by maximum owned quantity")


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    card_db = load_card_db(Path(args.card_db))
    card_indexes = build_card_indexes(card_db)
    collection = load_collection(Path(args.collection))
    rows = flatten_entries(collection, card_indexes)
    filtered_rows = filter_rows(rows, args)
    aggregated_cards = aggregate_cards(filtered_rows)
    owned_map = build_owned_quantity_map(aggregate_cards(rows))

    if args.command == "summary":
        payload = summarize(collection, filtered_rows)
        print(json.dumps(payload, indent=2) if args.json else render_summary(payload))
        return 0

    if args.command == "cards":
        payload = aggregated_cards
        if args.json:
            print(json.dumps(payload[: args.limit], indent=2))
        else:
            print(render_cards(payload, args.limit))
        return 0

    if args.command == "entries":
        if args.json:
            print(json.dumps(filtered_rows[: args.limit], indent=2))
        else:
            print(render_entries(filtered_rows, args.limit))
        return 0

    if args.command == "resolve":
        payload = [card for card in aggregated_cards if quantity_match(card["total_quantity"], args)]
        if args.json:
            print(json.dumps(payload[: args.limit], indent=2))
        else:
            print(render_resolved(payload, args.limit))
        return 0

    if args.command == "details":
        matching_cards = [card for card in aggregated_cards if quantity_match(card["total_quantity"], args)]
        payload = build_card_details(matching_cards, card_indexes)
        if args.json:
            print(json.dumps(payload[: args.limit], indent=2))
        else:
            print(render_details(payload, args.limit))
        return 0

    if args.command in {"movements", "movement-summary"}:
        transactions = load_transactions(Path(args.transactions), card_indexes)
        filtered_transactions = [row for row in transactions if transaction_matches_card(row, args)]
        if args.command == "movements":
            if args.json:
                print(json.dumps(filtered_transactions[: args.limit], indent=2))
            else:
                print(render_movements(filtered_transactions, args.limit))
        else:
            payload = summarize_movements(filtered_transactions)
            print(json.dumps(payload, indent=2) if args.json else render_movement_summary(payload))
        return 0

    if args.command == "decks":
        payload = list_decks(Path(args.decks_dir))
        if args.json:
            print(json.dumps(payload[: args.limit], indent=2))
        else:
            print(render_deck_list(payload, args.limit))
        return 0

    if args.command == "deck":
        decks = list_decks(Path(args.decks_dir))
        selected = resolve_deck_name(decks, args.deck_name)
        deck_data = parse_ydk_file(Path(selected["path"]))
        payload = build_deck_report(deck_data, card_indexes, owned_map)
        print(json.dumps(payload, indent=2) if args.json else render_deck_report(payload))
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
