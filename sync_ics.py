#!/usr/bin/env python3
"""
sync_ics.py — Fetches Yedion ICS and generates data/events.json
Run by GitHub Actions every hour.
"""

import os
import json
import re
import requests
from datetime import datetime, timezone
from collections import defaultdict

ICS_URL = os.environ.get("ICS_URL", "")

# Course name → key mapping
COURSE_MAP = {
    "סדנת תחקיר": "tachkir",
    "סדנת תסריט לוקיישן": "location",
    "תסריט לוקיישן": "location",
    "הסיפור הקצר": "short_story",
    "סדנת הסיפור הקצר": "short_story",
    "מבוא לקולנוע ישראלי": "israeli_cinema",
    "קולנוע ישראלי": "israeli_cinema",
    "תולדות הקולנוע": "film_history",
    "סדרת ילדים ונוער": "kids_series",
    "ילדים ונוער": "kids_series",
    "עושים סצינות": "scenes",
    "עושים סצנות": "scenes",
    "כתיבת סדרות רשת": "web_series",
    "סדרות רשת": "web_series",
    "בימוי לתסריטאים": "directing",
}

# Parallel course pairs: (course_key, parallel_key, group_b_hour, group_a_hour)
PARALLEL_PAIRS = [
    ("location",    "short_story", 12, 14),
    ("short_story", "location",   14, 12),
    ("kids_series", "scenes",     13, 15),
    ("scenes",      "kids_series",15, 13),
    ("web_series",  "directing",  17, 18),
    ("directing",   "web_series", 18, 17),
]


def parse_dt(s):
    """Parse ICS datetime string to ISO format."""
    s = s.strip()
    if "T" in s:
        try:
            return datetime.strptime(s, "%Y%m%dT%H%M%S").isoformat()
        except Exception:
            return None
    else:
        try:
            return datetime.strptime(s, "%Y%m%d").date().isoformat()
        except Exception:
            return None


def get_field(event_text, field):
    pattern = rf"^{field}[^:]*:(.*)"
    m = re.search(pattern, event_text, re.MULTILINE)
    return m.group(1).strip() if m else ""


def map_course(title):
    for k, v in COURSE_MAP.items():
        if k in title:
            return v
    return None


def get_group(course_key, start_iso):
    """Determine which group has this course at this time (B = ICS schedule)."""
    if not start_iso:
        return "both"
    try:
        hour = datetime.fromisoformat(start_iso).hour
    except Exception:
        return "both"
    for ck, pk, b_hour, a_hour in PARALLEL_PAIRS:
        if course_key == ck and hour == b_hour:
            return "B"
        if course_key == ck and hour == a_hour:
            return "A"
    return "both"


def fetch_ics(url):
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    # Force UTF-8 — Yedion sends UTF-8 but without charset in headers
    r.encoding = 'utf-8'
    return r.text


def parse_events(ics_text):
    raw_events = ics_text.split("BEGIN:VEVENT")[1:]
    events = []

    for raw in raw_events:
        uid = get_field(raw, "UID")
        summary = get_field(raw, "SUMMARY")
        description = get_field(raw, "DESCRIPTION")
        location = get_field(raw, "LOCATION")
        status = get_field(raw, "STATUS")

        # Parse start/end — handle TZID variant
        start_raw = re.search(r"DTSTART[^:]*:(.*)", raw)
        end_raw = re.search(r"DTEND[^:]*:(.*)", raw)
        start_str = start_raw.group(1).strip() if start_raw else ""
        end_str = end_raw.group(1).strip() if end_raw else ""

        start_iso = parse_dt(start_str)
        end_iso = parse_dt(end_str)

        if not start_iso:
            continue

        # Duration in minutes
        try:
            s = datetime.fromisoformat(start_iso)
            e = datetime.fromisoformat(end_iso) if end_iso else s
            duration_min = int((e - s).seconds / 60)
        except Exception:
            duration_min = 0

        # Clean title
        title = summary.replace("שיעור בנושא ", "").strip()

        # Determine type
        if "פרונטלי" in description:
            event_type = "lecture"
        elif "סדנא" in description:
            event_type = "workshop"
        else:
            event_type = "special"

        # Is all-day?
        is_allday = duration_min >= 300 or event_type == "special"

        # Map to course
        course_key = map_course(title)

        # Status
        logistic_status = "confirmed"
        if status == "CANCELLED":
            logistic_status = "cancelled"

        group = get_group(course_key, start_iso) if course_key else "both"

        events.append({
            "uid": uid,
            "title": title,
            "course_key": course_key,
            "type": event_type,
            "start": start_iso,
            "end": end_iso,
            "duration_min": duration_min,
            "location": location,
            "status": logistic_status,
            "is_allday": is_allday,
            "group": group,
            "lesson_number": None,  # filled below
        })

    # Sort by start time
    events.sort(key=lambda x: x["start"] or "")

    # Assign lesson numbers per course
    lesson_counter = defaultdict(int)
    for ev in events:
        if ev["course_key"] and not ev["is_allday"]:
            lesson_counter[ev["course_key"]] += 1
            ev["lesson_number"] = lesson_counter[ev["course_key"]]

    return events


def main():
    if not ICS_URL:
        print("❌ ICS_URL env var not set. Using fallback data.")
        # Keep existing events.json if it exists
        return

    print(f"📡 Fetching ICS from Yedion...")
    try:
        ics_text = fetch_ics(ICS_URL)
    except Exception as e:
        print(f"❌ Failed to fetch ICS: {e}")
        return

    events = parse_events(ics_text)
    print(f"✅ Parsed {len(events)} events")

    output_path = os.path.join(os.path.dirname(__file__), "data", "events.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    meta = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "total_events": len(events),
        "source": "Yedion ICS"
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({"meta": meta, "events": events}, f, ensure_ascii=False, indent=2)

    print(f"💾 Saved to {output_path}")


if __name__ == "__main__":
    main()
