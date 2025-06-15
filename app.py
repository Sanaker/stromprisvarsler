import datetime
import requests 
from nordpool import elspot
import pytz
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from io import BytesIO
from dotenv import load_dotenv
import os
from flask import Flask, jsonify
import sys
import subprocess

# --- NYE DEBUGGING LINJER FOR MILJØBEKREFTELSE ---
print(f"Python executable being used: {sys.executable}")
try:
    result = subprocess.run([sys.executable, '-m', 'pip', 'freeze'], capture_output=True, text=True, check=True)
    print("Installed packages in this environment:")
    print(result.stdout)
except Exception as e:
    print(f"Could not list packages: {e}")
# --------------------------------------------------

load_dotenv()

# Konfigurasjon
AREA = "NO1"
LOW_THRESHOLD = 0.20
HIGH_THRESHOLD = 0.60
TIMEZONE = pytz.timezone('Europe/Oslo')

# Strømstøtte og MVA
MVA_RATE = 0.25
STROEMSTOTTE_DEKNING = 0.90
STROEMSTOTTE_GRENSE = 0.9375

# Funksjoner
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
    
    try:
        data = prices_spot.hourly(areas=[AREA], end_date=today)
        print(f"Data received from nordpool.hourly(): {data}")
        return data
    except Exception as e:
        print(f"Feil ved henting av priser med nordpool.hourly(): {e}")
        return None

# --- KORRIGERT parse_priser - håndterer 'areas' nøkkelen ---
def parse_priser(data):
    # Sjekker at 'areas' og 'AREA' og 'values' finnes
    if not data or 'areas' not in data or AREA not in data['areas'] or 'values' not in data['areas'][AREA]:
        print(f"Ugyldig eller manglende data fra nordpool.hourly() for område {AREA}.")
        return {}

    prices_by_hour = {}
    
    # Går gjennom listen av prisobjekter under data['areas'][AREA]['values']
    for item in data['areas'][AREA]['values']: # Korrigert sti her
        oslo_time = item['start'].astimezone(TIMEZONE)
        
        råpris_nok_kwh = item['value'] / 1000

        justert_pris_nok_kwh = juster_med_stotte(råpris_nok_kwh)
        justert_pris_mva = legg_til_mva(justert_pris_nok_kwh)
        råpris_mva = legg_til_mva(råpris_nok_kwh)

        prices_by_hour[oslo_time.strftime("%H:%M")] = {
            "råpris": råpris_nok_kwh,
            "justert_pris": justert_pris_nok_kwh,
            "råpris_mva": råpris_mva,
            "justert_mva": justert_pris_mva,
            "time_obj": oslo_time
        }
    return prices_by_hour

def lag_prisgraf(priser):
    if not priser:
        return None

    sorted_priser = sorted(priser.items(), key=lambda item: item[1]['time_obj'])

    tider = [item[0] for item in sorted_priser]
    råpriser = [item[1]["råpris_mva"] for item in sorted_priser]
    justerte_priser = [item[1]["justert_mva"] for item in sorted_priser]

    plt.figure(figsize=(12, 6))
    plt.plot(tider, råpriser, label="Råpris (inkl. MVA)", marker='o')
    plt.plot(tider, justerte_priser, label="Justert pris (inkl. MVA & strømstøtte)", marker='x')

    plt.axhline(y=LOW_THRESHOLD, color='g', linestyle='--', label=f'Lavprisgrense ({LOW_THRESHOLD:.2f} kr/kWh)')
    plt.axhline(y=HIGH_THRESHOLD, color='r', linestyle='--', label=f'Høyprisgrense ({HIGH_THRESHOLD:.2f} kr/kWh)')

    plt.xlabel("Tidspunkt")
    plt.ylabel("Pris (kr/kWh inkl. MVA)")
    plt.title(f"Strømpriser for {AREA} - {datetime.date.today().strftime('%d.%m.%Y')}")
    plt.xticks(rotation=45, ha="right")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()

    buf = BytesIO()
    plt.savefig(buf, format='png')
    plt.close()
    buf.seek(0)
    return buf.getvalue()

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
        
        if meldinger:
            print("\n".join(meldinger))
        else:
            print("Ingen varsel-triggere aktivert.")

        graf = lag_prisgraf(priser) 

    except Exception as e:
        print(f"Feil i hovedfunksjon: {str(e)}")


# Flask applikasjon
app = Flask(__name__)

@app.route('/')
def home():
    return "Velkommen til strømpris API. Bruk /prices for å hente prisdata."

@app.route('/prices')
def get_prices_json():
    try:
        data = hent_strømpriser()
        priser = parse_priser(data)
        
        if not priser:
            return jsonify({"error": "Kunne ikke hente eller tolke prisdata. Sjekk API-respons og logg."}), 500

        json_response = []
        for time_str, details in priser.items():
            json_response.append({
                "time": time_str,
                "raw_price": details["råpris"],
                "adjusted_price": details["justert_pris"],
                "raw_price_mva": details["råpris_mva"],
                "adjusted_mva": details["justert_mva"]
            })
        return jsonify(json_response)
    except Exception as e:
        print(f"Feil ved henting av priser: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)