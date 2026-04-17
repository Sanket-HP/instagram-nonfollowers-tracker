"""Tests for the import parsers."""

from __future__ import annotations

import json

import pytest

from app.importers import parse_instagram_json, parse_plain_text


def test_parse_plain_text_strips_and_dedupes():
    text = """
    @alice
    bob
    https://www.instagram.com/carol/
      DANA
    bob
    """
    result = parse_plain_text(text)
    usernames = [e.username for e in result]
    assert usernames == ["alice", "bob", "carol", "dana"]


def test_parse_instagram_json_followers_shape():
    payload = json.dumps(
        [
            {
                "title": "Alice Example",
                "string_list_data": [
                    {
                        "value": "alice",
                        "href": "https://www.instagram.com/alice",
                    }
                ],
            },
            {
                "title": "",
                "string_list_data": [
                    {"value": "bob", "href": "https://www.instagram.com/bob"}
                ],
            },
        ]
    )
    result = parse_instagram_json(payload)
    assert [e.username for e in result] == ["alice", "bob"]
    assert result[0].full_name == "Alice Example"
    assert result[0].profile_url == "https://www.instagram.com/alice"


def test_parse_instagram_json_following_shape():
    payload = json.dumps(
        {
            "relationships_following": [
                {
                    "title": "",
                    "string_list_data": [
                        {"value": "carol", "href": "https://www.instagram.com/carol"}
                    ],
                }
            ]
        }
    )
    result = parse_instagram_json(payload)
    assert [e.username for e in result] == ["carol"]


def test_parse_instagram_json_invalid_raises():
    with pytest.raises(ValueError):
        parse_instagram_json(json.dumps({"unexpected": "shape"}))
