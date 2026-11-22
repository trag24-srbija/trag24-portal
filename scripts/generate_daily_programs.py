#!/usr/bin/env python3
"""TRAG 24: premium 9:16 graphics for 11, 14, 17 and 23 h.

Uses only existing published, multi-source analyses. No automatic social posting.
"""
import argparse
import datetime as dt
import json
import re
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont

TZ = ZoneInfo("Europe/Belgrade")
W, H = 1080, 1920
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "analize.json"
OUT = ROOT / "program_output"
FONT_ROOT = Path("/usr/share/fonts/truetype/dejavu")

PROGRAMS = {
    "11": {"title": "VEROVALI ILI NE", "subtitle": "NEOBIČNE PRIČE",
           "accent": "#A88CF2", "category": "ZANIMLJIVOST DANA"},
    "14": {"title": "NOVAC I ŽIVOT", "subtitle": "EKONOMIJA I SVAKODNEVICA",
           "accent": "#52C8B0", "category": "NOVAC I ŽIVOT"},
    "17": {"title": "PITANJE DANA", "subtitle": "VAŠ GLAS JE VAŽAN",
           "accent": "#F07575", "category": "ŠTA VI MISLITE?"},
    "20": {"title": "VESTI U 20", "subtitle": "VEČERNJI PREGLED",
           "accent": "#E45B69", "category": "NAJVAŽNIJE VESTI"},
    "23": {"title": "ARENA", "subtitle": "NOĆNI IZAZOV",
           "accent": "#4B9CFF", "category": "TRAG 24 ARENA"},
}
GOLD = "#F1BE61"
WHITE = "#F6F8FC"
LIGHT = "#E4EBF4"


def font(size, bold=False):
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    return ImageFont.truetype(str(FONT_ROOT / name), size)


def wrap(draw, text, face, width):
    parts, current = [], ""
    for word in str(text).split():
        candidate = (current + " " + word).strip()
        if current and draw.textbbox((0, 0), candidate, font=face)[2] > width:
            parts.append(current)
            current = word
        else:
            current = candidate
    if current:
        parts.append(current)
    return parts


def fit(draw, text, width, height, initial, minimum, bold=False, leading=1.25):
    """Responsive readable type, without text escaping the layout box."""
    for size in range(initial, minimum-1, -1):
        face = font(size, bold)
        lines = wrap(draw, text, face, width)
        step = round(size*leading)
        if len(lines)*step <= height and all(
                draw.textbbox((0, 0), x, font=face)[2] <= width for x in lines):
            return face, lines, step
    face = font(minimum, bold)
    lines = wrap(draw, text, face, width)
    step = round(minimum*leading)
    maximum = max(1, height // step)
    if len(lines) > maximum:
        lines = lines[:maximum]
        last = lines[-1]
        while last and draw.textbbox((0, 0), last + "…", font=face)[2] > width:
            last = last[:-1]
        lines[-1] = last.rstrip() + "…"
    return face, lines, step


def clean_summary(a):
    paragraphs = a.get("tekst", [])
    if not isinstance(paragraphs, list):
        paragraphs = [paragraphs]
    candidates = []
    for item in paragraphs:
        s = re.sub(r"\s+", " ", str(item)).strip()
        s = re.sub(r"^[^:]{3,50}:\s*", "", s)
        if len(s) >= 65:
            candidates.append(s)
    if not candidates:
        return ""
    s = candidates[0]
    if len(s) > 205:
        s = s[:205].rsplit(" ", 1)[0].rstrip(".,;:") + "…"
    return s


def published(day, hour):
    if not DATA.exists():
        return []
    data = json.loads(DATA.read_text(encoding="utf-8"))
    end = dt.datetime.combine(day, dt.time(int(hour), 0), TZ)
    start = end - dt.timedelta(hours=72 if hour == "14" else 42)
    result = []
    for a in data.get("analize", []):
        if not isinstance(a, dict) or a.get("status") != "objavljeno":
            continue
        title = str(a.get("naslov", "")).strip()
        if not title:
            continue
        try:
            stamp = dt.datetime.fromisoformat(
                str(a["objavljeno_u"]).replace("Z", "+00:00")
            ).astimezone(TZ)
        except (ValueError, KeyError, TypeError):
            continue
        if not start <= stamp <= end:
            continue
        urls = a.get("izvori", [])
        if not isinstance(urls, list):
            continue
        urls = [x for x in urls if isinstance(x, str) and x.startswith("https://")]
        hosts = list(dict.fromkeys(
            urlparse(u).netloc.lower().removeprefix("www.")
            for u in urls if urlparse(u).netloc
        ))
        if len(hosts) < 2:
            continue
        desc = clean_summary(a)
        if not desc:
            continue
        result.append((stamp, {
            "published_date": stamp.date().isoformat(),
            "title": title, "summary": desc, "sources": hosts[:3],
            "category": str(a.get("kategorija", "")),
            "id": str(a.get("id", "")),
        }))
    result.sort(key=lambda x: x[0], reverse=True)
    return [a for _, a in result]


def choose(hour, day):
    # Editor-safe program selection: do not turn deaths or tragedies into trivia.
    if hour == "23":
        return {
            "title": "5 PITANJA. JEDAN IZAZOV.",
            "summary": "Proveri znanje, osvoji poene i izazovi prijatelja.",
            "sources": [], "category": "ARENA", "id": "",
        }
    if hour == "17":
        questions = [
            "Šta bi trebalo prvo unaprediti u vašem gradu?",
            "Koju temu želite da TRAG 24 dodatno istraži?",
            "Da li više volite kratke vesti ili detaljne analize?",
            "Koja informacija vam najviše nedostaje u medijima?",
            "Koju rubriku biste želeli češće da pratite?",
            "Šta vam je važnije: brzina ili provera izvora?",
            "Koje pitanje biste postavili lokalnim vlastima?",
        ]
        return {
            "title": questions[day.toordinal() % len(questions)],
            "summary": "Napišite mišljenje u komentaru. Razgovarajmo uz uvažavanje različitih stavova.",
            "sources": [], "category": "PITANJE ZA PUBLIKU", "id": "",
        }

    data = published(day, hour)
    tragedy = re.compile(
        r"ubistv|nasil|traged|nesreć|stradal|hapše|zločin|poginu|smrt|"
        r"preminu|nestal|oružj|povređen|pogib|sudar|ranjen|izgubljen.*život|"
        r"pronađ.*telo|telo.*detet|dečak.*nest|devojčic.*nest|silovan|otmic|"
        r"teror|ratna.*dejstv|samoub", re.I
    )
    unusual = re.compile(
        r"munj|grom|meteor|astronom|svemir|nauč|naučn|tehnolog|"
        r"neobič|neverovat|zanimljiv|otkrić|eksperiment|robot|"
        r"rekord|fenomen|izum|prvi put|unikat", re.I
    )
    economy = re.compile(
        r"goriv|cen[ae]|cenov|inflacij|poskuplj|plata|plate|"
        r"zarad|penzij|porez|budžet|promet|lizing|bank|privred|"
        r"ekonom|finans|invest|subvenc|kamat|tržišt|potrošač|"
        r"energij|poslovanj|maloprodaj|kupovin|sniženj|"
        r"komunal|minimalac|zakup|kurs evra", re.I
    )
    misleading_econ = re.compile(
        r"zaplena|zaplenjen|krivič|uhapš|istrag|optuž|suđen|"
        r"bivš.*ministar|ubistv|nasil|traged|nesreć", re.I
    )
    if hour == "11":
        preferred = [
            x for x in data
            if unusual.search(x["title"])
            and not tragedy.search(x["title"] + " " + x["summary"])
        ]
        return preferred[0] if preferred else None
    if hour == "14":
        preferred = [
            x for x in data
            if x["category"].casefold() in {"ekonomija", "privreda", "finansije"}
            and economy.search(x["title"])
            and not misleading_econ.search(x["title"] + " " + x["summary"])
            and not tragedy.search(x["title"] + " " + x["summary"])
        ]
        return preferred[0] if preferred else None
    if hour == "20":
        today = [x for x in data if dt.date.fromisoformat(
            str(x.get("published_date", day.isoformat()))) == day]
        return today[0] if today else None
    return None


def make_card(hour, day, story):
    cfg = PROGRAMS[hour]
    accent = cfg["accent"]
    im = Image.new("RGB", (W, H), "#09192E")
    d = ImageDraw.Draw(im, "RGBA")
    for y in range(H):
        t = y/H
        d.line((0, y, W, y),
               fill=(round(7+5*t), round(22+7*t), round(43+10*t), 255))
    # Shared TV-news globe, with a different restrained accent per programme.
    d.ellipse((615, 43, 1055, 483), outline=(154, 180, 220, 70), width=2)
    for factor in (.38, .7):
        r = round(220*factor)
        d.ellipse((835-r, 43, 835+r, 483),
                  outline=(154, 180, 220, 44), width=2)
    d.arc((-280, 1370, 1350, 2000), 12, 167,
          fill=(204, 167, 92, 52), width=2)

    d.rectangle((75, 125, 100, 188), fill="#E5354D")
    d.text((124, 111), "TRAG 24", font=font(73, True), fill=WHITE)

    show_font = font(91, True)
    while d.textbbox((0, 0), cfg["title"], font=show_font)[2] > 930:
        show_font = font(show_font.size-1, True)
    d.text((76, 341), cfg["title"], font=show_font,
           fill=GOLD, stroke_width=0)
    d.text((78, 455), f"{hour}:00   |   {cfg['subtitle']}   |   {day:%d.%m.%Y.}",
           font=font(32, True), fill=LIGHT)
    d.line((73, 539, 1007, 539), fill=accent, width=6)

    d.rounded_rectangle((65, 614, 1027, 1606), radius=40,
                        fill=(0, 0, 0, 65))
    d.rounded_rectangle((58, 606, 1020, 1599), radius=40,
                        fill="#112C4C", outline=accent, width=3)
    d.line((102, 614, 976, 614), fill=(255, 224, 157, 105), width=2)
    d.rounded_rectangle((101, 658, 780, 733), radius=13,
                        fill=accent)
    tag = cfg["category"]
    tag_face = font(36, True)
    while d.textbbox((0, 0), tag, font=tag_face)[2] > 635:
        tag_face = font(tag_face.size-1, True)
    d.text((124, 669), tag, font=tag_face, fill="#0B1B2D")

    headline = story["title"]
    face, lines, step = fit(d, headline, 865, 344, 63, 45, True, 1.24)
    y = 771
    for line in lines:
        d.text((101, y), line, font=face, fill=WHITE)
        y += step

    d.line((101, max(1110, y+4), 976, max(1110, y+4)),
           fill=(237, 193, 103, 155), width=2)

    y = max(1152, y+30)
    body = story["summary"]
    face, lines, step = fit(d, body, 862, max(120, 1475-y),
                            50, 38, False, 1.24)
    for line in lines:
        d.text((101, y), line, font=face, fill=WHITE)
        y += step

    d.line((101, 1494, 974, 1494), fill=(229, 185, 96, 160), width=2)
    if hour == "23":
        source = "IGRAJ: trag24-srbija.github.io/trag24-portal/arena/"
    elif hour == "17":
        source = "PITANJE ZA PUBLIKU • BEZ TVRDNJI O DOGAĐAJIMA"
    else:
        source = "IZVORI: " + ", ".join(story["sources"])
    face = font(30, True)
    while d.textbbox((0, 0), source, font=face)[2] > 870 and face.size > 22:
        face = font(face.size-1, True)
    d.text((101, 1520), source, font=face, fill=GOLD)

    d.rectangle((77, 1693, 84, 1786), fill=accent)
    section = "PROVERI ZNANJE I IZAZOVI PRIJATELJA" if hour == "23" else (
        "PRATITE CELOKUPNU PRIČU NA TRAG 24")
    face = font(37, True)
    while d.textbbox((0, 0), section, font=face)[2] > 879:
        face = font(face.size-1, True)
    d.text((105, 1680), section, font=face, fill=WHITE)
    d.text((105, 1744), "Vesti, izvori i detalji na našem portalu",
           font=font(34), fill=LIGHT)

    d.rectangle((0, 1824, W, H), fill="#081326")
    d.line((0, 1824, W, 1824), fill=accent, width=6)
    d.text((76, 1851), "TRAG24  |  " + cfg["title"],
           font=font(31, True), fill=WHITE)
    d.text((882, 1848), f"{hour}:00", font=font(36, True), fill=GOLD)
    return im


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--program", choices=sorted(PROGRAMS), required=True)
    parser.add_argument("--date", default="")
    args = parser.parse_args()
    day = dt.date.fromisoformat(args.date) if args.date else dt.datetime.now(TZ).date()
    story = choose(args.program, day)
    if story is None:
        print(f"SKIP: nema prikladne sveže, objavljene teme sa 2 izvora za {args.program}:00")
        return
    OUT.mkdir(parents=True, exist_ok=True)
    stem = f"TRAG24-{args.program}-{day.isoformat()}"
    path = OUT / (stem + ".png")
    make_card(args.program, day, story).save(path, optimize=True)
    meta = {
        "status": "nacrt", "program": PROGRAMS[args.program]["title"],
        "sat": args.program + ":00", "datum": day.isoformat(),
        "slika": path.name, "vest": story,
        "napomena": "Sadrzaj iz objavljenih analiza sa vise izvora; navodi nisu nezavisno potvrdjeni. Nije automatski objavljeno."
    }
    (OUT / (stem + ".json")).write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("OK:", path)


if __name__ == "__main__":
    main()
