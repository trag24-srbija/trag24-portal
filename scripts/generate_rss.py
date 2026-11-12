
import json
import datetime
import email.utils
import xml.etree.ElementTree as ET
from pathlib import Path

root = Path(__file__).resolve().parent.parent
data = json.loads((root / "news.json").read_text(encoding="utf-8"))

rss = ET.Element("rss", version="2.0")
channel = ET.SubElement(rss, "channel")

site = "https://trag24-srbija.github.io/trag24-portal/"

for tag, value in {
    "title": "TRAG 24 - Vesti",
    "link": site,
    "description": "Najnovije vesti iz Srbije",
    "language": "sr-RS"
}.items():
    ET.SubElement(channel, tag).text = value

seen = set()

for article in sorted(
    data.get("articles", []),
    key=lambda a: a.get("published_at", ""),
    reverse=True
):
    title = article.get("title", "")
    url = article.get("source_url", "")
    uid = article.get("id", "")

    if not title or not url or not uid or uid in seen:
        continue

    seen.add(uid)
    item = ET.SubElement(channel, "item")

    ET.SubElement(item, "title").text = title
    ET.SubElement(item, "link").text = url
    ET.SubElement(item, "guid", isPermaLink="false").text = str(uid)
    ET.SubElement(item, "description").text = (
        "Izvor: " + article.get("source", "TRAG 24")
    )

    try:
        date = datetime.datetime.fromisoformat(
            article.get("published_at", "").replace("Z", "+00:00")
        )
        if date.tzinfo is None:
            date = date.replace(tzinfo=datetime.timezone.utc)
        ET.SubElement(item, "pubDate").text = email.utils.format_datetime(date)
    except ValueError:
        pass

    if len(seen) >= 30:
        break

ET.indent(rss, space="  ")
ET.ElementTree(rss).write(
    root / "feed.xml",
    encoding="utf-8",
    xml_declaration=True
)
