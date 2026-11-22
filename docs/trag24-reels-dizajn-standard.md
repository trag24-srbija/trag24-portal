# TRAG 24 — vizuelni standard za šest Reels emisija

Ovaj dokument opisuje **probnu** grafičku automatizaciju. Nema javnog objavljivanja niti izmena aktivnog portala.

## Brend i dizajn
- Osnovna pozadina: tamnoplava / antracit (**#101d30**).
- Kontura i separator: zlatna (**#e5b74d**).
- Crveni akcent i CTA: **#ae1129**.
- Naslovi: veliki, beli, zadebljani, najčešće 68–76 piksela u kadru 1080×1920.
- Svaki kadar ima gornju oznaku, zlatnu liniju, središnji tekst, izvor/datum i donji CTA.
- Svaka od šest emisija koristi *svoj postojeći prazan šablon* u `templates/*.jpg`. Grafički primeri sa unapred upisanim novinskim naslovima ne koriste se za automatiku.

## Raspored i trajanje
| Emisija | Vreme | Video | Kadrovi | CTA |
|---|---|---|---|---|
| Srbija se budi | 08:00 | 15 s | 5 | PRATI TRAG 24 |
| Verovali ili ne | 11:00 | 15 s | 5 | PROČITAJ CELU PRIČU |
| Novac i život | 14:00 | 15 s | 5 | VIŠE NA PORTALU |
| Pitanje dana | 17:00 | 15 s | 5 | PIŠI U KOMENTARU |
| Vesti u 20 | 20:00 | 20 s | 5 | PRATI TRAG 24 |
| Arena – noćni izazov | 23:00 | 15 s | 5 | IGRAJ TRAG 24 ARENU |

**Napomena:** kraći Reels `Vesti u 20` ne zamenjuje odvojenu dužu emisiju sa naratorom.

## Podaci i bezbednost
- Vesti se izvlače samo iz već objavljenih analiza; zahtevaju se najmanje dva izvora sa različitim domenima. Ovo je *filter kvaliteta*, ne nezavisna provera činjenične tačnosti.
- Emisija od 14:00 može da koristi analizu od prethodnog dana, uz istaknut datum te analize.
- Pitanje dana koristi neutralna unapred sastavljena pitanja za publiku; ne tvrdi ništa o novim događajima.
- Arena koristi pitanja iz pregledanog početnog fonda, uz oznaku da je iz arhive; ne otkriva odgovor u Reels-u.
- Ukoliko nema prihvatljivog sadržaja, objava se preskače umesto izmišljanja podataka.
- Svaki video dobija `*_cover.png` (drugi kadar, sa glavnim naslovom/pitanjem) za izgled profila.
- Trenutni GitHub Actions posao služi samo za ručnu/probnu pripremu `artifact` fajlova. **Nema objavljivanja na Instagram/Facebook/TikTok, nema zakazanog rasporeda, nema Make poziva.**

## Pre prelaska u produkciju
Potrebno je vizuelno pregledati bar po jedan uzorak za svaku emisiju, proveriti izvor i datum, napraviti idempotentno zakazivanje/zaštitu od duplih objava i tek tada odlučiti o spajanju Draft PR-a.
