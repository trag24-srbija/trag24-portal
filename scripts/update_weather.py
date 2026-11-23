"""TRAG 24: besplatna vremenska prognoza iz MET Norway (CC BY 4.0).
Ne pozivati API češće od dozvoljenog intervala; workflow radi na šest sati.
Prikazane temperature su izvedene iz modelskih prognoza, ne merenja.
"""
import datetime as dt
import json
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "weather.json"
TZ = ZoneInfo("Europe/Belgrade")
SOURCE_URL = "https://api.met.no/weatherapi/locationforecast/2.0/compact"
USER_AGENT = "TRAG24-Weather/1.0 (+https://www.trag24.rs)"

CITIES = {
    "Beograd": (44.8176, 20.4633),
    "Novi Sad": (45.2671, 19.8335),
    "Niš": (43.3209, 21.8958),
    "Kragujevac": (44.0128, 20.9114),
    "Subotica": (46.1004, 19.6651),
    "Smederevo": (44.6628, 20.9276),
    "Velika Plana": (44.3330, 21.0792),
    "Kraljevo": (43.7234, 20.6870),
    "Užice": (43.8556, 19.8425),
    "Novi Pazar": (43.1367, 20.5122),
}


def condition(code):
    value = (code or "").lower()
    if "thunder" in value:
        return "Grmljavina", "⛈️"
    if "sleet" in value:
        return "Susnežica", "🌨️"
    if "snow" in value:
        return "Sneg", "❄️"
    if "heavyrain" in value:
        return "Jaka kiša", "🌧️"
    if "rain" in value or "drizzle" in value:
        return "Kiša", "🌧️"
    if "fog" in value:
        return "Magla", "🌫️"
    if "partlycloudy" in value or "fair" in value:
        return "Delimično oblačno", "🌤️"
    if "cloudy" in value:
        return "Oblačno", "☁️"
    if "clearsky" in value:
        return "Vedro", "☀️"
    return "Promenljivo", "🌤️"


def city_forecast(name, latitude, longitude, today):
    url = f"{SOURCE_URL}?lat={latitude:.4f}&lon={longitude:.4f}"
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        data = json.load(response)

    series = data["properties"]["timeseries"]
    daily = {}
    for entry in series:
        when = dt.datetime.fromisoformat(entry["time"].replace("Z", "+00:00")).astimezone(TZ)
        day = when.date()
        if day < today or day > today + dt.timedelta(days=2):
            continue
        instant = entry.get("data", {}).get("instant", {}).get("details", {})
        temperature = instant.get("air_temperature")
        if not isinstance(temperature, (int, float)):
            continue
        summary = (
            entry.get("data", {}).get("next_1_hours", {}).get("summary")
            or entry.get("data", {}).get("next_6_hours", {}).get("summary")
            or entry.get("data", {}).get("next_12_hours", {}).get("summary")
            or {}
        )
        symbol = summary.get("symbol_code", "")
        daily.setdefault(day, []).append((when.hour, temperature, symbol))

    forecast = []
    for day in sorted(daily):
        hours = daily[day]
        if not hours:
            continue
        temperatures = [entry[1] for entry in hours]
        symbols = [entry for entry in hours if entry[2]]
        chosen = min(symbols, key=lambda entry: abs(entry[0] - 14)) if symbols else None
        label, icon = condition(chosen[2] if chosen else "")
        forecast.append({
            "date": day.isoformat(),
            "min_c": round(min(temperatures)),
            "max_c": round(max(temperatures)),
            "condition": label,
            "icon": icon,
        })

    if not forecast:
        raise ValueError("Nema podataka za naredna tri dana")
    return {"name": name, "forecast": forecast, "retrieved_at": dt.datetime.now(dt.timezone.utc).isoformat()}


def main():
    try:
        previous = json.loads(OUTPUT.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        previous = {}
    previous_cities = {
        city["name"]: city
        for city in previous.get("cities", [])
        if isinstance(city, dict) and city.get("name")
    }
    today = dt.datetime.now(TZ).date()
    cities = []
    successes = 0
    for name, (lat, lon) in CITIES.items():
        try:
            result = city_forecast(name, lat, lon, today)
            cities.append(result)
            successes += 1
            print(f"{name}: prognoza preuzeta")
        except (OSError, ValueError, KeyError, TypeError) as exc:
            print(f"{name}: izvor nedostupan ({exc})")
            if name in previous_cities:
                cities.append(previous_cities[name])

    if not successes:
        print("Nema nove prognoze; postojeći podaci ostaju sačuvani.")
        return

    result = {
        "updated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source": "MET Norway",
        "source_url": "https://api.met.no/",
        "license": "CC BY 4.0",
        "license_url": "https://creativecommons.org/licenses/by/4.0/",
        "note": "Prognoze su izvedene iz podataka MET Norway i nisu zvanična upozorenja RHMZ Srbije.",
        "cities": cities,
    }
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Sačuvano: {successes} osveženih gradova od {len(CITIES)}.")


if __name__ == "__main__":
    main()
