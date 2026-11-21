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
from html import unescape
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

TZ = ZoneInfo('Europe/Belgrade')
# Urednicki filter za 14:00; sama kategorija nije dovoljna (bilo je pogresnih kategorija).
UNUSUAL_HEADLINE = re.compile(
    r'munj|grom|avion.*(otkaz|udar|pogođ)|meteor|svemir|rekord|otkrić|'
    r'neobič|neverovat|iznena|retk|zanimljiv|izum|prvi put|unikat|'
    r'robot|eksperiment|tehnologij|naučn|astronom', re.IGNORECASE
)

ECON_HEADLINE = re.compile(
    r'goriv|cen[ae]|cenov|inflacij|poskuplj|plat[ae]|zarad|penzij|'
    r'porez|budžet|trgovin|promet|lizing|bank|privred|ekonom|'
    r'finans|invest|subvenc|kurs evra|kamat|izvoz|uvoz|'
    r'industr|tržišt|potrošač|energij|poslovanj|maloprodaj|'
    r'kupovin|sniženj|komunal|minimalac|zakup',
    re.IGNORECASE
)
PROGRAMS = {
    '0800': None,
    '1100': {'zanimljivosti', 'zabava', 'nauka', 'tehnologija', 'kultura'},
    '1400': {'ekonomija', 'privreda', 'novac', 'finansije'},
    '2000': None,
    '1700': None,
}
TITLES = {
    '0800': 'Jutarnji pregled',
    '1100': 'Verovali ili ne',
    '1400': 'Novac i život',
    '2000': 'Vesti u 20',
    '1700': 'Pitanje dana',
    '2300': 'Arena – noćni izazov',
}

# Neutralna pitanja za komentare; nikada se ne predstavljaju kao novinska cinjenica.
PUBLIC_QUESTIONS = [
    'Koju temu želite da TRAG 24 dodatno istraži?',
    'Koju vest ste danas najviše želeli da proverite?',
    'Šta vam je važnije: kratka vest ili detaljna analiza?',
    'Koji problem iz svakodnevnog života zaslužuje više pažnje?',
    'Koju rubriku najčešće pratite: ekonomiju, društvo ili sport?',
    'Šta najviše cenite u vestima: brzinu ili proverene izvore?',
    'Koju korisnu informaciju biste želeli svakog jutra?',
]

def prepare_arena_from_curated_html(path, date):
    """Samo pregledani starter fond iz Arena aplikacije, bez privatnih API-ja."""
    try:
        html = Path(path).read_text(encoding='utf-8')
        marker = 'window.ARENA_QUESTION_BANK = '
        start = html.index(marker) + len(marker)
        end = html.index(';', start)
        bank = json.loads(html[start:end])
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f'ARENA preskočena: nema dostupnog pregledanog fonda ({exc}).', file=sys.stderr)
        return None
    safe_categories = {'Ekonomija', 'Društvo', 'Sport', 'Kultura'}
    candidates = []
    for q in bank.get('questions', []):
        if q.get('quality_status') != 'reviewed_seed' or q.get('category') not in safe_categories:
            continue
        question = q.get('question', '')
        opts = q.get('options', [])
        if not isinstance(question, str) or len(question) > 96 or len(question) < 18:
            continue
        if not isinstance(opts, list) or len(opts) != 4 or not all(isinstance(o, str) and 1 <= len(o) <= 30 for o in opts):
            continue
        if len(set(opts)) != 4 or q.get('correct_index') not in (0, 1, 2, 3):
            continue
        if not str(q.get('source_url', '')).startswith('https://') or not str(q.get('analysis_url', '')).startswith('https://'):
            continue
        if any(word in question.casefold() for word in ('ubistv','optuž','prijav','pogin','nesreć')):
            continue
        candidates.append(q)
    if not candidates:
        print('ARENA preskočena: nema kratkog prethodno pregledanog pitanja.', file=sys.stderr)
        return None
    candidates.sort(key=lambda q: q.get('id', ''))
    q = candidates[dt.date.fromisoformat(date).toordinal() % len(candidates)]
    return {
        'program': '2300', 'naslov': q['question'],
        'tekst': 'Pitanje iz pregledanog početnog fonda TRAG 24 Arena.',
        'opcije': q['options'], 'id_pitanja': q['id'],
        'izvor': urlsplit(q['source_url']).hostname,
        'izvori': [q['source_url']], 'analiza_url': q['analysis_url'],
        'oznaka': 'ARENA KVIZ – IZ ARHIVE', 'datum': date,
        'status': 'ZA_PROVERU',
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
    day_before = (dt.date.fromisoformat(date) - dt.timedelta(days=1)).isoformat()
    for row in rows:
        if not isinstance(row, dict):
            continue
        if row.get('datum') not in (date, day_before) or row.get('status') != 'objavljeno':
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
        if program == '1700':
            question = PUBLIC_QUESTIONS[dt.date.fromisoformat(date).toordinal() % len(PUBLIC_QUESTIONS)]
            result.append({
                'program': '1700', 'naslov': question,
                'tekst': 'Pitanje za komentare – ne tvrdi ništa o događajima.',
                'oznaka': 'PITANJE ZA PUBLIKU', 'datum': date,
                'izvor': '', 'status': 'ZA_PROVERU',
            })
            continue
        if program == '2300':
            q = prepare_arena_from_curated_html('arena/index.html', date)
            if q:
                result.append(q)
            continue
        if program not in PROGRAMS:
            raise ValueError(f'Nepoznat termin: {program}')
        cats = PROGRAMS[program]
        match = next((
            x for x in filtered
            if x[0].get('id') not in used
            and (x[0].get('datum') == date
                 or (program in ('1400', '1100') and x[0].get('datum') == day_before))
            and (cats is None or any(k in str(x[0].get('kategorija', '')).casefold() for k in cats)
                 or (program == '1400' and ECON_HEADLINE.search(x[2]))
                 or (program == '1100' and UNUSUAL_HEADLINE.search(x[2])))
            and (program != '1400' or ECON_HEADLINE.search(x[2]))
            and (program != '1100' or UNUSUAL_HEADLINE.search(x[2]))
        ), None)
        if not match:
            print(f'PRESKOČENO {program}: nema odgovarajuće analize sa dva izvora za {date}.', file=sys.stderr)
            continue
        row, urls, headline, text = match
        used.add(row.get('id'))
        if program in ('1100', '1400') and row.get('datum') != date:
            print(f'{program}: koristim analizu od {row.get("datum")} (nije nova vest).', file=sys.stderr)
        result.append({
            'program': program,
            'naslov': headline,
            'tekst': text,
            'izvor': ', '.join(sorted({urlsplit(x).hostname for x in urls})[:2]),
            'oznaka': ('ANALIZA OD ' + row.get('datum')) if row.get('datum') != date else 'PREGLED IZVORA',
            'datum': date,
            'datum_vesti': row.get('datum'),
            'id_analize': row.get('id'),
            'izvori': urls,
            'status': 'ZA_PROVERU',
        })
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--analize', default='analize.json')
    parser.add_argument('--datum', default=dt.datetime.now(TZ).date().isoformat())
    parser.add_argument('--termini', default='0800,1100,1400,1700,2000,2300')
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