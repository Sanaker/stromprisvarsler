# 🔌 Strømprisvarsler for Norge

Et Python-skript som automatisk henter strømpriser for valgt område i Norge (f.eks. NO1), beregner pris med strømstøtte og MVA, og sender deg et Pushover-varsel med høy- og lavprisperioder – komplett med graf! Perfekt for å vite når det lønner seg å lade bilen eller sette på vaskemaskina.

![graf-eksempel](graf.png)

## 🚀 Funksjoner

- Henter timespriser fra Nord Pool for valgt prisområde
- Justerer for strømstøtte og 25 % MVA
- Marker høy- og lavprisperioder
- Lager graf med fargekoder
- Sender Pushover-varsling én gang per dag via systemd timer
- Miljøvariabler for sikker deling (API-nøkler ligger ikke i koden)

## 🧰 Krav

- Python 3.10+
- Linux/macOS anbefalt
- En gratis Pushover-konto og en app token

## 📦 Avhengigheter

Installeres med pip:

```bash
pip install -r requirements.txt
```
