"""SQLAlchemy models for the tracker."""

from __future__ import annotations

from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import UniqueConstraint

db = SQLAlchemy()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Account(db.Model):
    """An Instagram account whose follower graph we track."""

    __tablename__ = "accounts"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=_utcnow, nullable=False)

    snapshots = db.relationship(
        "Snapshot",
        back_populates="account",
        cascade="all, delete-orphan",
        order_by="Snapshot.taken_at.desc()",
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Account {self.username!r}>"


class Snapshot(db.Model):
    """A point-in-time import of followers and following for an account."""

    __tablename__ = "snapshots"

    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(
        db.Integer,
        db.ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    taken_at = db.Column(db.DateTime, default=_utcnow, nullable=False)
    note = db.Column(db.String(255), default="", nullable=False)

    account = db.relationship("Account", back_populates="snapshots")
    entries = db.relationship(
        "FollowEntry",
        back_populates="snapshot",
        cascade="all, delete-orphan",
    )

    def entries_by_kind(self, kind: str) -> list["FollowEntry"]:
        return [e for e in self.entries if e.kind == kind]

    @property
    def follower_count(self) -> int:
        return sum(1 for e in self.entries if e.kind == "follower")

    @property
    def following_count(self) -> int:
        return sum(1 for e in self.entries if e.kind == "following")


class FollowEntry(db.Model):
    """A single username in either the followers or following list for a snapshot."""

    __tablename__ = "follow_entries"
    __table_args__ = (
        UniqueConstraint(
            "snapshot_id", "username", "kind", name="uq_entry_snapshot_username_kind"
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    snapshot_id = db.Column(
        db.Integer,
        db.ForeignKey("snapshots.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    username = db.Column(db.String(64), nullable=False, index=True)
    full_name = db.Column(db.String(128), default="", nullable=False)
    profile_url = db.Column(db.String(255), default="", nullable=False)
    # Either "follower" (they follow the account) or "following" (account follows them).
    kind = db.Column(db.String(16), nullable=False)

    snapshot = db.relationship("Snapshot", back_populates="entries")
