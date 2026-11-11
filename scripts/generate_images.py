
import json
import re
from pathlib import Path
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "analize.json"
IMAGES = ROOT / "slike"
IMAGES.mkdir(exist_ok=True)

NAVY = "#071629"
NAVY_LIGHT = "#142C49"
GOLD = "#F1BE55"
WHITE = "#FFF9ED"
MUTED = "#BCC8D7"
RED = "#BA2039"

FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")
REGULAR = FONT_DIR / "DejaVuSans.ttf"
BOLD = FONT_DIR / "DejaVuSans-Bold.ttf"


def font(size, bold=False):
    path = BOLD if bold else REGULAR
    return ImageFont.truetype(str(path), size)


def wrap(draw, text, face, max_width):
    words = str(text).split()
    lines = []
    current = ""

    for word in words:
        candidate = (current + " " + word).strip()
        if draw.textbbox((0, 0), candidate, font=face)[2] <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word

    if current:
        lines.append(current)

    return lines


def draw_poster(item, width, height, destination):
    image = Image.new("RGB", (width, height), NAVY)
    draw = ImageDraw.Draw(image)

    margin = 65
    usable = width - margin * 2

    # Originalna dekorativna ilustracija
    draw.ellipse(
        (width - 570, height - 650,
         width + 240, height + 160),
        fill=NAVY_LIGHT
    )
    draw.ellipse(
        (-360, height - 390, 420, height + 390),
        outline=GOLD,
        width=5
    )

    for offset in range(0, 260, 34):
        draw.arc(
            (width - 520 - offset,
             height - 530 - offset,
             width + 140 + offset,
             height + 130 + offset),
            190, 330,
            fill="#294666",
            width=3
        )

    # Logo
    draw.text(
        (margin, 70), "TRAG",
        font=font(92, True), fill=WHITE
    )
    draw.text(
        (390, 70), "24",
        font=font(92, True), fill=GOLD
    )

    draw.line(
        (margin, 195, width - margin, 195),
        fill=GOLD, width=4
    )

    date = item.get("datum", "")
    try:
        date = datetime.strptime(
            date, "%Y-%m-%d"
        ).strftime("%d.%m.%Y.")
    except ValueError:
        pass

    draw.text(
        (margin, 225),
        date + "  |  AI pregled izvora",
        font=font(27),
        fill=MUTED
    )

    category = str(
        item.get("kategorija", "ANALIZA")
    ).upper()

    draw.rounded_rectangle(
        (margin, 310, margin + 390, 380),
        radius=15,
        fill=RED
    )
    draw.text(
        (margin + 22, 327),
        category[:19],
        font=font(29, True),
        fill=WHITE
    )

    # Naslov se prilagodjava prostoru
    title = str(item.get("naslov", "TRAG 24"))
    top = 430
    bottom_limit = height - 270

    for size in range(69, 30, -2):
        face = font(size, True)
        lines = wrap(draw, title, face, usable)
        line_height = int(size * 1.38)
        if top + len(lines) * line_height < bottom_limit:
            break

    y = top
    for line in lines:
        draw.text(
            (margin, y),
            line,
            font=face,
            fill=WHITE
        )
        y += line_height

    # Donja traka
    footer_y = height - 160
    draw.line(
        (margin, footer_y, width - margin, footer_y),
        fill=GOLD, width=4
    )

    draw.text(
        (margin, footer_y + 32),
        "TRAG 24  |  ANALIZE",
        font=font(28, True),
        fill=WHITE
    )

    draw.text(
        (width - margin, footer_y + 75),
        "Originalna ilustracija",
        font=font(23),
        fill=MUTED,
        anchor="ra"
    )

    image.save(destination, "PNG", optimize=True)


def main():
    if not DATA.exists():
        print("Nema analize.json")
        return

    data = json.loads(DATA.read_text(encoding="utf-8"))
    changed = False

    for item in data.get("analize", []):
        if not isinstance(item, dict):
            continue

        uid = str(item.get("id", ""))
        if not re.fullmatch(r"[a-zA-Z0-9_-]+", uid):
            continue

        portrait = IMAGES / f"{uid}.png"
        story = IMAGES / f"{uid}-story.png"

        if not portrait.exists():
            draw_poster(item, 1080, 1350, portrait)
            print("Kreirana slika:", portrait.name)

        if not story.exists():
            draw_poster(item, 1080, 1920, story)
            print("Kreirana Story slika:", story.name)

        expected = f"slike/{uid}.png"
        if item.get("slika") != expected:
            item["slika"] = expected
            changed = True

    if changed:
        DATA.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8"
        )

    print("Generisanje ilustracija završeno.")


if __name__ == "__main__":
    main()
