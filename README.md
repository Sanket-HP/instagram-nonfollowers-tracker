# Instagram Non-Followers Tracker

A small Flask + SQLite web app that tells you which Instagram accounts you
follow but don't follow you back — and the other way around. Data is imported
from Instagram's official **Download Your Information** export (or pasted
manually); the app does **not** scrape Instagram or automate any account
actions, so you stay within Instagram's Terms of Service.

## Features

- Track multiple Instagram accounts.
- Each import creates a timestamped **snapshot** so you can see how your graph
  changes over time.
- Two ways to import each list (followers / following):
  - Upload the JSON file from Instagram's *Download Your Information* export
    (`followers_1.json`, `following.json`).
  - Paste usernames one per line (`@handle`, `handle`, or profile URLs are all
    accepted).
- Per-snapshot views:
  - **Not following you back** — users you follow who don't follow you.
  - **You don't follow back** — users who follow you but you don't follow.
  - **Mutuals**.
- **Compare** any two snapshots to see new followers, unfollowers, and users
  you started/stopped following.
- Export any list as CSV.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run the dev server:
flask --app wsgi run --debug
# or
python wsgi.py
```

Then open <http://127.0.0.1:5000>.

The SQLite database lives in `instance/tracker.sqlite` by default. Override
with the `DATABASE_URL` environment variable if you want a different path.

## Getting your Instagram data

1. In the Instagram app or web: **Settings → Accounts Center → Your
   information and permissions → Download your information**.
2. Request a download of *Followers and following*, format **JSON**.
3. When the email arrives, download and unzip the archive.
4. You'll find `followers_1.json` and `following.json` inside. Upload them to a
   snapshot in this app.

## Running tests

```bash
pip install pytest
pytest
```

## Project layout

```
app/
  __init__.py      # Flask app factory
  models.py        # SQLAlchemy models (Account, Snapshot, FollowEntry)
  importers.py     # JSON + plain-text parsers
  services.py     # diffing + bulk insert
  routes.py        # HTTP routes
  templates/       # Jinja2 templates
  static/style.css # minimal CSS
wsgi.py            # entry point
tests/             # pytest suite
```

## Disclaimer

This tool is not affiliated with or endorsed by Instagram or Meta. It is a
personal productivity utility that operates strictly on data you have
explicitly exported from your own account.
