
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
ANALIZE = ROOT / "analize.json"
VESTI = ROOT / "news.json"
TZ = ZoneInfo("Europe/Belgrade")

KATEGORIJE = ("Politika", "Hronika", "Ekonomija", "Društvo")


def ucitaj(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def main():
    sada = datetime.now(timezone.utc)
    lokalno = sada.astimezone(TZ)

    if lokalno.hour < 12:
        termin = "Jutarnji"
    elif lokalno.hour < 18:
        termin = "Popodnevni"
    else:
        termin = "Večernji"

    oznaka = f"{lokalno:%Y-%m-%d}-{termin.lower()}"
    identifikator = "pregled-" + oznaka

    podaci = ucitaj(ANALIZE, {"analize": []})
    analize = podaci.get("analize", [])

    if not isinstance(analize, list):
        analize = []

    if any(
        isinstance(a, dict) and a.get("id") == identifikator
        for a in analize
    ):
        print("Pregled za ovaj termin već postoji.")
        return

    vesti = ucitaj(VESTI, {}).get("articles", [])
    kandidati = []

    for vest in vesti:
        if not isinstance(vest, dict):
            continue

        if vest.get("region") != "Srbija":
            continue

        if vest.get("category") not in KATEGORIJE:
            continue

        naslov = str(vest.get("title", "")).strip()
        link = str(vest.get("source_url", "")).strip()
        izvor = str(vest.get("source", "")).strip()

        if not naslov or not izvor:
            continue

        if not link.startswith("https://"):
            continue

        if not urlparse(link).hostname:
            continue

        try:
            datum = datetime.fromisoformat(
                str(vest.get("published_at", "")).replace("Z", "+00:00")
            )
            if datum.tzinfo is None:
                continue

            starost = sada - datum.astimezone(timezone.utc)

            if not timedelta(0) <= starost <= timedelta(hours=18):
                continue
        except ValueError:
            continue

        kandidati.append((datum, vest))

    kandidati.sort(key=lambda x: x[0], reverse=True)

    odabrano = []
    izvori = set()
    naslovi = set()

    for _, vest in kandidati:
        izvor = vest["source"]
        naslov = vest["title"].strip().casefold()

        if izvor in izvori or naslov in naslovi:
            continue

        odabrano.append(vest)
        izvori.add(izvor)
        naslovi.add(naslov)

        if len(odabrano) == 4:
            break

    if len(odabrano) < 2:
        print("Nema dovoljno novih vesti za pregled.")
        return

    pasusi = [
        "Automatski pregled medijskih objava iz Srbije. "
        "Navodi su preneti iz označenih izvora i nisu "
        "nezavisno potvrđeni od strane redakcije TRAG 24."
    ]

    for vest in odabrano:
        pasusi.append(
            f"{vest['category']} — {vest['source']} objavljuje: "
            f"„{vest['title'].strip()}”. "
            "Detalji su dostupni u izvornom članku."
        )

    pasusi.append(
        "Za potpuniju procenu ovih događaja potrebno je "
        "proveriti zvanična saopštenja, dokumenta i "
        "nezavisne potvrde. Ovaj pregled nije "
        "istraživačka analiza."
    )

    nova = {
        "id": identifikator,
        "datum": lokalno.strftime("%Y-%m-%d"),
        "kategorija": "Pregled izvora",
        "naslov": (
            f"TRAG 24: {termin} pregled tema — "
            f"{lokalno:%d.%m.%Y.}"
        ),
        "autor": "TRAG 24 — automatski pregled izvora",
        "tekst": pasusi,
        "izvori": [v["source_url"] for v in odabrano],
        "status": "objavljeno"
    }

    analize.append(nova)

    automatske = [
        a for a in analize
        if isinstance(a, dict)
        and str(a.get("id", "")).startswith("pregled-")
    ]

    sacuvani = {
        a["id"] for a in automatske[-45:]
    }

    analize = [
        a for a in analize
        if isinstance(a, dict)
        and (
            not str(a.get("id", "")).startswith("pregled-")
            or a.get("id") in sacuvani
        )
    ]

    podaci["analize"] = analize

    ANALIZE.write_text(
        json.dumps(podaci, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8"
    )

    print(f"Objavljen {termin.lower()} pregled.")


if __name__ == "__main__":
    main()
