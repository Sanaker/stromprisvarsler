import datetime
import requests
from nordpool import elspot
import pytz
import matplotlib.pyplot as plt
from io import BytesIO
from dotenv import load_dotenv
import os

from flask import Flask, jsonify, send_file # Importer Flask

load_dotenv()

app = Flask(__name__) # Initialiser Flask appen

# Konfigurasjon (kan flyttes til en config-fil eller miljøvariabler)
PUSHOVER_TOKEN = os.getenv("PUSHOVER_TOKEN") # Trengs ikke for API-et, men kan beholdes
PUSHOVER_USER = os.getenv("PUSHOVER_USER")   # Trengs ikke for API-et, men kan beholdes
AREA = "NO1"
LOW_THRESHOLD = 0.20
HIGH_THRESHOLD = 0.60
TIMEZONE = pytz.timezone('Europe/Oslo')

# Strømstøtte og MVA
MVA_RATE = 0.25
STROEMSTOTTE_DEKNING = 0.90
STROEMSTOTTE_GRENSE = 0.9375

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
    # Henter data for i dag og i morgen for å ha litt fremover
    data_today = prices_spot.hourly(areas=[AREA], end_date=today)
    tomorrow = today + datetime.timedelta(days=1)
    data_tomorrow = prices_spot.hourly(areas=[AREA], end_date=tomorrow)

    # Slå sammen dataene hvis begge er tilgjengelige
    combined_data = {}
    if AREA in data_today.get('areas', {}):
        combined_data.setdefault('areas', {})[AREA] = data_today['areas'][AREA]
    if AREA in data_tomorrow.get('areas', {}):
        if AREA in combined_data.get('areas', {}):
            combined_data['areas'][AREA]['values'].extend(data_tomorrow['areas'][AREA]['values'])
        else:
            combined_data.setdefault('areas', {})[AREA] = data_tomorrow['areas'][AREA]

    # Sorter etter starttid for å sikre riktig rekkefølge
    if AREA in combined_data.get('areas', {}):
        combined_data['areas'][AREA]['values'].sort(key=lambda x: x['start'])

    return combined_data


def parse_priser(data):
    priser_liste = [] # Endrer til liste av dictionary for enklere JSON-output
    if AREA in data.get('areas', {}):
        for hour_data in data['areas'][AREA]['values']:
            start_time = hour_data['start'].astimezone(TIMEZONE)
            time_str = start_time.strftime("%H:%M")
            date_str = start_time.strftime("%Y-%m-%d") # Legg til dato for klarhet

            råpris = hour_data['value'] / 1000
            justert = juster_med_stotte(råpris)

            priser_liste.append({
                "time": time_str,
                "date": date_str, # Inkluder dato
                "raw_price_mva": round(legg_til_mva(råpris), 4), # Bruk round for konsistent presisjon
                "adjusted_price_mva": round(legg_til_mva(justert), 4)
            })
    return priser_liste

def lag_prisgraf(priser_liste): # Endret til å ta imot listen direkte
    # Konverterer tilbake til dictionary for å passe eksisterende graf-logikk,
    # eller endre graf-logikken til å bruke liste direkte.
    # For enkelhets skyld konverterer vi tilbake her.
    priser_dict = {f"{p['date']} {p['time']}": {"råpris_mva": p["raw_price_mva"], "justert_mva": p["adjusted_price_mva"]} for p in priser_liste}

    tider = [p['time'] for p in priser_liste]
    # Forbedre x-aksen for grafer med to dager data
    # Hvis du viser to dager, kan det bli mange punkter. Du må vurdere hvordan du vil vise dem.
    # For en enkel graf, kan vi kanskje bare vise hver 4. time.
    display_tider = tider[::4] + [tider[-1]] if len(tider) > 1 else tider
    display_indices = list(range(0, len(tider), 4)) + ([len(tider) - 1] if (len(tider) - 1) % 4 != 0 else [])
    display_indices = sorted(list(set(display_indices))) # Unike og sorterte indekser

    råverdier = [p["raw_price_mva"] for p in priser_liste]
    justertverdier = [p["adjusted_price_mva"] for p in priser_liste]

    farger = []
    for pris in justertverdier:
        if pris <= LOW_THRESHOLD:
            farger.append('blue')
        elif pris >= HIGH_THRESHOLD:
            farger.append('red')
        else:
            farger.append('green')

    plt.figure(figsize=(12, 6)) # Større figur for mer data
    plt.plot(tider, råverdier, linestyle='--', label='Råpris + MVA', color='orange')
    plt.plot(tider, justertverdier, linestyle='-', label='Justert + MVA', color='gray')
    plt.scatter(tider, justertverdier, c=farger, s=40, edgecolors='black')

    plt.axhline(LOW_THRESHOLD, color='blue', linestyle='--', label=f'Lav terskel ({LOW_THRESHOLD} kr)')
    plt.axhline(HIGH_THRESHOLD, color='red', linestyle='--', label=f'Høy terskel ({HIGH_THRESHOLD} kr)')

    plt.title(f"Strømpris i {AREA} (inkl. MVA) - {datetime.date.today().strftime('%d.%m.%Y')}")
    plt.xlabel("Tidspunkt")
    plt.ylabel("kr/kWh")
    plt.xticks(display_indices, [tider[i] for i in display_indices], rotation=45) # Vis færre tider
    plt.grid(True)
    plt.legend()
    plt.tight_layout()

    buffer = BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    plt.close() # Lukk figuren for å frigi minne
    return buffer

# --- Flask API Endepunkter ---

@app.route('/prices', methods=['GET'])
def get_current_prices():
    try:
        data = hent_strømpriser()
        priser = parse_priser(data)
        if not priser:
            return jsonify({"error": "Ingen prisdata funnet"}), 404
        return jsonify(priser)
    except Exception as e:
        print(f"Feil ved henting av priser: {str(e)}")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

@app.route('/price_graph', methods=['GET'])
def get_price_graph():
    try:
        data = hent_strømpriser()
        priser = parse_priser(data)
        if not priser:
            return jsonify({"error": "Ingen prisdata funnet"}), 404

        graph_buffer = lag_prisgraf(priser)
        # Send_file krever at du kjenner content-type, og at buffer er "rewound"
        return send_file(graph_buffer, mimetype='image/png')
    except Exception as e:
        print(f"Feil ved generering av graf: {str(e)}")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

if __name__ == '__main__':
    # Kjør Flask-appen. Dette er kun for lokal testing.
    # I produksjon bør du bruke en WSGI-server som Gunicorn eller Waitress.
    app.run(debug=True, host='0.0.0.0', port=5000)