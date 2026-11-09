
import json
from pathlib import Path
from datetime import datetime

FAJL = Path(__file__).resolve().parent.parent / "analize.json"

def main():
    if not FAJL.exists():
        print("Fajl analize.json ne postoji.")
        return

    with FAJL.open("r", encoding="utf-8") as f:
        podaci = json.load(f)

    analize = podaci.get("analize", [])
    rezultat = []
    vidjeni = set()

    for analiza in analize:
        if not isinstance(analiza, dict):
            continue

        naslov = str(analiza.get("naslov", "")).strip()
        datum = str(analiza.get("datum", "")).strip()
        identifikator = str(analiza.get("id", "")).strip()

        if not naslov or not datum:
            continue

        try:
            datetime.strptime(datum, "%Y-%m-%d")
        except ValueError:
            continue

        kljuc = identifikator or (datum + "|" + naslov.lower())

        if kljuc in vidjeni:
            continue

        vidjeni.add(kljuc)
        rezultat.append(analiza)

    rezultat.sort(
        key=lambda a: a.get("datum", ""),
        reverse=True
    )

    podaci["analize"] = rezultat

    with FAJL.open("w", encoding="utf-8") as f:
        json.dump(
            podaci,
            f,
            ensure_ascii=False,
            indent=2
        )
        f.write("\n")

    print(f"Sačuvano analiza: {len(rezultat)}")

if __name__ == "__main__":
    main()
