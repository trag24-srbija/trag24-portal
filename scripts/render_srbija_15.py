#!/usr/bin/env python3
"""TRAG 24: 08:00 -- pet kadrova, tacno 15 sekundi, bez AI videa.
Ovo je SAMO lokalna proba; nema objavljivanja na sajtu i mrezama.
"""
import argparse
import json
import re
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw

from render_reels import (
    ROOT, TEMPLATES, W, H, X1, X2, get_font, wrap, draw_shadow,
    WHITE, MUTED, ACCENT
)

DURATIONS = [2, 4, 4, 3, 2]
TIMELINE = [
    "JUTARNJI PREGLED",
    "GLAVNA TEMA",
    "PREMA IZVORIMA",
    "JOS DETALJA",
    "PRATI TRAG 24",
]
TEMPLATE = TEMPLATES / "0800_srbija_se_budi.jpg"


def sentences(value):
    text = re.sub(r"\s+", " ", str(value)).strip()
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def sections(text):
    pieces = sentences(text)
    if not pieces:
        return ("", "")
    # Kratki doslovni izvodi -- ne dodajemo nove cinjenice.
    first = pieces[0]
    second = " ".join(pieces[1:])
    if len(first) > 170:
        words = first.split()
        buf = []
        for w in words:
            if len(" ".join(buf+[w])) > 150:
                break
            buf.append(w)
        first = " ".join(buf).rstrip(" ,;:") + "…"
    if not second:
        second = "Vise detalja i izvori dostupni su na portalu TRAG 24."
    elif len(second) > 170:
        second = second[:160].rsplit(" ",1)[0].rstrip(" ,;:") + "…"
    return first, second


def fit_text(draw, txt, max_width=870, max_lines=5, start=58, minimum=36):
    for size in range(start, minimum - 1, -2):
        face = get_font(size, True)
        lines = wrap(draw, txt, face, max_width)
        if len(lines) <= max_lines:
            return face, lines, int(size*1.32)
    raise ValueError("Tekst ne moze citljivo da stane u kadar.")


def make_frame(bg, number, heading, main, detail, source, dest):
    im = bg.copy()
    draw = ImageDraw.Draw(im)
    # Sve promenljivo ostaje unutar praznog centralnog panela.
    draw.text((X1, 690), heading.upper(), font=get_font(34, True), fill="#F3AAB4")
    draw.line((X1, 747, X1+275, 747), fill=ACCENT, width=5)

    f, lines, step = fit_text(draw, main, max_lines=5,
                               start=61 if number == 2 else 56)
    yy=805
    for line in lines:
        draw_shadow(draw, (X1, yy), line, f, WHITE)
        yy+=step

    if detail:
        dface = get_font(34)
        dl = wrap(draw, detail, dface, X2-X1)
        if len(dl)>4:
            raise ValueError("Dopunski tekst je predugacak.")
        yy=max(yy+52, 1190)
        for line in dl:
            draw_shadow(draw, (X1, yy), line, dface, MUTED)
            yy+=48

    draw.text((X1, 1504), "PREGLED IZVORA • PROBNI VIDEO",
              font=get_font(21, True), fill="#B5C2D2")
    if source:
        draw.text((X1, 1538), "IZVORI: "+source[:64],
                  font=get_font(20), fill="#CCD5E0")
    draw.text((930, 1503), f"{number}/5",
              font=get_font(24, True), fill=WHITE, anchor="ra")
    dest.parent.mkdir(parents=True, exist_ok=True)
    im.save(dest, optimize=True)


def render(item, output):
    bg=Image.open(TEMPLATE).convert("RGB")
    if bg.size != (W,H):
        bg=bg.resize((W,H), Image.Resampling.LANCZOS)
    headline=re.sub(r"\s+"," ",str(item.get("naslov",""))).strip()
    text=str(item.get("tekst","")).strip()
    if not headline or not text:
        raise ValueError("Nema naslova ili teksta. Preskacem objavu.")
    excerpt1, excerpt2 = sections(text)
    date=str(item.get("datum",""))
    source=re.sub(r"\s+"," ",str(item.get("izvor",""))).strip()

    slides=[
        ("JUTARNJI PREGLED", "Dobro jutro, Srbijo", "TRAG 24 • "+date),
        ("GLAVNA TEMA", headline, ""),
        ("PREMA IZVORIMA", excerpt1, ""),
        ("NASTAVAK TEME", excerpt2, ""),
        ("PRATI TRAG 24", "Cela analiza i izvori na portalu",
         "Pratite nove vesti i provere tokom dana."),
    ]
    if len(slides)!=5 or sum(DURATIONS)!=15:
        raise AssertionError("Neispravna satnica emisije.")

    output.mkdir(parents=True,exist_ok=True)
    frames=[]
    for i,(label,head,sub) in enumerate(slides,1):
        dest=output/f"0800_{i:02d}.png"
        make_frame(bg,i,label,head,sub,source,dest)
        frames.append(dest)

    # Concat demuxer obezbedjuje pojedinacna trajanja kadrova.
    lst=output/"0800_frames.ffconcat"
    with lst.open("w",encoding="utf-8") as fp:
        fp.write("ffconcat version 1.0\n")
        for path,duration in zip(frames,DURATIONS):
            fp.write("file '"+path.name+"'\n")
            fp.write("duration "+str(duration)+"\n")
        fp.write("file '"+frames[-1].name+"'\n")

    movie=output/"0800_reel.mp4"
    subprocess.run([
        "ffmpeg","-hide_banner","-loglevel","error","-y",
        "-safe","0","-f","concat","-i",str(lst),
        "-t","15","-vf","fps=24,format=yuv420p",
        "-c:v","libx264","-preset","veryfast","-crf","25",
        "-movflags","+faststart",str(movie)
    ],check=True)

    # Fail closed: proveri trajanje, ne salji skracene videe.
    check=subprocess.check_output([
        "ffprobe","-v","error","-show_entries","format=duration",
        "-of","default=nokey=1:noprint_wrappers=1",str(movie)
    ],text=True)
    duration=float(check.strip())
    if not 15.0 <= duration <= 15.1:
        movie.unlink(missing_ok=True)
        raise RuntimeError(f"Pogresno trajanje Reels-a: {duration}")
    return movie


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--content",required=True)
    ap.add_argument("--out",default="reels_preview/izlaz")
    args=ap.parse_args()
    content=json.loads(Path(args.content).read_text(encoding="utf-8"))
    if isinstance(content,dict):
        content=[content]
    items=[x for x in content if str(x.get("program"))=="0800"]
    if not items:
        print("Nema podobne jutarnje teme. Preskacem.")
        return
    movie=render(items[0],Path(args.out))
    print(f"Proba 08:00: 5 kadrova, 15 s, {movie}")


if __name__ == "__main__":
    main()
