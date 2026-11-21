# TRAG 24 → Make: postavljanje bez dupliranja (PROBNA VERZIJA)

## Šta je već automatizovano
- GitHub Actions pravi 6 MP4 Reels snimaka u 1080×1920 sa zvukom `Global Pulse`.
- Uz MP4 se automatski pravi `reels_preview/make_pregled.json`, sa datumom objave, nazivom emisije, opisom, 5 kadrova, nazivom MP4 i naslovnice, originalnim izvorima, SHA-256 i **posebnim ključem za svaku platformu**.
- `publish_enabled=false`, `editorial_status=NEPROVERENO` i `media_url=null`; GitHub ništa ne objavljuje niti šalje Make-u.
- GitHub Actions artifact je privatan/kratkotrajan (3 dana). **Nije** direktan javni URL za Instagram i TikTok.

## Raspored (Europe/Belgrade)
| 08:00 | Srbija se budi | 15 sekundi |
| 11:00 | Verovali ili ne | 15 sekundi |
| 14:00 | Novac i život | 15 sekundi |
| 17:00 | Pitanje dana | 15 sekundi |
| 20:00 | Vesti u 20 – kratki Reels | 20 sekundi |
| 23:00 | Arena | 15 sekundi |

Ovo je plan termina, **nije uključen vremenski raspored javnih objava**.

## Make – preporučeni scenario za povezivanje (bez objavljivanja)
1. Napraviti **NOVI** scenario `TRAG24 REELS – TEST`, da ne dira postojeće FB/IG/TikTok scenarije.
2. Modul `Webhooks > Custom webhook`: nazvati `trag24-reels-test` i izabrati zaseban novi webhook. URL je tajna, **ne stavljati ga u chat ili javni GitHub fajl**.
3. Za probu koristiti primer bezbednog JSON-a iz `docs/make-preview-primer.json`. Ne dodavati izdavačke module.
4. `JSON > Parse JSON` ili direktno koristiti parsirana polja webhooka; `Iterator` kroz `posts[]`; `Tools` ili `Data Store` za evidenciju. Make treba da pamti jedinstveni ključ.
5. Čuvati spisak bezbedno u Make Data Store, sa ključem `idempotency_key`. Jedan ključ = datum + emisija + platforma. Ovaj ključ **ne zavisi** od broja GitHub pokretanja, pa ne nastaju nove objave pri ponavljanju testa.
6. Uključiti sekvencijalnu obradu ili odgovarajući lock; pre svakog objavljivanja proveriti stanje `PUBLISHED`, `SENDING`, `UNKNOWN` i postojeći ID objave. **NIKADA automatski ne ponavljati objavu** ako prethodni API poziv možda uspeo, a Make nije dobio potvrdu.
7. Kada se zasebno reši direktan, stabilan, javno dostupan HTTPS MP4 i provera redakcije, tek tada vezati izdavačke module. Instagram for Business → `Create a reel post`, Facebook Pages → `Publish a Reel`. TikTok zahteva odgovarajući modul/odobren nalog i posebnu proveru mogućnosti — modul za reklamne kampanje nije isto što i objavljivanje TikTok videa.
8. Obezbediti polje `provider_post_id` i status po platformi. Ažurirati u `PUBLISHED` tek kad API potvrdi uspešno objavljivanje i sačuvati ID/link.

## Neprekidna kontrola
- Nikada ne mešati naš kratki `Vesti u 20` Reels i postojeću zasebnu dugu/naratorsku emisiju (različiti formati, rizik dupliranja).
- U jednom danu jedna emisija može dobiti jedan ID po kanalu. Ako se sadržaj promeni, isti ID se blokira dok se ne razjasni stara objava.
- Samo dva medijska URL-a **ne znače** da su navodi nezavisno potvrđeni. Za visoko-rizične teme je potrebna redakcijska provera.
- Uz `Global Pulse` proveriti autorska prava za komercijalnu upotrebu na svakom kanalu i eventualna audio ograničenja platformi.
- Nikada ne ubacivati Make webhook URL, GitHub PAT, access token ili platformni ključ u javne datoteke, logove ili komentare PR-a.

## Sledeći konkretni koraci
1. Dobiti pristup postojećem Make nalogu u Make interfejsu, napraviti **novi izolovan test scenario**.
2. Proveriti prijem jednog probnog JSON-a bez slanja javnih objava.
3. Izabrati media hosting koji daje **direktan javni MP4 URL** i testirati da ga Instagram može preuzeti. GitHub Actions artifact to nije.
4. Tek posle provere sadržaja, veze i deduplikacije odlučiti o uključenju rasporeda i javnih objava.

Ovaj fajl je vodič; nije tvrdnja da su Make ili društvene mreže već spojene.
