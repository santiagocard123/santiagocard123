"""Build a static activity card from Jottysng's public GitHub events."""

from __future__ import annotations

import json
import os
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from xml.sax.saxutils import escape


USER = "Jottysng"
DAYS = 30
OUTPUT = Path(__file__).resolve().parents[1] / "metrics.activity.svg"
NOW = datetime.now(timezone.utc)
START = NOW - timedelta(days=DAYS - 1)
EVENT_NAMES = {
    "PushEvent": "push",
    "PullRequestEvent": "pull request",
    "IssuesEvent": "issue",
    "ReleaseEvent": "release",
    "CreateEvent": "new branch or tag",
    "IssueCommentEvent": "comment",
}


def public_events() -> list[dict]:
    token = os.environ.get("GH_TOKEN", "")
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "Jottysng-profile-activity",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    events = []
    for page in range(1, 4):
        url = f"https://api.github.com/users/{USER}/events/public?per_page=100&page={page}"
        with urlopen(Request(url, headers=headers), timeout=20) as response:
            batch = json.load(response)
        if not batch:
            break
        for event in batch:
            when = datetime.fromisoformat(event["created_at"].replace("Z", "+00:00"))
            if when >= START:
                events.append(event)
        if datetime.fromisoformat(batch[-1]["created_at"].replace("Z", "+00:00")) < START:
            break
    return events


def build_svg(events: list[dict]) -> str:
    dates = [(NOW - timedelta(days=DAYS - 1 - index)).date() for index in range(DAYS)]
    counts = Counter(datetime.fromisoformat(event["created_at"].replace("Z", "+00:00")).date() for event in events)
    values = [counts[date] for date in dates]
    ceiling = max(1, max(values))
    points = [(26 + index * 428 / (DAYS - 1), 122 - value * 53 / ceiling) for index, value in enumerate(values)]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    area = "M26 122 L" + " L".join(f"{x:.1f} {y:.1f}" for x, y in points) + " L454 122 Z"
    active_days = sum(value > 0 for value in values)
    latest = max(events, key=lambda event: event["created_at"], default=None)
    if latest:
        when = datetime.fromisoformat(latest["created_at"].replace("Z", "+00:00"))
        action = EVENT_NAMES.get(latest["type"], latest["type"].removesuffix("Event").lower())
        repo = latest.get("repo", {}).get("name", "GitHub")
        detail = f"Latest · {when.strftime('%b %d')} · {action} · {repo}"
    else:
        detail = "No public events in the last 30 days"
    detail = escape(detail[:68] + ("…" if len(detail) > 68 else ""))
    total_label = f"{len(events)} public event{'s' if len(events) != 1 else ''}"
    day_label = f"{active_days} active day{'s' if active_days != 1 else ''}"
    label = escape(f"Activity Pulse: {total_label} and {day_label} in the last 30 days")
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="480" height="180" viewBox="0 0 480 180" role="img" aria-label="{label}">
  <defs>
    <linearGradient id="pulse-fill" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#58a6ff" stop-opacity=".28"/>
      <stop offset="1" stop-color="#58a6ff" stop-opacity="0"/>
    </linearGradient>
  </defs>
  <rect x=".5" y=".5" width="479" height="179" rx="12" fill="#0d1117" stroke="#30363d"/>
  <g font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace">
    <text x="24" y="31" fill="#e6edf3" font-size="15" font-weight="700">ACTIVITY PULSE</text>
    <circle cx="411" cy="25" r="4" fill="#3fb950"/>
    <text x="422" y="29" fill="#8b949e" font-size="10">PUBLIC</text>
    <path d="M24 46H456" stroke="#30363d"/>
    <path d="M26 94H454 M26 122H454" stroke="#21262d" stroke-dasharray="3 5"/>
    <path d="{area}" fill="url(#pulse-fill)"/>
    <polyline points="{line}" fill="none" stroke="#58a6ff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
    <circle cx="{points[-1][0]:.1f}" cy="{points[-1][1]:.1f}" r="4" fill="#58a6ff" stroke="#0d1117" stroke-width="2"/>
    <text x="26" y="61" fill="#8b949e" font-size="10">LAST 30 DAYS</text>
    <text x="24" y="147" fill="#e6edf3" font-size="12" font-weight="600">{escape(total_label)}</text>
    <text x="456" y="147" text-anchor="end" fill="#8b949e" font-size="11">{escape(day_label)}</text>
    <text x="24" y="166" fill="#8b949e" font-size="10">{detail}</text>
  </g>
</svg>
'''


if __name__ == "__main__":
    OUTPUT.write_text(build_svg(public_events()), encoding="utf-8")
    print(f"Updated {OUTPUT.name} with public events from the last {DAYS} days")
