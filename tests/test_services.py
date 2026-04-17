"""Tests for diff/compare logic."""

from __future__ import annotations

from app.importers import ParsedEntry
from app.models import Account, Snapshot, db
from app.services import compare_snapshots, diff_snapshot, replace_entries


def _make_snapshot(username="me", followers=(), following=(), note=""):
    account = Account.query.filter_by(username=username).first()
    if not account:
        account = Account(username=username)
        db.session.add(account)
        db.session.flush()
    snap = Snapshot(account_id=account.id, note=note)
    db.session.add(snap)
    db.session.flush()
    replace_entries(snap, "follower", [ParsedEntry(username=u) for u in followers])
    replace_entries(snap, "following", [ParsedEntry(username=u) for u in following])
    return snap


def test_diff_snapshot_buckets_users_correctly(app):
    with app.app_context():
        snap = _make_snapshot(
            followers=["alice", "bob"], following=["bob", "carol", "dana"]
        )
        diff = diff_snapshot(snap)
        assert [e.username for e in diff.not_following_back] == ["carol", "dana"]
        assert [e.username for e in diff.you_dont_follow_back] == ["alice"]
        assert [e.username for e in diff.mutuals] == ["bob"]


def test_replace_entries_overwrites_existing(app):
    with app.app_context():
        snap = _make_snapshot(followers=["alice"], following=["alice"])
        replace_entries(snap, "follower", [ParsedEntry(username="zeb")])
        diff = diff_snapshot(snap)
        assert [e.username for e in diff.mutuals] == []
        assert [e.username for e in diff.you_dont_follow_back] == ["zeb"]


def test_compare_snapshots(app):
    with app.app_context():
        older = _make_snapshot(followers=["alice", "bob"], following=["bob", "carol"])
        newer = _make_snapshot(followers=["bob", "dana"], following=["dana", "eve"])
        result = compare_snapshots(older, newer)
        assert result.new_followers == ["dana"]
        assert result.lost_followers == ["alice"]
        assert result.newly_followed == ["dana", "eve"]
        assert result.newly_unfollowed == ["bob", "carol"]
