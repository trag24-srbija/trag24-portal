#!/usr/bin/env python3
"""TRAG 24: tekstualni Reels -- pet citljivih kadrova, >= 15 s, bez AI videa.
Ovo je SAMO lokalna proba; nema objavljivanja na sajtu i mrezama.
"""
import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw

from render_reels import (
    ROOT, TEMPLATES, W, H, X1, X2, get_font, wrap, draw_shadow,
    WHITE, MUTED, ACCENT
)

DURATIONS_BY_PROGRAM = {
    "0800": [2, 4, 4, 3, 2],  # 15s
    "1400": [2, 4, 4, 3, 2],  # 15s
    "1100": [2, 4, 4, 3, 2],  # 15s
    "1700": [2, 4, 4, 3, 2],  # 15s
    "2300": [2, 4, 4, 3, 2],  # 15s
    "2000": [2, 5, 5, 5, 3],  # 20s -- odvojeno od duze naratorske emisije
}
TEMPLATES_BY_PROGRAM = {
    "0800": TEMPLATES / "0800_srbija_se_budi.jpg",
    "1400": TEMPLATES / "1400_novac_i_zivot.jpg",
    "1100": TEMPLATES / "1100_verovali_ili_ne.jpg",
    "1700": TEMPLATES / "1700_pitanje_dana.jpg",
    "2300": TEMPLATES / "2300_arena.jpg",
    "2000": TEMPLATES / "2000_vesti_u_20.jpg",
}


def sentences(value):
    text = re.sub(r"\s+", " ", str(value)).strip()
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def sections(text):
    """Dva kratka izvoda iz postojece analize; bez dodavanja tvrdnji."""
    pieces = sentences(text)
    if not pieces:
        return ("", "")
    def shorten(value, limit=105):
        if len(value) <= limit:
            return value
        prefix = value[:limit-1].rsplit(" ", 1)[0].rstrip(" ,;:")
        return (prefix or value[:limit-1]) + "…"
    first = shorten(pieces[0])
    second = shorten(" ".join(pieces[1:])) if len(pieces) > 1 else "Detalji i originalni izvori nalaze se na portalu TRAG 24."
    return first, second

def fit_text(draw, txt, max_width=870, max_lines=5, start=70, minimum=46):
    for size in range(start, minimum - 1, -2):
        face = get_font(size, True)
        lines = wrap(draw, txt, face, max_width)
        if len(lines) <= max_lines:
            return face, lines, int(size*1.32)
    raise ValueError("Tekst ne moze citljivo da stane u kadar.")


CTA = {
    "0800": "PRATI TRAG 24",
    "1100": "PROČITAJ CELU PRIČU",
    "1400": "VIŠE NA PORTALU",
    "1700": "PIŠI U KOMENTARU",
    "2000": "PRATI TRAG 24",
    "2300": "IGRAJ TRAG 24 ARENU",
}


def make_frame(bg, number, heading, main, detail, source, dest,
               label="PREGLED IZVORA • PROBNI VIDEO", date_note="", program="0800"):
    """Zajednički premium raspored: zlato, tamnoplava, crvena, krupan tekst."""
    im = bg.copy()
    draw = ImageDraw.Draw(im)

    # Brendirani zaglavni pojas unutar slobodnog polja.
    draw.rounded_rectangle((X1-16, 670, X2+14, 765), radius=17,
                           fill="#0A1C32", outline="#E5B74D", width=3)
    draw.rounded_rectangle((X1-16, 674, X1-4, 759), radius=4, fill="#D42139")
    font_h = get_font(40, True)
    if draw.textlength(heading.upper(), font=font_h) > X2-X1-34:
        font_h = get_font(34, True)
    draw.text((X1+13, 690), heading.upper(), font=font_h, fill="#FFFFFF")
    draw.line((X1, 783, X1+310, 783), fill="#E5B74D", width=5)

    f, lines, step = fit_text(draw, main, max_lines=5,
                             start=76 if number == 2 else 68)
    yy = 822
    for line in lines:
        draw_shadow(draw, (X1, yy), line, f, WHITE)
        yy += step

    if detail:
        dface = get_font(40)
        dl = wrap(draw, detail, dface, X2-X1)
        if len(dl) > 4:
            raise ValueError("Dopunski tekst ne staje u centralni panel.")
        yy = max(yy+40, 1210)
        if yy + 56 * len(dl) > 1455:
            raise ValueError("Tekst prelazi dozvoljeni prostor.")
        for line in dl:
            draw_shadow(draw, (X1, yy), line, dface, MUTED)
            yy += 56

    # Izvor i datum nisu deo fotografije i uvek ostaju ažurirani.
    draw.line((X1, 1483, X2, 1483), fill="#AC8A4B", width=2)
    draw.text((X1, 1503), label[:36].upper(),
              font=get_font(25, True), fill="#E5B74D")
    datepart = "DATUM: " + str(date_note) if date_note else ""
    info = datepart + (("  •  " if datepart else "") + "IZVORI: " + source if source else "")
    if info:
        info_font = get_font(22)
        while len(info) > 20 and draw.textlength(info, font=info_font) > X2-X1:
            info = info[:-2].rstrip() + "…"
        draw.text((X1, 1543), info, font=info_font, fill="#D4DCE6")
    draw.text((X2-4, 1502), f"{number}/5",
              font=get_font(28, True), fill=WHITE, anchor="ra")

    # Zajednički CTA na svim emisijama: prepoznatljiv Instagram cover.
    draw.rounded_rectangle((X1+6, 1691, X2-6, 1776), radius=21,
                           fill="#AE1129", outline="#E5B74D", width=4)
    cta = CTA.get(program, "PRATI TRAG 24")
    cta_font = get_font(43, True)
    draw.text(((W//2), 1709), cta, font=cta_font, fill="#FFFFFF", anchor="mt")

    dest.parent.mkdir(parents=True, exist_ok=True)
    im.save(dest, optimize=True)


def render(item, output):
    program=str(item.get("program", ""))
    if program not in TEMPLATES_BY_PROGRAM:
        raise ValueError(f"Nepoznat program: {program}")
    bg=Image.open(TEMPLATES_BY_PROGRAM[program]).convert("RGB")
    if bg.size != (W,H):
        bg=bg.resize((W,H), Image.Resampling.LANCZOS)
    headline=re.sub(r"\s+"," ",str(item.get("naslov",""))).strip()
    text=str(item.get("tekst","")).strip()
    if not headline or not text:
        raise ValueError("Nema naslova ili teksta. Preskacem objavu.")
    excerpt1, excerpt2 = sections(text)
    date=str(item.get("datum",""))
    source=re.sub(r"\s+"," ",str(item.get("izvor",""))).strip()
    date_note=str(item.get("datum_vesti") or date)

    durations = DURATIONS_BY_PROGRAM[program]
    if program == "0800":
        slides=[
            ("JUTARNJI PREGLED", "Dobro jutro, Srbijo", "TRAG 24 • "+date),
            ("GLAVNA TEMA", headline, ""),
            ("PREMA IZVORIMA", excerpt1, ""),
            ("NASTAVAK TEME", excerpt2, ""),
            ("PRATI TRAG 24", "Cela analiza i izvori na portalu",
             "Pratite nove vesti i provere tokom dana."),
        ]
    elif program == "1100":
        date_note = str(item.get("datum_vesti", date))
        slides=[
            ("VEROVALI ILI NE", "Neobična vest iz izvora", "Analiza od "+date_note),
            ("ŠTA SE DOGODILO", headline, ""),
            ("PREMA IZVORIMA", excerpt1, ""),
            ("ŠTA JOŠ ZNAMO", excerpt2, ""),
            ("PRATI TRAG 24", "Više detalja na portalu", "Pogledaj originalne izvore vesti."),
        ]
    elif program == "1400":
        date_note = str(item.get("datum_vesti", date))
        slides=[
            ("NOVAC I ŽIVOT", "Šta utiče na vaš novčanik?", "Analiza od "+date_note),
            ("GLAVNA TEMA", headline, ""),
            ("PREMA IZVORIMA", excerpt1, ""),
            ("DETALJI I KONTEKST", excerpt2, ""),
            ("PRATI TRAG 24", "Pročitaj celu analizu", "Više informacija i izvori na portalu."),
        ]
    elif program == "1700":
        slides=[
            ("PITANJE DANA", "Vaše mišljenje je važno", "TRAG 24 • "+date),
            ("DANAS PITAMO", headline, ""),
            ("VAŠ ODGOVOR", "Napišite šta mislite", "Vaše iskustvo je dragoceno."),
            ("OBRAZLOŽITE", "Zašto tako mislite?", "Kratak komentar je dovoljan."),
            ("PRATI TRAG 24", "Odgovori u komentarima", "Pridruži se razgovoru."),
        ]
    elif program == "2300":
        options=item.get("opcije")
        if not isinstance(options, list) or len(options)!=4:
            raise ValueError("Arena: nema četiri postojeća ponuđena odgovora.")
        slides=[
            ("ARENA – NOĆNI IZAZOV", "Spreman za kviz?", "Pitanje iz fonda TRAG 24 Arena"),
            ("PITANJE", headline, ""),
            ("IZABERI ODGOVOR", "A) "+options[0]+"\nB) "+options[1], ""),
            ("IZABERI ODGOVOR", "C) "+options[2]+"\nD) "+options[3], ""),
            ("PRATI TRAG 24 ARENA", "Proveri odgovor u Areni", "Izazovi prijatelja na portalu."),
        ]
    else:
        slides=[
            ("VESTI U 20", "Najvažnija tema dana", "Kratak pregled • TRAG 24"),
            ("GLAVNA VEST", headline, ""),
            ("ŠTA ZNAMO", excerpt1, ""),
            ("DETALJI", excerpt2, ""),
            ("PRATI TRAG 24", "Celu analizu čitaj na portalu", "Proveri izvore • trag24"),
        ]
    total_seconds = sum(durations)
    if len(slides) != 5 or total_seconds < 15:
        raise AssertionError("Neispravna satnica emisije.")

    output.mkdir(parents=True,exist_ok=True)
    frames=[]
    for i,(label,head,sub) in enumerate(slides,1):
        dest=output/f"{program}_{i:02d}.png"
        provenance = ("PITANJE ZA KOMENTARE" if program == "1700"
                      else "ARENA: PRETHODNO PREGLEDAN KVIZ" if program == "2300"
                      else "PREGLED IZVORA • PROBNI VIDEO")
        make_frame(bg,i,label,head,sub,source,dest,label=provenance,
                   date_note=date_note,program=program)
        frames.append(dest)

    # Naslovna slika za Instagram grid: 2. kadar sa pravim naslovom/pitanjem.
    shutil.copyfile(frames[1], output / f"{program}_cover.png")

    # Concat demuxer obezbedjuje pojedinacna trajanja kadrova.
    lst=output/f"{program}_frames.ffconcat"
    with lst.open("w",encoding="utf-8") as fp:
        fp.write("ffconcat version 1.0\n")
        for path,duration in zip(frames,durations):
            fp.write("file '"+path.name+"'\n")
            fp.write("duration "+str(duration)+"\n")
        fp.write("file '"+frames[-1].name+"'\n")

    movie=output/f"{program}_reel.mp4"
    subprocess.run([
        "ffmpeg","-hide_banner","-loglevel","error","-y",
        "-safe","0","-f","concat","-i",str(lst),
        "-t",str(total_seconds),"-vf","fps=24,format=yuv420p",
        "-c:v","libx264","-preset","veryfast","-crf","25",
        "-movflags","+faststart",str(movie)
    ],check=True)

    # Fail closed: proveri trajanje, ne salji skracene videe.
    check=subprocess.check_output([
        "ffprobe","-v","error","-show_entries","format=duration",
        "-of","default=nokey=1:noprint_wrappers=1",str(movie)
    ],text=True)
    duration=float(check.strip())
    if not total_seconds <= duration <= total_seconds+0.1:
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
    found = False
    for program in ("0800", "1100", "1400", "1700", "2000", "2300"):
        items=[x for x in content if str(x.get("program")) == program]
        if not items:
            print(f"Nema odgovarajuce teme za {program}. Preskacem.")
            continue
        movie=render(items[0],Path(args.out))
        print(f"Proba {program}: 5 kadrova, {sum(DURATIONS_BY_PROGRAM[program])} s, {movie}")
        found = True
    if not found:
        print("Nema odgovarajucih tema ili prethodno pregledanih pitanja.")


if __name__ == "__main__":
    main()
