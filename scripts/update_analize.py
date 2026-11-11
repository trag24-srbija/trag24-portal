


import os
import json
import re
import html
import hashlib
import urllib.request
import urllib.error
import unicodedata
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
NEWS = ROOT / "news.json"
ANALYSES = ROOT / "analize.json"
TZ = ZoneInfo("Europe/Belgrade")

API_KEY = os.environ.get("OPENAI_API_KEY", "")
MODEL = "gpt-4.1-mini"

MAX_INPUT_CHARS = 6500
MAX_SOURCES = 3

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


def normalize(value):
    value = unicodedata.normalize(
        "NFKD", str(value).casefold()
    )
    value = "".join(
        c for c in value
        if not unicodedata.combining(c)
    )
    return re.sub(r"[^a-z0-9 ]", " ", value)


def keywords(title):
    return {
        w for w in normalize(title).split()
        if len(w) >= 4 and w not in STOP
    }


class TextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.skip = 0
        self.in_p = False
        self.current = []
        self.paragraphs = []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "nav", "footer"):
            self.skip += 1
        if tag == "p" and not self.skip:
            self.in_p = True
            self.current = []

    def handle_endtag(self, tag):
        if tag == "p" and self.in_p:
            value = " ".join(self.current).strip()
            value = re.sub(r"\s+", " ", value)
            if len(value) >= 90:
                self.paragraphs.append(value)
            self.in_p = False
        if tag in ("script", "style", "nav", "footer"):
            self.skip = max(0, self.skip - 1)

    def handle_data(self, value):
        if self.in_p and not self.skip:
            self.current.append(value.strip())


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
            req, timeout=12
        ) as response:
            if "html" not in response.headers.get(
                "Content-Type", ""
            ).lower():
                return ""

            raw = response.read(450000)

        parser = TextParser()
        parser.feed(
            raw.decode("utf-8", errors="replace")
        )

        unique = []
        seen = set()

        for paragraph in parser.paragraphs:
            paragraph = html.unescape(paragraph)
            if paragraph not in seen:
                seen.add(paragraph)
                unique.append(paragraph)

        return "\n".join(unique)[:MAX_INPUT_CHARS]

    except Exception as exc:
        print("Članak nije dostupan:", str(exc)[:150])
        return ""


def ai_analysis(articles):
    if not API_KEY:
        print("OPENAI_API_KEY nije podešen.")
        return None

    material = []

    for index, article in enumerate(articles, 1):
        material.append(
            f"IZVOR {index}: {article['source']}\n"
            f"NASLOV: {article['title']}\n"
            f"URL: {article['url']}\n"
            f"TEKST:\n{article['body']}"
        )

    instructions = """
Ti si urednik informativnog portala TRAG 24.

Napiši kvalitetan, neutralan i razumljiv
novinarski pregled JEDNOG događaja na
srpskom jeziku, latinicom.

Pravila:
- Koristi ISKLJUČIVO dostavljene tekstove.
- Ne izmišljaj činjenice, datume ni izjave.
- Ne predstavljaj tvrdnje medija kao dokaze.
- Razlikuj potvrđene činjenice od navoda.
- Ne proglašavaj nikoga krivim.
- Ako izvori nisu saglasni, objasni razliku.
- Ne prepisuj duge delove tuđih članaka.
- Ne izmišljaj hronologiju ako nije poznata.
- Ne dodaj izvore koji nisu dostavljeni.
- Ako tekstovi ne govore o istom događaju
  ili nema dovoljno pouzdanih podataka,
  vrati {"publish": false}.

Ako ima dovoljno podataka, vrati ISKLJUČIVO
validan JSON sa sledećim poljima:

{
  "publish": true,
  "title": "Jasan informativan naslov",
  "sections": [
    "ŠTA SE DOGODILO: ...",
    "HRONOLOGIJA: ...",
    "ŠTA NAVODE IZVORI: ...",
    "ŠTA JE POTVRĐENO: ...",
    "ŠTA NIJE POTVRĐENO: ...",
    "ŠTA OSTАJE OTVORENO: ..."
  ]
}

Naslov mora biti neutralan.
Svaki odeljak neka bude sadržajan,
ali bez ponavljanja i nagađanja.
Ukupno približno 350 do 550 reči.
"""

    payload = {
        "model": MODEL,
        "instructions": instructions,
        "input": "\n\n".join(material),
        "max_output_tokens": 1800,
        "store": False
    }

    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": "Bearer " + API_KEY,
            "Content-Type": "application/json"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(
            request, timeout=70
        ) as response:
            result = json.loads(response.read())

        pieces = []

        for output in result.get("output", []):
            for content in output.get("content", []):
                if content.get("type") == "output_text":
                    pieces.append(content.get("text", ""))

        raw = "\n".join(pieces).strip()

        if raw.startswith("```"):
            raw = re.sub(
                r"^```(?:json)?\s*|\s*```$",
                "",
                raw
            ).strip()

        answer = json.loads(raw)

        if not isinstance(answer, dict):
            return None

        if answer.get("publish") is not True:
            return None

        title = answer.get("title")
        sections = answer.get("sections")

        if not isinstance(title, str):
            return None

        if not isinstance(sections, list):
            return None

        if len(sections) < 4:
            return None

        if not all(
            isinstance(s, str) and len(s) >= 35
            for s in sections
        ):
            return None

        return {
            "title": title.strip()[:180],
            "sections": sections
        }

    except Exception as exc:
        print("AI analiza nije uspela:", str(exc)[:250])
        return None


def main():
    now = datetime.now(timezone.utc)
    local = now.astimezone(TZ)

    news = load(NEWS, {}).get("articles", [])
    data = load(ANALYSES, {"analize": []})
    analyses = data.get("analize", [])

    if not isinstance(news, list):
        return

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
            published = datetime.fromisoformat(
                str(item["published_at"]).replace(
                    "Z", "+00:00"
                )
            )

            if published.tzinfo is None:
                continue

            age = now - published.astimezone(
                timezone.utc
            )

            if not timedelta(0) <= age <= timedelta(
                hours=30
            ):
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
                1,
                min(len(words), len(group["words"]))
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
        key=lambda group: len({
            x["source"] for x in group["items"]
        }),
        reverse=True
    )

    for group in groups:
        unique = {}

        for item in group["items"]:
            unique.setdefault(item["source"], item)

        if len(unique) < 2:
            continue

        selected = list(unique.values())[:MAX_SOURCES]

        fingerprint = "|".join(
            sorted(group["words"])
        )

        uid = "ai-" + hashlib.sha256(
            fingerprint.encode()
        ).hexdigest()[:16]

        if any(
            isinstance(a, dict) and a.get("id") == uid
            for a in analyses
        ):
            continue

        articles = []

        for item in selected:
            body = read_article(
                item["source_url"]
            )

            if len(body) < 400:
                continue

            articles.append({
                "source": item["source"],
                "title": item["title"],
                "url": item["source_url"],
                "body": body
            })

        if len(articles) < 2:
            continue

        print(
            "Priprema AI analize iz",
            len(articles),
            "izvora."
        )

        result = ai_analysis(articles)

        if not result:
            print("Nema objave za ovu temu.")
            return

        analyses.append({
            "id": uid,
            "datum": local.strftime("%Y-%m-%d"),
            "kategorija": group["category"],
            "naslov": result["title"],
            "slika": f"slike/{uid}.png",
            "autor": "TRAG 24 — AI pregled izvora",
            "tekst": result["sections"],
            "izvori": [
                a["url"] for a in articles
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

        print("AI analiza sačuvana.")
        return

    print("Nema dovoljno izvora za novu analizu.")


if __name__ == "__main__":
    main()
