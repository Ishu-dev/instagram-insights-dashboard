# Instagram insights dashboard

A small Python tool that pulls profile, post and account insights from the Instagram API (Instagram Login) for a Creator or Business account and builds a single self-contained `dashboard.html`. No third-party packages, only the standard library.

I built it to see which of my own posts earned reach and why, without paying for an analytics tool.

## What the dashboard shows

- Account reach per day for the last 30 days, plus 30-day totals for views, accounts engaged, interactions and profile views
- Every post ranked by a metric you choose
- Engagement mix per post (likes, comments, shares, saves)
- Average reach and engagement rate by format (Reel, image, carousel)
- A table of all posts with thumbnails

## Setup

1. Create a Meta app with the Instagram use case and generate a long-lived access token for your account. The token lasts about 60 days.
2. Copy `.env.example` to `.env` and fill in the three values.
3. Run:

```
python3 fetch_insights.py
python3 build_dashboard.py
open dashboard.html
```

`fetch_insights.py` writes `data.json` and a `thumbs/` folder. `build_dashboard.py` combines them with `dashboard_template.html`.

## Notes

- The token is read from `.env` only. The script removes anything token-shaped from errors and from `data.json`, and it follows pagination cursors itself so the token-bearing `next` URL that Instagram returns is never used or printed.
- `.env`, `data.json`, `thumbs/` and `dashboard.html` are git-ignored because they hold account data.
- Posts made before an account became professional return likes and comments only, with no reach or views. That is an API limit, not an error. In my account, 5 of 14 posts were in that group.
- If one metric is rejected for a post, the script retries each metric on its own and records the failure under `problems` in `data.json`.

## Files

| File | Purpose |
| --- | --- |
| `fetch_insights.py` | Calls the Graph API, saves `data.json` and thumbnails |
| `build_dashboard.py` | Injects the data into the HTML template |
| `dashboard_template.html` | The dashboard page (charts drawn in the browser) |
