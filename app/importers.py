"""Parsers for the different ways users can supply follower/following data."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class ParsedEntry:
    """A single row extracted from an import source."""

    username: str
    full_name: str = ""
    profile_url: str = ""


def _clean_username(value: str) -> str:
    value = value.strip()
    if value.startswith("@"):
        value = value[1:]
    # Strip a pasted profile URL down to just the handle.
    if "instagram.com/" in value:
        value = value.split("instagram.com/", 1)[1]
    value = value.split("/")[0].split("?")[0]
    return value.strip().lower()


def parse_plain_text(text: str) -> list[ParsedEntry]:
    """Parse one-username-per-line text (with optional @ or URL)."""

    seen: set[str] = set()
    entries: list[ParsedEntry] = []
    for raw in text.splitlines():
        username = _clean_username(raw)
        if not username or username in seen:
            continue
        seen.add(username)
        entries.append(ParsedEntry(username=username))
    return entries


def _entries_from_instagram_nodes(nodes: Iterable[dict]) -> list[ParsedEntry]:
    """Extract entries from Instagram's export ``string_list_data`` nodes."""

    out: list[ParsedEntry] = []
    seen: set[str] = set()
    for node in nodes:
        data = node.get("string_list_data") or []
        if not data:
            continue
        first = data[0]
        username = _clean_username(first.get("value", ""))
        if not username or username in seen:
            continue
        seen.add(username)
        out.append(
            ParsedEntry(
                username=username,
                full_name=(node.get("title") or "").strip(),
                profile_url=(first.get("href") or "").strip(),
            )
        )
    return out


def parse_instagram_json(raw: str | bytes) -> list[ParsedEntry]:
    """Parse an Instagram "Download Your Information" JSON export.

    Supports both the ``followers_1.json`` shape (a bare list of nodes) and the
    ``following.json`` shape (an object with a ``relationships_following`` key).
    """

    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    data = json.loads(raw)

    if isinstance(data, list):
        return _entries_from_instagram_nodes(data)

    if isinstance(data, dict):
        # Newer exports wrap the list; check any likely key.
        for key in (
            "relationships_following",
            "relationships_followers",
            "relationships_follow_requests_sent",
        ):
            if key in data and isinstance(data[key], list):
                return _entries_from_instagram_nodes(data[key])

    raise ValueError(
        "Unrecognized Instagram export format. Expected a list of follower/"
        "following nodes or an object with a 'relationships_*' key."
    )
