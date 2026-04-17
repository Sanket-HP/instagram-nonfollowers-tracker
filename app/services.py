"""Business logic: diffing snapshots and bulk-inserting entries."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .importers import ParsedEntry
from .models import FollowEntry, Snapshot, db


@dataclass(frozen=True)
class DiffResult:
    """Result of diffing a snapshot's followers against its following."""

    not_following_back: list[FollowEntry]
    you_dont_follow_back: list[FollowEntry]
    mutuals: list[FollowEntry]


def replace_entries(
    snapshot: Snapshot, kind: str, parsed: Iterable[ParsedEntry]
) -> int:
    """Replace all entries of a given kind on a snapshot with the parsed set.

    Returns the number of rows inserted.
    """

    if kind not in {"follower", "following"}:
        raise ValueError(f"Unknown entry kind: {kind!r}")

    FollowEntry.query.filter_by(snapshot_id=snapshot.id, kind=kind).delete(
        synchronize_session=False
    )

    seen: set[str] = set()
    inserted = 0
    for entry in parsed:
        if entry.username in seen:
            continue
        seen.add(entry.username)
        db.session.add(
            FollowEntry(
                snapshot_id=snapshot.id,
                username=entry.username,
                full_name=entry.full_name,
                profile_url=entry.profile_url,
                kind=kind,
            )
        )
        inserted += 1

    db.session.commit()
    return inserted


def diff_snapshot(snapshot: Snapshot) -> DiffResult:
    """Compute follow-back diffs for a single snapshot."""

    followers = {e.username: e for e in snapshot.entries if e.kind == "follower"}
    following = {e.username: e for e in snapshot.entries if e.kind == "following"}

    not_following_back = sorted(
        (e for u, e in following.items() if u not in followers),
        key=lambda e: e.username,
    )
    you_dont_follow_back = sorted(
        (e for u, e in followers.items() if u not in following),
        key=lambda e: e.username,
    )
    mutuals = sorted(
        (e for u, e in following.items() if u in followers),
        key=lambda e: e.username,
    )
    return DiffResult(
        not_following_back=not_following_back,
        you_dont_follow_back=you_dont_follow_back,
        mutuals=mutuals,
    )


@dataclass(frozen=True)
class SnapshotCompareResult:
    """Diff of two snapshots of the same account."""

    new_followers: list[str]
    lost_followers: list[str]
    newly_followed: list[str]
    newly_unfollowed: list[str]


def compare_snapshots(older: Snapshot, newer: Snapshot) -> SnapshotCompareResult:
    """Return usernames that appeared/disappeared between two snapshots."""

    def _names(snap: Snapshot, kind: str) -> set[str]:
        return {e.username for e in snap.entries if e.kind == kind}

    old_followers = _names(older, "follower")
    new_followers_set = _names(newer, "follower")
    old_following = _names(older, "following")
    new_following_set = _names(newer, "following")

    return SnapshotCompareResult(
        new_followers=sorted(new_followers_set - old_followers),
        lost_followers=sorted(old_followers - new_followers_set),
        newly_followed=sorted(new_following_set - old_following),
        newly_unfollowed=sorted(old_following - new_following_set),
    )
