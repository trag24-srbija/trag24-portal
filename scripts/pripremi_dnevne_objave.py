#!/usr/bin/env python3
"""TRAG 24: priprema probnih Reels kartica iz objavljenih analiza.

Nema AI zahteva, objavljivanja niti slanja podataka društvenim mrežama.
Ne verifikuje istinitost izvora: koristi samo već objavljene analize i URL-ove.
"""
import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

TZ = ZoneInfo('Europe/Belgrade')
PROGRAMS = {
    '0800': None,
    '1100': {'zanimljivosti', 'zabava', 'nauka', 'tehnologija', 'kultura'},
    '1400': {'ekonomija', 'privreda', 'novac', 'finansije'},
    '2000': None,
}
TITLES = {
    '0800': 'Jutarnji pregled',
    '1100': 'Verovali ili ne',
    '1400': 'Novac i život',
    '2000': 'Vesti u 20',
}


def approved_urls(row):
    urls = row.get('izvori', [])
    if not isinstance(urls, list):
        return []
    out = []
    hosts = set()
    for url in urls:
        if not isinstance(url, str) or not url.startswith('https://'):
            continue
        parts = urlsplit(url)
        domain = parts.hostname or ''
        if not domain or domain in hosts:
            continue
        out.append(url)
        hosts.add(domain)
    return out


def clean(value, limit):
    text = re.sub(r'\s+', ' ', str(value or '')).strip()
    if len(text) <= limit:
        return text
    cut = text[:limit - 1].rsplit(' ', 1)[0]
    return (cut or text[:limit - 1]).rstrip(' ,.;:') + '…'


def body(row):
    chunks = row.get('tekst', [])
    if isinstance(chunks, str):
        chunks = [chunks]
    if not isinstance(chunks, list):
        return ''
    for part in chunks:
        text = clean(part, 290)
        if len(text) >= 80 and not text.lower().startswith(('ova analiza', 'automatski pregled', 'trag 24 |')):
            return text
    return ''


def prepare(source, date, selected):
    rows = source.get('analize', []) if isinstance(source, dict) else []
    filtered = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if row.get('datum') != date or row.get('status') != 'objavljeno':
            continue
        urls = approved_urls(row)
        if len(urls) < 2:  # bez dva različita domena ne šaljemo u probnu automatiku
            continue
        headline = clean(row.get('naslov'), 95)
        text = body(row)
        if not headline or not text:
            continue
        filtered.append((row, urls, headline, text))
    # Redosled po polju u JSON-u: novije objave su na kraju.
    filtered.reverse()
    result = []
    used = set()
    for program in selected:
        if program in ('1700', '2300'):
            print(f'PRESKOČENO {program}: potreban odobren urednički unos / ARENA pitanje.', file=sys.stderr)
            continue
        if program not in PROGRAMS:
            raise ValueError(f'Nepoznat termin: {program}')
        cats = PROGRAMS[program]
        match = next((x for x in filtered if x[0].get('id') not in used and
            (cats is None or any(k in str(x[0].get('kategorija', '')).casefold() for k in cats))), None)
        if not match:
            print(f'PRESKOČENO {program}: nema odgovarajuće analize sa dva izvora za {date}.', file=sys.stderr)
            continue
        row, urls, headline, text = match
        used.add(row.get('id'))
        result.append({
            'program': program,
            'naslov': headline,
            'tekst': text,
            'izvor': ', '.join(sorted({urlsplit(x).hostname for x in urls})[:2]),
            'oznaka': 'PREGLED IZVORA',
            'datum': date,
            'id_analize': row.get('id'),
            'izvori': urls,
            'status': 'ZA_PROVERU',
        })
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--analize', default='analize.json')
    parser.add_argument('--datum', default=dt.datetime.now(TZ).date().isoformat())
    parser.add_argument('--termini', default='0800,1100,1400,2000')
    parser.add_argument('--izlaz', default='reels_preview/dnevne_objave.json')
    args = parser.parse_args()
    dt.date.fromisoformat(args.datum)
    data = json.loads(Path(args.analize).read_text(encoding='utf-8'))
    selected = [x.strip() for x in args.termini.split(',') if x.strip()]
    rows = prepare(data, args.datum, selected)
    path = Path(args.izlaz)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'{len(rows)} probnih sadržaja u {path}. Bez objavljivanja.')


if __name__ == '__main__':
    main()