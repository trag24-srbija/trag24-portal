#!/usr/bin/env python3
"""Validated Make webhook envelope for TRAG 24 morning programme.

A manual run is preview-only unless approve_publish is explicitly enabled.
The schedule may publish only if a real MP4 and >=1 multi-source story exist.
"""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Belgrade")
REPO = "trag24-srbija/trag24-portal"


def build(day, meta, video, run_id, approved=False):
    if meta.get("datum") != day.isoformat() or meta.get("program") != "Srbija se budi":
        raise ValueError("Morning metadata date/program mismatch")
    if not run_id.isdecimal() or int(run_id) < 1:
        raise ValueError("Missing GitHub Actions run ID")
    if video.name != "SRBIJA-SE-BUDI.mp4" or not video.is_file() or video.stat().st_size < 20000:
        raise ValueError("Expected generated morning MP4")
    topics = meta.get("teme")
    if not isinstance(topics, list) or not (1 <= len(topics) <= 3):
        raise ValueError("Expected 1-3 morning topics")
    for topic in topics:
        if not isinstance(topic, dict):
            raise ValueError("Invalid morning topic")
        heading = str(topic.get("title") or "").strip()
        summary = str(topic.get("summary") or "").strip()
        sources = topic.get("urls") or []
        hosts = {urlparse(u).netloc.lower().removeprefix("www.") for u in sources
                 if isinstance(u, str) and u.startswith("https://")}
        if not heading or not summary or len(hosts) < 2:
            raise ValueError("Morning topic must have a headline, summary, two original source URLs")
        if "TEHNICKA PROBA" in heading.upper() or "TEHNIČKA PROBA" in heading.upper():
            raise ValueError("Never publish a test headline")

    key = f"trag24:{'LIVE' if approved else 'PREVIEW'}:{day.isoformat()}:0800"
    lines = "\n".join(f"{idx}. {t['title']}" for idx, t in enumerate(topics, 1))
    caption = (f"TRAG 24 | SRBIJA SE BUDI\nJutarnji pregled — {day:%d.%m.%Y.}\n\n"
               f"{lines}\n\nDetalji i izvori: https://www.trag24.rs\n"
               "Pregled objavljenih izvora; navodi nisu nezavisno potvrđeni.\n"
               "#TRAG24 #SrbijaSeBudi #Vesti")
    planned = dt.datetime.combine(day, dt.time(8, 0), tzinfo=TZ)
    url = (f"https://github.com/{REPO}/releases/download/"
           f"srbija-se-budi-{day.isoformat()}/{video.name}") if approved else None
    sources = list(dict.fromkeys(u for t in topics for u in t["urls"]))
    return {
        "schema": "trag24.make.premium.v1",
        "mode": "PRODUCTION" if approved else "PREVIEW_ONLY",
        "publish_enabled": bool(approved),
        "test_only": not bool(approved),
        "date": day.isoformat(),
        "timezone": "Europe/Belgrade",
        "repository": REPO,
        "github_run_id": run_id,
        "artifact_name": "TRAG24-SRBIJA-SE-BUDI",
        "content_ready": 1,
        "posts": [{
            "id": key,
            "program": "0800",
            "title": "SRBIJA SE BUDI",
            "event_date": day.isoformat(),
            "content_date": day.isoformat(),
            "timezone": "Europe/Belgrade",
            "planned_local_time": planned.isoformat(),
            "headline": "SRBIJA SE BUDI — " + topics[0]["title"],
            "caption": caption,
            "media_file": video.name,
            "cover_file": "slide-0.png",
            "media_url": url,
            "duration_seconds": round(2.4 + 7.6 * len(topics), 1),
            "video_sha256": hashlib.sha256(video.read_bytes()).hexdigest(),
            "sources": sources,
            "editorial_status": "READY" if approved else "HOLD_REVIEW",
            "publishing_enabled": bool(approved),
            "destinations": {
                p: {"idempotency_key": f"{key}:{p}",
                    "status": "READY" if approved else "HOLD_REVIEW"}
                for p in ("facebook", "instagram", "tiktok")
            }
        }],
        "notice": "Make must verify the MP4 and idempotency key before public publishing."
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--date", required=True)
    p.add_argument("--metadata", required=True)
    p.add_argument("--video", required=True)
    p.add_argument("--github-run-id", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--approved", action="store_true")
    args = p.parse_args()
    day = dt.date.fromisoformat(args.date)
    meta = json.loads(Path(args.metadata).read_text(encoding="utf-8"))
    payload = build(day, meta, Path(args.video), args.github_run_id, args.approved)
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("MORNING MAKE PACKET OK -", "PRODUCTION" if args.approved else "PREVIEW_ONLY")


if __name__ == "__main__":
    main()
