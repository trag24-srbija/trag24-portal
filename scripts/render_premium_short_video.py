#!/usr/bin/env python3
"""TRAG24: 15-second MP4 Reel using approved premium card and existing soundtrack.

No generation API, no public posting, and no external media service.
"""
import argparse
import subprocess
from pathlib import Path

import imageio_ffmpeg
from PIL import Image


def render(image_path, destination, soundtrack, seconds=15):
    image_path = Path(image_path)
    destination = Path(destination)
    soundtrack = Path(soundtrack)
    if seconds != 15:
        raise ValueError("The short Reel must last exactly 15 seconds")
    if not image_path.is_file() or not soundtrack.is_file():
        raise FileNotFoundError("Missing card or original soundtrack")
    with Image.open(image_path) as im:
        if im.size != (1080, 1920):
            raise ValueError("Reel cover must be 1080x1920")
    destination.parent.mkdir(parents=True, exist_ok=True)
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    command = [
        ff, "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
        "-loop", "1", "-framerate", "24", "-i", str(image_path),
        "-stream_loop", "-1", "-i", str(soundtrack),
        "-filter_complex",
        "[0:v]scale=1080:1920,format=yuv420p,"
        "fade=t=in:st=0:d=0.35,fade=t=out:st=14.5:d=0.5[v];"
        "[1:a]volume=0.55,afade=t=in:st=0:d=0.35,"
        "afade=t=out:st=13.7:d=1.3[a]",
        "-map", "[v]", "-map", "[a]",
        "-t", str(seconds), "-c:v", "libx264", "-preset", "veryfast",
        "-crf", "25", "-pix_fmt", "yuv420p", "-r", "24",
        "-c:a", "aac", "-b:a", "128k", "-ar", "48000",
        "-movflags", "+faststart", str(destination),
    ]
    subprocess.run(command, check=True, timeout=180)
    if destination.stat().st_size < 20000:
        raise RuntimeError("Reel encoding failed or produced an empty file")
    return destination


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--soundtrack", default="trag24-vesti-podloga.mov")
    args = parser.parse_args()
    result = render(args.image, args.output, args.soundtrack)
    print("PREMIUM REEL OK:", result)


if __name__ == "__main__":
    main()
