"""HTTP routes for the tracker."""

from __future__ import annotations

import csv
import io
import re

from flask import (
    Blueprint,
    Response,
    abort,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

from .importers import parse_instagram_json, parse_plain_text
from .models import Account, FollowEntry, Snapshot, db
from .services import compare_snapshots, diff_snapshot, replace_entries

bp = Blueprint("main", __name__)

USERNAME_RE = re.compile(r"^[A-Za-z0-9._]{1,30}$")


@bp.route("/")
def index():
    accounts = Account.query.order_by(Account.username).all()
    return render_template("index.html", accounts=accounts)


@bp.route("/accounts", methods=["POST"])
def create_account():
    username = (request.form.get("username") or "").strip().lstrip("@").lower()
    if not USERNAME_RE.match(username):
        flash(
            "Invalid username. Use 1-30 characters: letters, numbers, '.' or '_'.",
            "error",
        )
        return redirect(url_for("main.index"))

    if Account.query.filter_by(username=username).first():
        flash(f"Account @{username} already exists.", "error")
        return redirect(url_for("main.index"))

    account = Account(username=username)
    db.session.add(account)
    db.session.commit()
    flash(f"Added account @{username}.", "success")
    return redirect(url_for("main.account_detail", account_id=account.id))


@bp.route("/accounts/<int:account_id>/delete", methods=["POST"])
def delete_account(account_id: int):
    account = db.session.get(Account, account_id) or abort(404)
    db.session.delete(account)
    db.session.commit()
    flash(f"Deleted account @{account.username}.", "success")
    return redirect(url_for("main.index"))


@bp.route("/accounts/<int:account_id>")
def account_detail(account_id: int):
    account = db.session.get(Account, account_id) or abort(404)
    return render_template("account.html", account=account)


@bp.route("/accounts/<int:account_id>/snapshots", methods=["POST"])
def create_snapshot(account_id: int):
    account = db.session.get(Account, account_id) or abort(404)
    note = (request.form.get("note") or "").strip()[:255]
    snapshot = Snapshot(account_id=account.id, note=note)
    db.session.add(snapshot)
    db.session.commit()
    flash("Snapshot created. Now import followers and following below.", "success")
    return redirect(url_for("main.snapshot_detail", snapshot_id=snapshot.id))


@bp.route("/snapshots/<int:snapshot_id>")
def snapshot_detail(snapshot_id: int):
    snapshot = db.session.get(Snapshot, snapshot_id) or abort(404)
    diff = diff_snapshot(snapshot)
    return render_template("snapshot.html", snapshot=snapshot, diff=diff)


@bp.route("/snapshots/<int:snapshot_id>/delete", methods=["POST"])
def delete_snapshot(snapshot_id: int):
    snapshot = db.session.get(Snapshot, snapshot_id) or abort(404)
    account_id = snapshot.account_id
    db.session.delete(snapshot)
    db.session.commit()
    flash("Snapshot deleted.", "success")
    return redirect(url_for("main.account_detail", account_id=account_id))


def _parse_upload(kind: str) -> list:
    """Read either the uploaded file or pasted text for the given list kind."""

    file_field = f"{kind}_file"
    text_field = f"{kind}_text"

    uploaded = request.files.get(file_field)
    if uploaded and uploaded.filename:
        raw = uploaded.read()
        name = uploaded.filename.lower()
        if name.endswith(".json"):
            return parse_instagram_json(raw)
        return parse_plain_text(raw.decode("utf-8", errors="replace"))

    text = request.form.get(text_field, "")
    if text.strip():
        return parse_plain_text(text)

    return []


@bp.route("/snapshots/<int:snapshot_id>/import", methods=["POST"])
def import_to_snapshot(snapshot_id: int):
    snapshot = db.session.get(Snapshot, snapshot_id) or abort(404)

    total = 0
    for kind in ("follower", "following"):
        try:
            parsed = _parse_upload(kind)
        except ValueError as exc:
            flash(f"Could not parse {kind} data: {exc}", "error")
            return redirect(url_for("main.snapshot_detail", snapshot_id=snapshot.id))

        if parsed:
            inserted = replace_entries(snapshot, kind, parsed)
            total += inserted
            flash(
                f"Imported {inserted} {kind}{'s' if inserted != 1 else ''} "
                f"into snapshot #{snapshot.id}.",
                "success",
            )

    if total == 0:
        flash("Nothing to import — upload a file or paste usernames.", "error")

    return redirect(url_for("main.snapshot_detail", snapshot_id=snapshot.id))


@bp.route("/snapshots/<int:snapshot_id>/export/<string:which>.csv")
def export_csv(snapshot_id: int, which: str):
    snapshot = db.session.get(Snapshot, snapshot_id) or abort(404)
    diff = diff_snapshot(snapshot)
    buckets = {
        "not-following-back": diff.not_following_back,
        "you-dont-follow-back": diff.you_dont_follow_back,
        "mutuals": diff.mutuals,
    }
    if which not in buckets:
        abort(404)

    rows: list[FollowEntry] = buckets[which]
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["username", "full_name", "profile_url"])
    for entry in rows:
        writer.writerow(
            [
                entry.username,
                entry.full_name,
                entry.profile_url or f"https://www.instagram.com/{entry.username}/",
            ]
        )
    filename = f"{snapshot.account.username}-snapshot{snapshot.id}-{which}.csv"
    return Response(
        buf.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@bp.route("/accounts/<int:account_id>/compare")
def compare(account_id: int):
    account = db.session.get(Account, account_id) or abort(404)
    snapshots = sorted(account.snapshots, key=lambda s: s.taken_at)
    if len(snapshots) < 2:
        flash("Need at least two snapshots to compare.", "error")
        return redirect(url_for("main.account_detail", account_id=account.id))

    try:
        older_id = int(request.args.get("older", snapshots[0].id))
        newer_id = int(request.args.get("newer", snapshots[-1].id))
    except (TypeError, ValueError):
        abort(400)

    older = db.session.get(Snapshot, older_id) or abort(404)
    newer = db.session.get(Snapshot, newer_id) or abort(404)
    if older.account_id != account.id or newer.account_id != account.id:
        abort(404)

    result = compare_snapshots(older, newer)
    return render_template(
        "compare.html",
        account=account,
        snapshots=snapshots,
        older=older,
        newer=newer,
        result=result,
    )
