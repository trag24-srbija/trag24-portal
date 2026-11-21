#!/usr/bin/env python3
"""TRAG 24: dodaj autorizovanu muziku na vec generisane, neme Reels klipove.

Rad je lokalni u okviru GitHub Actions; nema objavljivanja, slanja podataka ni API-ja.
Ne menja originalne neme MP4 fajlove. Ovo ne koristiti za klipove sa naratorom.
"""
import argparse
import json
import subprocess
from pathlib import Path

PROGRAMS = ("0800", "1100", "1400", "1700", "2000", "2300")


def probe(path):
    raw = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries",
         "format=duration:stream=codec_type", "-of", "json", str(path)],
        text=True,
    )
    return json.loads(raw)


def add_music(video: Path, music: Path):
    metadata = probe(video)
    streams = metadata.get("streams", [])
    if "video" not in [s.get("codec_type") for s in streams]:
        raise ValueError(f"Nedostaje video: {video}")
    if "audio" in [s.get("codec_type") for s in streams]:
        raise ValueError(f"Video vec ima zvuk – ne brisem glas/naraciju: {video}")
    duration = float(metadata["format"]["duration"])
    if duration < 14.9:
        raise ValueError(f"Reels je kraci od 15 sekundi: {video}")
    if float(probe(music)["format"]["duration"]) < duration:
        raise ValueError("Muzicki zapis je kraci od Reels-a; odbijam petlju.")
    output = video.with_name(video.stem + "_sa_muzikom.mp4")
    fade_out = max(0, duration - 1.4)
    audio_filter = (
        "volume=0.73,"
        "afade=t=in:st=0:d=0.35,"
        f"afade=t=out:st={fade_out:.2f}:d=1.4,"
        "alimiter=limit=0.92"
    )
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-i", str(video), "-i", str(music),
         "-map", "0:v:0", "-map", "1:a:0",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-ar", "48000",
         "-af", audio_filter, "-t", str(duration),
         "-movflags", "+faststart", str(output)],
        check=True,
    )
    result = probe(output)
    output_types = {s.get("codec_type") for s in result.get("streams", [])}
    out_duration = float(result["format"]["duration"])
    if output_types != {"video", "audio"} or abs(duration - out_duration) > 0.1:
        output.unlink(missing_ok=True)
        raise RuntimeError(f"Provera zvuka/trajanja nije prosla: {output}")
    return output, duration


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--music", default="assets/global_pulse.m4a")
    parser.add_argument("--videos", default="reels_preview/izlaz")
    args = parser.parse_args()
    music = Path(args.music)
    if not music.is_file():
        parser.error(f"Muzika nije dodata u repozitorijum: {music}")
    videos = Path(args.videos)
    found = False
    for program in PROGRAMS:
        path = videos / f"{program}_reel.mp4"
        if not path.exists():
            print(f"Nema videa za {program}; preskacem.")
            continue
        result, seconds = add_music(path, music)
        found = True
        print(f"MUZIKA OK: {program}, {seconds:.2f}s, {result}")
    if not found:
        print("Nema probnih videa kojima treba dodati zvuk.")


if __name__ == "__main__":
    main()
