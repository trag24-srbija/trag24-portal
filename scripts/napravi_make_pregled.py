#!/usr/bin/env python3
"""TRAG 24 -> Make: BEZBEDAN spisak MP4 za pregled, ne za javno objavljivanje.

Ne šalje webhooks, ne objavljuje, ne izmišlja javni media_url.
GitHub Actions artifact mora kasnije biti preuzet autorizovanim GitHub pristupom
ili video hostovan na odobrenom HTTPS medijskom hostingu.
"""
import argparse
import datetime as dt
import hashlib
import json
import re
import subprocess
from pathlib import Path
from urllib.parse import quote
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Belgrade")
REPO = "trag24-srbija/trag24-portal"
BASE = "https://trag24-srbija.github.io/trag24-portal/"
PROGRAMS = {
    "0800": ("SRBIJA SE BUDI", "08:00", 15),
    "1100": ("VEROVALI ILI NE", "11:00", 15),
    "1400": ("NOVAC I ŽIVOT", "14:00", 15),
    "1700": ("PITANJE DANA", "17:00", 15),
    "2000": ("VESTI U 20", "20:00", 20),
    "2300": ("ARENA – NOĆNI IZAZOV", "23:00", 15),
}
CHANNELS = ("instagram", "facebook", "tiktok")


def metadata(path):
    return json.loads(subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries",
         "format=duration:stream=codec_name,codec_type,width,height",
         "-of", "json", str(path)],
        text=True,
    ))


def checksum(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1048576), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_file(path, duration):
    if not path.is_file() or not path.stat().st_size:
        raise ValueError(f"Nedostaje finalni MP4 sa muzikom: {path}")
    info = metadata(path)
    tracks = info.get("streams", [])
    videos = [x for x in tracks if x.get("codec_type") == "video"]
    audios = [x for x in tracks if x.get("codec_type") == "audio"]
    if len(videos) != 1 or len(audios) != 1:
        raise ValueError(f"Neispravni audio/video tokovi: {path}")
    if (videos[0].get("width"), videos[0].get("height")) != (1080, 1920):
        raise ValueError(f"Neispravan 9:16 format: {path}")
    if videos[0].get("codec_name") != "h264" or audios[0].get("codec_name") != "aac":
        raise ValueError(f"Neispravan MP4 kodek: {path}")
    measured = float(info["format"]["duration"])
    if measured < 15 or abs(measured - duration) > 0.12:
        raise ValueError(f"Neispravno trajanje: {path} ({measured})")
    return round(measured, 2)


def caption(item, program, label):
    title = re.sub(r"\s+", " ", str(item.get("naslov") or "")).strip()
    if not title or len(title) > 130 or any(x in title for x in "<>"):
        raise ValueError("Neispravan ili predug naslov.")
    if program == "1700":
        return f"TRAG 24 | PITANJE DANA\n\n{title}\n\nPišite svoje mišljenje u komentarima.\n#TRAG24 #PitanjeDana"
    if program == "2300":
        return f"TRAG 24 | ARENA\n\n{title}\n\nPogledajte ponuđene odgovore i igrajte Arenu:\n{BASE}arena/\n#TRAG24 #Arena"
    old = item.get("datum_vesti") or item.get("datum")
    source_date = f"\nAnaliza od: {old}" if old else ""
    aid = str(item.get("id_analize") or "")
    article_url = BASE + "analiza/" + quote(aid, safe="") + ".html" if re.fullmatch(r"[A-Za-z0-9_-]{5,100}", aid) else BASE
    return (
        f"TRAG 24 | {label}\n\n{title}{source_date}\n\n"
        f"Analiza i navedeni izvori: {article_url}\n"
        "Pregled javnih izvora; navodi nisu nužno nezavisno potvrđeni.\n"
        "#TRAG24 #Vesti #Srbija"
    )


def build(raw, folder, date, run_id):
    dt.date.fromisoformat(date)
    items = []
    seen = set()
    for item in raw:
        program = str(item.get("program", ""))
        if program not in PROGRAMS:
            raise ValueError(f"Nepoznat program: {program}")
        if program in seen:
            raise ValueError(f"Dupli program u istom danu: {program}")
        seen.add(program)
        if str(item.get("datum")) != date:
            raise ValueError(f"Datum u analizi se ne poklapa sa danom izrade: {program}")
        label, clock, expected = PROGRAMS[program]
        timestamp = dt.datetime.fromisoformat(f"{date}T{clock}").replace(tzinfo=TZ)
        mp4 = folder / f"{program}_reel_sa_muzikom.mp4"
        cover = folder / f"{program}_cover.png"
        if not cover.is_file():
            raise ValueError(f"Nedostaje naslovnica: {cover}")
        duration = validate_file(mp4, expected)
        caption_text = caption(item, program, label)
        idkey = f"trag24:{date}:{program}"
        # Isti idempotency ključ po platformi, nezavisan od broja GitHub testa.
        channel_keys = {
            channel: {"idempotency_key": f"{idkey}:{channel}", "status": "HOLD_REVIEW"}
            for channel in CHANNELS
        }
        entry = {
            "id": idkey,
            "program": program,
            "title": label,
            "event_date": date,
            "content_date": item.get("datum_vesti") or date,
            "timezone": "Europe/Belgrade",
            "planned_local_time": timestamp.isoformat(),
            "headline": item["naslov"],
            "caption": caption_text,
            "media_file": f"izlaz/{mp4.name}",
            "cover_file": f"izlaz/{cover.name}",
            "media_url": None,  # NIJE direktan javni URL; ne izmišljati ga.
            "duration_seconds": duration,
            "video_sha256": checksum(mp4),
            "analysis_id": item.get("id_analize"),
            "sources": item.get("izvori", []),
            "editorial_status": "NEPROVERENO",
            "publishing_enabled": False,
            "destinations": channel_keys,
        }
        items.append(entry)
    items.sort(key=lambda x: x["program"])
    return {
        "schema": "trag24.make.preview.v1",
        "mode": "PREVIEW_ONLY",
        "publish_enabled": False,
        "date": date,
        "timezone": "Europe/Belgrade",
        "repository": REPO,
        "branch": "feature/trag24-reels-six-programs-20261121",
        "github_run_id": str(run_id or ""),
        "artifact_name": "trag24-reels-preview",
        "artifact_fetch": "requires_authenticated_github_actions_download",
        "content_ready": len(items),
        "posts": items,
        "notice": "NIJE za direktno slanje u objavu; nema javnih media URL-ova, provera vesti je odvojena.",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--content", default="reels_preview/dnevne_objave.json")
    parser.add_argument("--videos", default="reels_preview/izlaz")
    parser.add_argument("--output", default="reels_preview/make_pregled.json")
    parser.add_argument("--datum", required=True)
    parser.add_argument("--run-id", default="")
    args = parser.parse_args()
    raw = json.loads(Path(args.content).read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("Očekivana lista dnevnih objava.")
    data = build(raw, Path(args.videos), args.datum, args.run_id)
    dest = Path(args.output)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"MAKE PREVIEW: {len(data['posts'])} pripremljenih pozicija; 0 javnih objava.")


if __name__ == "__main__":
    main()
