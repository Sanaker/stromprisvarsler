🔌 Strømprisvarsler for Norge

Et Python-skript som automatisk henter strømpriser for valgt område i Norge (f.eks. NO1), beregner pris med strømstøtte og MVA, og sender deg et Pushover-varsel med høy- og lavprisperioder – komplett med graf! Perfekt for å vite når det lønner seg å lade bilen eller sette på vaskemaskina.



🚀 Funksjoner

Henter timespriser fra Nord Pool for valgt prisområde

Justerer for strømstøtte og 25 % MVA

Marker høy- og lavprisperioder

Lager graf med fargekoder

Sender Pushover-varsling én gang per dag via systemd timer

Miljøvariabler for sikker deling (API-nøkler ligger ikke i koden)

🧰 Krav

Python 3.10+

Linux/macOS anbefalt

En gratis Pushover-konto og en app token

🎞️ Avhengigheter

Installeres med pip:
```bash
pip install -r requirements.txt
```
Eksempel på requirements.txt:
```pip
requests
matplotlib
nordpool
python-dotenv
pytz
```
⚙️ Oppsett

1. Klon repoet
```bash
git clone https://github.com/dittbrukernavn/stromprisvarsler.git
cd stromprisvarsler
```
2. Lag .env-fil

Lag en .env-fil i prosjektmappen med følgende innhold:
```
PUSHOVER_TOKEN=din_pushover_app_token
PUSHOVER_USER=din_pushover_user_key
```
3. Tilpass konfigurasjon i skriptet

I Python-skriptet (stromvarsler.py), sett riktig prisområde:

AREA = "NO1"  # For eksempel: NO1 for Østlandet

Du kan også justere terskelverdier for varsling:
```python
LOW_THRESHOLD = 0.20  # Lavpris grense
HIGH_THRESHOLD = 0.60  # Høypris grense
```
4. Sett opp daglig varsling med systemd (Linux)
```bash
mkdir -p ~/.config/systemd/user
```
Opprett stromvarsler.service:
```bash
[Unit]
Description=Daglig strømprisvarsel

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 /full/stien/til/stromvarsler.py
WorkingDirectory=/full/stien/til/prosjektmappen
Environment="PYTHONUNBUFFERED=1"
```
```bash
Opprett stromvarsler.timer:

[Unit]
Description=Kjør strømprisvarsler daglig kl. 08:00

[Timer]
OnCalendar=*-*-* 08:00:00
Persistent=true
Unit=stromvarsler.service

[Install]
WantedBy=timers.target
```
Aktiver timeren:
```bash
systemctl --user daemon-reload
systemctl --user enable --now stromvarsler.timer
```
🛡️ Sikkerhet

API-nøkler lagres i .env, og .env bør være i .gitignore for å hindre lekkasje.

Du kan rotere Pushover-nøkler på pushover.net ved behov.

🧪 Eksempelutdata

Varseltekst:

⚡ LAVPRIS 03:00: 0.19 kr/kWh
🔥 HØYPRIS 18:00: 0.78 kr/kWh

Graf:

Blå: Lavpris

Grønn: Normal

Rød: Høypris

📍 Om prisområder

De viktigste nordiske prisområdene hos Nord Pool:

NO1: Østlandet (Oslo, Tønsberg, m.m.)

NO2: Sørvest (Kristiansand, Stavanger)

NO3: Midt-Norge (Trondheim)

NO4: Nord-Norge (Tromsø, Bodø)

NO5: Vestlandet (Bergen)

📄 Lisens

Dette prosjektet er delt under MIT-lisens. Bruk det fritt og bidra gjerne!

🂨 Laget med 💡 og mye Monster av Sanaker
