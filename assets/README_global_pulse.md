# Originalna muzika za TRAG 24 Reels

Očekivana lokacija: `assets/global_pulse.m4a` (tačan naziv malim slovima).

Kada korisnik doda **svoj** fajl `Global Pulse.m4a` u ovaj folder pod navedenim imenom, probni GitHub Actions automatski pravi i `0800_reel_sa_muzikom.mp4`, `1100_reel_sa_muzikom.mp4`, `1400_reel_sa_muzikom.mp4`, `1700_reel_sa_muzikom.mp4`, `2000_reel_sa_muzikom.mp4`, `2300_reel_sa_muzikom.mp4`.

- Ne menja originalne neme MP4 fajlove.
- Muzika: normalizovana relativno na ulaz (`volume=0.73`), fade-in 0,35 s, fade-out 1,4 s; AAC 160 kbps.
- Ne zamenjuje naratorski govor. Skripta odbija video koji već ima zvuk.
- U ovoj probnoj fazi nema javnog objavljivanja.
- Pre puštanja na mreže proveriti pravo na komercijalnu upotrebu muzičkog snimka.

Dok originalna audio datoteka nije dodata u GitHub, automatika samo beleži obaveštenje i ostavlja probne video-fajlove bez zvuka. Lokalni snimci sa muzikom već su napravljeni za korisnikov pregled.
