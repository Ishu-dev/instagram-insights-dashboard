#!/usr/bin/env python3
"""Pull profile, post and account insights for the Instagram account in .env.

Writes data.json and thumbs/<media_id>.jpg. The access token is read from .env
and is never written to disk or printed. Run: python3 fetch_insights.py
"""
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = "https://graph.instagram.com"


def load_env(path):
    env = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


ENV = load_env(HERE / ".env")
TOKEN = ENV.get("IG_ACCESS_TOKEN", "")
USER_ID = ENV.get("IG_USER_ID", "")
if not TOKEN or not USER_ID:
    sys.exit("IG_ACCESS_TOKEN and IG_USER_ID must both be set in .env")


def scrub(text):
    """Remove anything token-shaped before it can reach the screen or a file."""
    text = text.replace(TOKEN, "<token>")
    return re.sub(r"access_token=[^&\s\"']+", "access_token=<token>", text)


def get(path, **params):
    """GET a Graph endpoint. Returns (json, None) or (None, error_message)."""
    params["access_token"] = TOKEN
    url = f"{BASE}/{path}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            return json.load(resp), None
    except urllib.error.HTTPError as err:
        try:
            body = json.load(err)
            message = body.get("error", {}).get("message", str(body))
        except Exception:
            message = f"HTTP {err.code}"
        return None, scrub(message)
    except Exception as err:  # network trouble
        return None, scrub(str(err))


def metric_values(payload):
    out = {}
    for item in (payload or {}).get("data", []):
        values = item.get("values") or []
        if values and "value" in values[0]:
            out[item["name"]] = values[0]["value"]
        elif "total_value" in item:
            out[item["name"]] = item["total_value"].get("value")
    return out


def media_insights(media):
    base = ["reach", "views", "likes", "comments", "shares", "saved", "total_interactions"]
    if media.get("media_product_type") == "REELS":
        base += ["ig_reels_avg_watch_time", "ig_reels_video_view_total_time"]
    payload, error = get(f"{media['id']}/insights", metric=",".join(base))
    if payload is not None:
        return metric_values(payload), []
    # One bad metric fails the whole call, so retry each on its own.
    got, errors = {}, [error]
    for name in base:
        one, err = get(f"{media['id']}/insights", metric=name)
        if one is not None:
            got.update(metric_values(one))
        else:
            errors.append(f"{name}: {err}")
    return got, errors


def download(url, dest):
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            dest.write_bytes(resp.read())
        return True
    except Exception:
        return False


def main():
    problems = []

    profile, err = get(
        "me",
        fields="user_id,username,name,account_type,followers_count,follows_count,media_count",
    )
    if profile is None:
        sys.exit(f"Profile call failed: {err}")

    # Posts, newest first. Follow the cursor ourselves so the token-bearing
    # "next" URL that Instagram returns is never used or shown.
    media, after = [], None
    fields = ("id,caption,media_type,media_product_type,timestamp,permalink,"
              "like_count,comments_count,thumbnail_url,media_url")
    while True:
        params = {"fields": fields, "limit": 50}
        if after:
            params["after"] = after
        page, err = get(f"{USER_ID}/media", **params)
        if page is None:
            sys.exit(f"Media call failed: {err}")
        media.extend(page.get("data", []))
        after = page.get("paging", {}).get("cursors", {}).get("after")
        if not page.get("paging", {}).get("next") or not after:
            break

    thumbs = HERE / "thumbs"
    thumbs.mkdir(exist_ok=True)
    for index, item in enumerate(media, 1):
        insights, errors = media_insights(item)
        item["insights"] = insights
        if errors:
            problems.append({"media": item["id"], "errors": errors})
        src = item.get("thumbnail_url") or item.get("media_url")
        item["thumb"] = None
        if src and download(src, thumbs / f"{item['id']}.jpg"):
            item["thumb"] = f"thumbs/{item['id']}.jpg"
        # Signed CDN links expire and are not needed once the image is saved.
        item.pop("thumbnail_url", None)
        item.pop("media_url", None)
        print(f"  post {index}/{len(media)}: {len(insights)} metrics")

    # Account level, last 30 days.
    now = int(time.time())
    window = {"since": now - 30 * 86400, "until": now}
    reach_payload, err = get(f"{USER_ID}/insights", metric="reach", period="day", **window)
    daily_reach = []
    if reach_payload:
        for item in reach_payload.get("data", []):
            for v in item.get("values", []):
                daily_reach.append({"date": v["end_time"][:10], "value": v["value"]})
    else:
        problems.append({"account_reach": err})

    totals = {}
    for name in ["views", "accounts_engaged", "total_interactions", "profile_views"]:
        payload, err = get(f"{USER_ID}/insights", metric=name, period="day",
                           metric_type="total_value", **window)
        if payload:
            totals.update(metric_values(payload))
        else:
            problems.append({f"account_{name}": err})

    data = {
        "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "profile": profile,
        "posts": media,
        "account": {"daily_reach": daily_reach, "totals_30d": totals},
        "problems": problems,
    }
    out = HERE / "data.json"
    out.write_text(scrub(json.dumps(data, ensure_ascii=False, indent=2)))
    print(f"Saved {len(media)} posts, {len(daily_reach)} days of reach to {out.name}")
    if problems:
        print(f"{len(problems)} metric call(s) returned errors; see 'problems' in data.json")


if __name__ == "__main__":
    main()
