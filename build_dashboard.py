#!/usr/bin/env python3
"""Combine data.json and dashboard_template.html into dashboard.html.

Run after fetch_insights.py: python3 build_dashboard.py
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
data = json.loads((HERE / "data.json").read_text())
template = (HERE / "dashboard_template.html").read_text()

# Escape characters that could close the script tag or be read as markup.
payload = (json.dumps(data, ensure_ascii=False)
           .replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026"))
out = HERE / "dashboard.html"
out.write_text(template.replace("__DATA__", payload))
print(f"Wrote {out} ({out.stat().st_size // 1024} KB)")
