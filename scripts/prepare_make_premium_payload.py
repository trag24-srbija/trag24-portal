#!/usr/bin/env python3
"""Create the TRAG 24 Make webhook envelope for ONE premium video.

Defaults to review-only. Does not publish or contact Make itself.
"""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Belgrade")
VALID = {"11": "1100", "14": "1400", "17": "1700", "23": "2300"}
BASE = "https://trag24-srbija.github.io/trag24-portal/"


def build(program, day, metadata, video, run_id, approved=False):
    if program not in VALID:
        raise ValueError("Unexpected programme")
    if not run_id.isdecimal() or int(run_id) < 1:
        raise ValueError("Missing GitHub run ID")
    if not video.is_file() or video.suffix != ".mp4" or video.stat().st_size < 20000:
        raise ValueError("Expected a non-empty MP4")
    if metadata.get("datum") != day.isoformat() or metadata.get("sat") != program + ":00":
        raise ValueError("Wrong programme date or hour")
    story = metadata.get("vest")
    if not isinstance(story, dict) or not story.get("title"):
        raise ValueError("Missing story")
    sources = story.get("sources") or []
    euro = story.get("euro_nbs") if program == "14" else None
    official_rate_only = (
        euro and story["title"] == "Zvanični srednji kurs evra"
        and sources == ["nbs.rs"]
        and euro.get("source") == "https://webappcenter.nbs.rs/ExchangeRateWebApp/ExchangeRate/CurrentMiddleRate"
    )
    if program in {"11", "14"} and len(set(sources)) < 2 and not official_rate_only:
        raise ValueError("A news Reel must have two separate sources")
    text = str(story.get("summary") or "").strip()
    if not text:
        raise ValueError("Missing meaningful story context")
    if "PROBA" in str(story["title"]).upper() or "TEST" in str(story["title"]).upper():
        raise ValueError("Never publish mock headlines")

    code = VALID[program]
    key = f"trag24:{'LIVE' if approved else 'PREVIEW'}:{day.isoformat()}:{code}"
    heading = str(story["title"])
    title = metadata.get("program", "TRAG 24")
    if program == "17":
        caption = f"TRAG 24 | PITANJE DANA\n\n{heading}\n\n{BASE}\n#TRAG24 #PitanjeDana"
    elif program == "23":
        caption = f"TRAG 24 | ARENA\n\n{heading}\n\nIgraj kviz: {BASE}arena/\n#TRAG24 #Arena"
    else:
        caption = (f"TRAG 24 | {title}\n\n{heading}\n\n{BASE}"
                   f"\nPregled objavljenih izvora; navodi nisu nezavisno potvrđeni."
                   f"\n#TRAG24 #Vesti")
    if euro:
        rate_note = f'{euro["title"]}\n{euro["detail"]}\n{euro["source"]}'
        if official_rate_only:
            caption = f"TRAG 24 | {title}\n\n{heading}\n\n{rate_note}\n\n{BASE}\n#TRAG24"
        else:
            caption += "\n\n" + rate_note
    digest = hashlib.sha256(video.read_bytes()).hexdigest()
    planned = dt.datetime.combine(day, dt.time(int(program), 0), tzinfo=TZ)
    return {
        "schema": "trag24.make.premium.v1",
        "mode": "PRODUCTION" if approved else "PREVIEW_ONLY",
        "publish_enabled": bool(approved),
        "test_only": not bool(approved),
        "date": day.isoformat(),
        "timezone": "Europe/Belgrade",
        "repository": "trag24-srbija/trag24-portal",
        "github_run_id": run_id,
        "artifact_name": f"TRAG24-PREMIUM-{program}",
        "content_ready": 1,
        "posts": [{
            "id": key,
            "program": code,
            "title": title,
            "event_date": day.isoformat(),
            "content_date": story.get("published_date") or day.isoformat(),
            "timezone": "Europe/Belgrade",
            "planned_local_time": planned.isoformat(),
            "headline": heading,
            "caption": caption,
            "media_file": video.name,
            "cover_file": video.with_suffix(".png").name,
            "media_url": (f"https://github.com/trag24-srbija/trag24-portal/releases/"
                          f"download/premium-{program}-{day.isoformat()}/{video.name}")
                         if approved else None,
            "duration_seconds": 15,
            "video_sha256": digest,
            "sources": sources,
            "editorial_status": "READY" if approved else "HOLD_REVIEW",
            "publishing_enabled": bool(approved),
            "destinations": {
                platform: {"idempotency_key": f"{key}:{platform}", "status": "READY" if approved else "HOLD_REVIEW"}
                for platform in ("facebook", "instagram", "tiktok")
            },
        }],
        "notice": "A Make module must independently validate file type and deduplicate before public publishing.",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--program", choices=sorted(VALID), required=True)
    parser.add_argument("--date", required=True)
    parser.add_argument("--metadata", required=True)
    parser.add_argument("--video", required=True)
    parser.add_argument("--github-run-id", required=True)
    parser.add_argument("--approved", action="store_true")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    day = dt.date.fromisoformat(args.date)
    metadata = json.loads(Path(args.metadata).read_text(encoding="utf-8"))
    envelope = build(args.program, day, metadata, Path(args.video), args.github_run_id, args.approved)
    target = Path(args.out)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(envelope, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"MAKE PACKET OK: {args.program}:00 - " + ("READY" if args.approved else "PREVIEW_ONLY"))


if __name__ == "__main__":
    main()
