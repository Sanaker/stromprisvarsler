import datetime
import requests
from nordpool import elspot
import pytz
import matplotlib.pyplot as plt
from io import BytesIO
from dotenv import load_dotenv
import os

load_dotenv()  # Load environment variables from .env file if available

# Konfigurasjon
PUSHOVER_TOKEN = os.getenv("PUSHOVER_TOKEN")
PUSHOVER_USER = os.getenv("PUSHOVER_USER")
AREA = "NO1"  # F.eks. NO1 for Tønsberg/Oslo
LOW_THRESHOLD = 0.20
HIGH_THRESHOLD = 0.60
TIMEZONE = pytz.timezone('Europe/Oslo')

# Strømstøtte og MVA
MVA_RATE = 0.25
STROEMSTOTTE_DEKNING = 0.90 # 90% dekning av støtten
STROEMSTOTTE_GRENSE = 0.9375  # i NOK

def legg_til_mva(pris):
    return pris * (1 + MVA_RATE)

def juster_med_stotte(pris):
    if pris > STROEMSTOTTE_GRENSE:
        støtte = (pris - STROEMSTOTTE_GRENSE) * STROEMSTOTTE_DEKNING
    else:
        støtte = 0
    return pris - støtte

def hent_strømpriser():
    prices_spot = elspot.Prices(currency="NOK")
    today = datetime.date.today()
    data = prices_spot.hourly(areas=[AREA], end_date=today)
    return data

def parse_priser(data):
    priser = {}

    if AREA in data.get('areas', {}):
        for hour_data in data['areas'][AREA]['values']:
            start_time = hour_data['start'].astimezone(TIMEZONE)
            time_str = start_time.strftime("%H:%M")

            råpris = hour_data['value'] / 1000  # Fra NOK/MWh til NOK/kWh
            justert = juster_med_stotte(råpris)

            priser[time_str] = {
                "råpris_mva": legg_til_mva(råpris),
                "justert_mva": legg_til_mva(justert)
            }

    return priser

def lag_prisgraf(priser):
    tider = list(priser.keys())
    råverdier = [v["råpris_mva"] for v in priser.values()]
    justertverdier = [v["justert_mva"] for v in priser.values()]

    farger = []
    for pris in justertverdier:
        if pris <= LOW_THRESHOLD:
            farger.append('blue')
        elif pris >= HIGH_THRESHOLD:
            farger.append('red')
        else:
            farger.append('green')

    plt.figure(figsize=(10, 4))
    plt.plot(tider, råverdier, linestyle='--', label='Råpris + MVA', color='orange')
    plt.plot(tider, justertverdier, linestyle='-', label='Justert + MVA', color='gray')
    plt.scatter(tider, justertverdier, c=farger, s=40, edgecolors='black')

    plt.axhline(LOW_THRESHOLD, color='blue', linestyle='--', label=f'Lav terskel ({LOW_THRESHOLD} kr)')
    plt.axhline(HIGH_THRESHOLD, color='red', linestyle='--', label=f'Høy terskel ({HIGH_THRESHOLD} kr)')

    plt.title("Strømpris i dag (inkl. MVA)")
    plt.xlabel("Tidspunkt")
    plt.ylabel("kr/kWh")
    plt.xticks(rotation=45)
    plt.grid(True)
    plt.legend()
    plt.tight_layout()

    buffer = BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    return buffer

def send_pushover_notification(message, image_data=None):
    url = "https://api.pushover.net/1/messages.json"
    payload = {
        "token": PUSHOVER_TOKEN,
        "user": PUSHOVER_USER,
        "message": message,
        "title": "Strømprisvarsel",
        "sound": "cashregister"
    }

    files = None
    if image_data:
        files = {
            "attachment": ("graf.png", image_data, "image/png")
        }

    try:
        response = requests.post(url, data=payload, files=files)
        response.raise_for_status()
        print("Varsel sendt til Pushover!")
    except Exception as e:
        print(f"Pushover Error: {str(e)}")

def sjekk_priser():
    try:
        data = hent_strømpriser()
        priser = parse_priser(data)

        if not priser:
            print("Ingen prisdata funnet")
            return

        meldinger = []
        for tidspunkt, p in priser.items():
            pris_j = p["justert_mva"]
            pris_r = p["råpris_mva"]

            if pris_j <= LOW_THRESHOLD:
                meldinger.append(f"⚡ LAVPRIS {tidspunkt}: {pris_j:.2f} kr/kWh (rå: {pris_r:.2f})")
            elif pris_j >= HIGH_THRESHOLD:
                meldinger.append(f"🔥 HØYPRIS {tidspunkt}: {pris_j:.2f} kr/kWh (rå: {pris_r:.2f})")

        graf = lag_prisgraf(priser)

        if meldinger:
            send_pushover_notification("\n".join(meldinger), image_data=graf)
        else:
            print("Ingen varsel-triggere aktivert.")
    except Exception as e:
        print(f"Feil i hovedfunksjon: {str(e)}")

if __name__ == "__main__":
    sjekk_priser()
# This script checks electricity prices, generates a graph, and sends notifications via Pushover.
# It includes support for VAT and electricity subsidies.
# It uses the Nordpool API to fetch hourly prices for a specified area.
# It also handles low and high price thresholds for notifications.
# The graph is generated using Matplotlib and sent as an attachment in the notification.
# The script is designed to run daily and can be scheduled using a task scheduler.