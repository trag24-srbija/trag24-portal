

import json
import re
import hashlib
import html
import urllib.request
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from html.parser import HTMLParser
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
NEWS = ROOT / "news.json"
ANALYSES = ROOT / "analize.json"
TZ = ZoneInfo("Europe/Belgrade")

STOP = set("""
danas sutra juce najnovije vesti vest srbija srbiji
srpski srpske rekao rekla otkrio otkrila
nakon posle zbog kako zasto koji koja koje
ovo ovaj ova evo foto video godine godina
sada samo nije jeste imaju poznato detalji
""".split())


def load(path, default):
    try:
        return json.loads(
            path.read_text(encoding="utf-8")
        )
    except (OSError, ValueError):
        return default


def normalize(text):
    text = unicodedata.normalize(
        "NFKD", text.casefold()
    )
    text = "".join(
        c for c in text
        if not unicodedata.combining(c)
    )
    return re.sub(r"[^a-z0-9 ]", " ", text)


def keywords(title):
    return {
        w for w in normalize(title).split()
        if len(w) >= 4 and w not in STOP
    }


class ArticleParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.depth = 0
        self.skip = 0
        self.parts = []
        self.current = []
        self.in_paragraph = False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "nav", "footer"):
            self.skip += 1
        if tag == "p" and not self.skip:
            self.in_paragraph = True
            self.current = []

    def handle_endtag(self, tag):
        if tag == "p" and self.in_paragraph:
            text = " ".join(self.current).strip()
            if len(text) >= 80:
                self.parts.append(text)
            self.in_paragraph = False
        if tag in ("script", "style", "nav", "footer"):
            self.skip = max(0, self.skip - 1)

    def handle_data(self, data):
        if self.in_paragraph and not self.skip:
            self.current.append(data.strip())


def read_article(url):
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "text/html"
            }
        )
        with urllib.request.urlopen(
            req, timeout=10
        ) as response:
            raw = response.read(500000)
            content_type = response.headers.get(
                "Content-Type", ""
            )
            if "html" not in content_type.lower():
                return []

        parser = ArticleParser()
        parser.feed(
            raw.decode("utf-8", errors="replace")
        )

        paragraphs = []
        for text in parser.parts:
            text = html.unescape(text)
            text = re.sub(r"\s+", " ", text)
            if len(text) >= 80:
                paragraphs.append(text[:700])

        return paragraphs[:12]

    except Exception as exc:
        print("Čitanje članka nije uspelo:", exc)
        return []


def main():
    now = datetime.now(timezone.utc)
    local = now.astimezone(TZ)

    news = load(NEWS, {}).get("articles", [])
    data = load(ANALYSES, {"analize": []})
    analyses = data.get("analize", [])

    if not isinstance(analyses, list):
        analyses = []

    candidates = []

    for item in news:
        if not isinstance(item, dict):
            continue

        if item.get("category") not in (
            "Politika", "Hronika",
            "Ekonomija", "Društvo"
        ):
            continue

        title = str(item.get("title", "")).strip()
        source = str(item.get("source", "")).strip()
        url = str(item.get("source_url", ""))

        if not title or not source:
            continue
        if not url.startswith("https://"):
            continue

        try:
            date = datetime.fromisoformat(
                item["published_at"].replace(
                    "Z", "+00:00"
                )
            )
            if date.tzinfo is None:
                continue
            age = now - date.astimezone(timezone.utc)
            if not timedelta(0) <= age <= timedelta(hours=24):
                continue
        except (ValueError, KeyError, TypeError):
            continue

        words = keywords(title)
        if len(words) >= 3:
            candidates.append((item, words))

    groups = []

    for item, words in candidates:
        matched = False

        for group in groups:
            shared = words & group["words"]
            similarity = len(shared) / max(
                1, min(len(words), len(group["words"]))
            )

            if (
                item["category"] == group["category"]
                and len(shared) >= 2
                and similarity >= 0.5
            ):
                group["items"].append(item)
                group["words"] &= words
                matched = True
                break

        if not matched:
            groups.append({
                "category": item["category"],
                "words": set(words),
                "items": [item]
            })

    groups.sort(
        key=lambda g: len({
            x["source"] for x in g["items"]
        }),
        reverse=True
    )

    for group in groups:
        unique = {}

        for item in group["items"]:
            unique.setdefault(item["source"], item)

        if len(unique) < 2:
            continue

        selected = list(unique.values())[:4]

        signature = "|".join(
            sorted(group["words"])
        )

        uid = "tema-" + hashlib.sha256(
            signature.encode()
        ).hexdigest()[:16]

        if any(
            a.get("id") == uid
            for a in analyses
            if isinstance(a, dict)
        ):
            continue

        articles = []

        for item in selected:
            paragraphs = read_article(
                item["source_url"]
            )

            if paragraphs:
                articles.append({
                    "item": item,
                    "paragraphs": paragraphs
                })

        if len(articles) < 2:
            continue

        title = min(
            selected,
            key=lambda x: len(x["title"])
        )["title"]

        paragraphs = [
            "TRAG 24 | PREGLED VIŠE IZVORA",
            "Tema: " + title,
            "Ovaj pregled povezuje izveštavanje "
            "više medija o istoj temi. Navodi nisu "
            "nezavisno potvrđeni od strane TRAG 24.",
            "ŠTA OBJAVLJUJU MEDIJI"
        ]

        for article in articles:
            item = article["item"]

            paragraphs.append(
                item["source"] + " objavljuje: "
                + item["title"]
            )

            paragraphs.append(
                "U tekstu ovog medija navodi se: "
                + " ".join(
                    article["paragraphs"][:2]
                )[:1100]
            )

        paragraphs.extend([
            "ŠTA JE POTVRĐENO",
            "Potvrđeno je da navedeni mediji "
            "objavljuju informacije o ovoj temi. "
            "To samo po sebi ne potvrđuje "
            "tačnost svih njihovih navoda.",
            "ŠTA OSTАJE OTVORENO",
            "Za konačne zaključke potrebno je "
            "proveriti primarne dokumente, "
            "zvanična saopštenja i eventualne "
            "razlike među izvorima."
        ])

        analyses.append({
            "id": uid,
            "datum": local.strftime("%Y-%m-%d"),
            "kategorija": group["category"],
            "naslov": (
                "TRAG 24 | Više izvora o događaju: "
                + title[:105]
            ),
            "autor": (
                "TRAG 24 — automatski pregled izvora"
            ),
            "tekst": paragraphs,
            "izvori": [
                a["item"]["source_url"]
                for a in articles
            ],
            "status": "objavljeno"
        })

        data["analize"] = analyses

        ANALYSES.write_text(
            json.dumps(
                data,
                ensure_ascii=False,
                indent=2
            ) + "\n",
            encoding="utf-8"
        )

        print(
            "Objavljen pregled iz",
            len(articles),
            "medijskih izvora."
        )
        return

    print(
        "Nema dovoljno povezanih i čitljivih "
        "članaka za novu objavu."
    )


if __name__ == "__main__":
    main()
