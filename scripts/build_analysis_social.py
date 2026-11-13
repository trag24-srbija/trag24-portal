
#!/usr/bin/env python3
import datetime as dt
from zoneinfo import ZoneInfo
import email.utils
import html
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "analiza"
BASE = "https://trag24-srbija.github.io/trag24-portal/"
MEDIA_NS = "http://search.yahoo.com/mrss/"
ET.register_namespace("media", MEDIA_NS)

HEADINGS = {
    "ŠTA SE DOGODILO",
    "HRONOLOGIJA",
    "ŠTA NAVODE IZVORI",
    "ŠTA JE POTVRĐENO",
    "ŠTA NIJE POTVRĐENO",
    "ŠTA OSTAJE OTVORENO",
}

def esc(value):
    return html.escape(str(value), quote=True)

def valid_image(item):
    relative = str(
        item.get("slika") or item.get("image") or ""
    ).strip()

    if re.fullmatch(
        r"slike/[a-zA-Z0-9_-]+\.(png|jpg|jpeg|webp)",
        relative
    ):
        file = ROOT / relative
        if file.is_file():
            return (
                relative,
                BASE + quote(relative, safe="/"),
                file.stat().st_size,
            )

    return (
        "share.jpg",
        BASE + "share.jpg",
        (ROOT / "share.jpg").stat().st_size,
    )

def paragraphs(item):
    data = item.get("tekst", [])
    return data if isinstance(data, list) else [data]

def summary(item):
    for part in paragraphs(item):
        text = re.sub(
            r"\s+", " ",
            html.unescape(str(part))
        ).strip()
        text = re.sub(
            r"^[^:]{3,45}:\s*", "", text
        )
        if len(text) > 25:
            return text[:330].rstrip() + (
                "…" if len(text) > 330 else ""
            )
    return "Najnovija analiza portala TRAG 24."

def article_body(item):
    chunks = []

    for value in paragraphs(item):
        value = str(value).strip()
        match = re.match(
            r"^([^:]{3,50}):\s*(.*)$",
            value,
            re.S
        )

        if match and match.group(1).strip().upper() in HEADINGS:
            chunks.append(
                f"<h2>{esc(match.group(1).strip())}</h2>"
            )
            if match.group(2).strip():
                chunks.append(
                    f"<p>{esc(match.group(2).strip())}</p>"
                )
        elif value:
            chunks.append(f"<p>{esc(value)}</p>")

    sources = item.get("izvori", [])
    if isinstance(sources, list):
        links = [
            f'<li><a href="{esc(url)}" '
            f'rel="noopener noreferrer" target="_blank">'
            f'{esc(url)}</a></li>'
            for url in sources
            if isinstance(url, str)
            and url.startswith("https://")
        ]
        if links:
            chunks.append(
                "<h2>Izvori</h2><ul>"
                + "".join(links) + "</ul>"
            )

    chunks.append(
        '<p class="notice">'
        'Ova analiza je pripremljena uz pomoć '
        'veštačke inteligencije na osnovu '
        'javno dostupnih izvora. Navodi izvora '
        'nisu nužno nezavisno potvrđeni.'
        '</p>'
    )

    return "\n".join(chunks)

def write_page(item, uid, image_path, image_url):
    title = str(item["naslov"]).strip()
    page_url = (
        BASE + "analiza/" + quote(uid) + ".html"
    )
    date = str(item.get("datum", ""))

if item.get("objavljeno_u"):
    stamp = dt.datetime.fromisoformat(
        str(item["objavljeno_u"]).replace("Z", "+00:00")
    )
    date = stamp.astimezone(
        ZoneInfo("Europe/Belgrade")
    ).strftime("%d.%m.%Y. u %H:%M")
    author = str(item.get("autor", "TRAG 24"))
    description = summary(item)
    image_src = "../" + image_path

    image_size = (
        ("1200", "630")
        if image_path == "share.jpg"
        else ("1080", "1350")
    )

    image_type = (
        "image/jpeg"
        if image_path.lower().endswith((".jpg", ".jpeg"))
        else "image/png"
    )

    page = f'''<!DOCTYPE html>
<html lang="sr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} | TRAG 24</title>
<meta name="description" content="{esc(description)}">
<link rel="canonical" href="{esc(page_url)}">
<meta property="og:type" content="article">
<meta property="og:site_name" content="TRAG 24">
<meta property="og:url" content="{esc(page_url)}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:image" content="{esc(image_url)}">
<meta property="og:image:secure_url" content="{esc(image_url)}">
<meta property="og:image:type" content="{image_type}">
<meta property="og:image:width" content="{image_size[0]}">
<meta property="og:image:height" content="{image_size[1]}">
<meta name="twitter:card" content="summary_large_image">
<style>
*{{box-sizing:border-box}}
body{{margin:0;background:#f3f4f6;color:#142238;font-family:Arial,sans-serif}}
header,footer{{background:#142238;color:white;padding:24px 20px}}
header strong{{font-size:27px}}
header p{{color:#cad4df}}
main{{max-width:820px;margin:25px auto;background:white;padding:30px;line-height:1.75}}
h1{{font-size:clamp(27px,4vw,39px);line-height:1.25}}
h2{{font-size:23px;margin-top:27px}}
p,li{{font-size:17px}}
a{{color:#a92338;overflow-wrap:anywhere}}
.meta{{color:#657389;font-size:14px}}
.cover{{display:block;width:100%;height:auto;max-width:650px;margin:22px auto}}
.notice{{font-size:13px;color:#637083;border-top:1px solid #e2e8f0;padding-top:15px}}
footer a{{color:white}}
</style>
</head>
<body>
<header>
<strong>TRAG 24</strong>
<p>Srbija. Činjenice. Događaji.</p>
</header>
<main>
<a href="../index.html" style="display:inline-block;background:#b92336;color:#fff;padding:12px 18px;border-radius:10px;text-decoration:none;font-weight:700;margin-bottom:12px">← Sve vesti</a>
<h1>{esc(title)}</h1>
<p class="meta">{esc(date)} · {esc(author)}</p>
<img class="cover" src="{esc(image_src)}"
alt="Ilustracija analize: {esc(title)}">
{article_body(item)}
</main>
<footer>
TRAG 24 | <a href="../">Najnovije vesti</a>
</footer>
</body>
</html>
'''

    destination = OUT / (uid + ".html")
    if (
        not destination.is_file()
        or destination.read_text(encoding="utf-8") != page
    ):
        destination.write_text(
            page, encoding="utf-8"
        )

    return page_url

def generate():
    data = json.loads(
        (ROOT / "analize.json").read_text(
            encoding="utf-8"
        )
    )

    OUT.mkdir(exist_ok=True)
    rss = ET.Element("rss", {"version": "2.0"})
    channel = ET.SubElement(rss, "channel")

    for key, value in (
        ("title", "TRAG 24 - Analize"),
        ("link", BASE + "analize.html"),
        ("description", "Analize i pregledi izvora TRAG 24"),
        ("language", "sr-RS"),
    ):
        ET.SubElement(channel, key).text = value

    processed = set()
    published = 0

    for item in sorted(
        data.get("analize", []),
        key=lambda a: str(a.get("objavljeno_u") or a.get("datum", "")),
        reverse=True
    ):
        if (
            not isinstance(item, dict)
            or item.get("status") != "objavljeno"
        ):
            continue

        uid = str(item.get("id", "")).strip()
        title = str(item.get("naslov", "")).strip()

        if (
            not re.fullmatch(r"[A-Za-z0-9_-]+", uid)
            or not title
            or uid in processed
        ):
            continue

        processed.add(uid)

        image_path, image_url, image_size = (
            valid_image(item)
        )

        page_url = write_page(
            item, uid, image_path, image_url
        )

        if published >= 30:
            continue

        published += 1

        entry = ET.SubElement(channel, "item")
        ET.SubElement(entry, "title").text = title
        ET.SubElement(entry, "link").text = page_url
        ET.SubElement(
            entry, "guid",
            {"isPermaLink": "false"}
        ).text = uid

        ET.SubElement(
            entry, "description"
        ).text = summary(item)

        ET.SubElement(
            entry, f"{{{MEDIA_NS}}}content",
            {"url": image_url, "medium": "image"}
        )

        ET.SubElement(
            entry, "enclosure",
            {
                "url": image_url,
                "type": (
                    "image/png"
                    if image_path.endswith(".png")
                    else "image/jpeg"
                ),
                "length": str(image_size),
            }
        )

        try:
            stamp = dt.datetime.fromisoformat(
                str(item.get("objavljeno_u") or item.get("datum", "")).replace(
                    "Z", "+00:00"
                )
            )
            if stamp.tzinfo is None:
                stamp = stamp.replace(
                    tzinfo=dt.timezone.utc
                )

            ET.SubElement(
                entry, "pubDate"
            ).text = email.utils.format_datetime(
                stamp
            )
        except (ValueError, TypeError):
            pass

    ET.indent(rss, space="  ")

    ET.ElementTree(rss).write(
        ROOT / "analize-feed.xml",
        encoding="utf-8",
        xml_declaration=True
    )

    print(
        f"TRAG 24: {len(processed)} stranica, "
        f"{published} RSS vesti."
    )

if __name__ == "__main__":
    generate()
