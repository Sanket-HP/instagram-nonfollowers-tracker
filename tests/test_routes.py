"""End-to-end route tests."""

from __future__ import annotations

import io
import json


def test_index_lists_no_accounts(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"No accounts yet" in resp.data


def test_full_flow_creates_account_snapshot_and_imports(client):
    resp = client.post("/accounts", data={"username": "@Me"}, follow_redirects=True)
    assert resp.status_code == 200
    assert b"@me" in resp.data

    # Find the account id by scraping the snapshot-create URL from the page.
    create_resp = client.post(
        "/accounts/1/snapshots", data={"note": "first"}, follow_redirects=False
    )
    assert create_resp.status_code == 302
    snapshot_url = create_resp.headers["Location"]
    assert snapshot_url.endswith("/snapshots/1")

    followers_payload = json.dumps(
        [
            {
                "title": "",
                "string_list_data": [
                    {"value": "alice", "href": "https://www.instagram.com/alice"}
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
    following_payload = json.dumps(
        {
            "relationships_following": [
                {
                    "title": "",
                    "string_list_data": [
                        {"value": "bob", "href": "https://www.instagram.com/bob"}
                    ],
                },
                {
                    "title": "",
                    "string_list_data": [
                        {"value": "carol", "href": "https://www.instagram.com/carol"}
                    ],
                },
            ]
        }
    )

    resp = client.post(
        "/snapshots/1/import",
        data={
            "follower_file": (
                io.BytesIO(followers_payload.encode()),
                "followers_1.json",
            ),
            "following_file": (
                io.BytesIO(following_payload.encode()),
                "following.json",
            ),
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert resp.status_code == 200
    body = resp.data.decode()
    assert "Not following you back" in body
    assert "@carol" in body  # not following back
    assert "@alice" in body  # you don't follow back
    assert "@bob" in body  # mutual


def test_import_plain_text_paste(client):
    client.post("/accounts", data={"username": "me2"}, follow_redirects=True)
    create_resp = client.post("/accounts/1/snapshots", data={})
    snapshot_url = create_resp.headers["Location"]

    resp = client.post(
        snapshot_url + "/import",
        data={
            "follower_text": "alice\n@bob\nhttps://www.instagram.com/carol/",
            "following_text": "bob\ncarol\ndana",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    body = resp.data.decode()
    assert "@dana" in body  # not following back
    assert "@alice" in body  # you don't follow back


def test_csv_export(client):
    client.post("/accounts", data={"username": "me3"}, follow_redirects=True)
    create_resp = client.post("/accounts/1/snapshots", data={})
    snapshot_url = create_resp.headers["Location"]
    client.post(
        snapshot_url + "/import",
        data={
            "follower_text": "alice\nbob",
            "following_text": "bob\ncarol",
        },
        follow_redirects=True,
    )
    resp = client.get(snapshot_url + "/export/not-following-back.csv")
    assert resp.status_code == 200
    assert resp.mimetype == "text/csv"
    assert b"carol" in resp.data
