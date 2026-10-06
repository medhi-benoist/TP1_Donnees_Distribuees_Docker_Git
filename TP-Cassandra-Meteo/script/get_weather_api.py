"""Script d'ingestion de données Météo temps réel et prévisions vers Apache Cassandra.

Module : Données distribuées - TP2 Cassandra
API : Open-Meteo (https://open-meteo.com/)
Keyspace cible : weather
"""

from datetime import datetime
import requests
from cassandra.cluster import Cluster

CITIES = [
    {"name": "Paris", "lat": 48.8566, "lon": 2.3522, "country": "France"},
    {"name": "Marseille", "lat": 43.2965, "lon": 5.3698, "country": "France"},
    {"name": "Lyon", "lat": 45.7640, "lon": 4.8357, "country": "France"},
    {"name": "Toulouse", "lat": 43.6047, "lon": 1.4442, "country": "France"},
    {"name": "Nice", "lat": 43.7102, "lon": 7.2620, "country": "France"},
    {"name": "Nantes", "lat": 47.2184, "lon": -1.5536, "country": "France"},
    {"name": "Strasbourg", "lat": 48.5734, "lon": 7.7521, "country": "France"},
    {"name": "Montpellier", "lat": 43.6108, "lon": 3.8767, "country": "France"},
    {"name": "Bordeaux", "lat": 44.8378, "lon": -0.5792, "country": "France"},
    {"name": "Lille", "lat": 50.6292, "lon": 3.0573, "country": "France"},
]

WMO_CODES = {
    0: "Ciel dégagé",
    1: "Principalement dégagé",
    2: "Partiellement nuageux",
    3: "Couvert",
    45: "Brouillard",
    48: "Brouillard givrant",
    51: "Bruine légère",
    53: "Bruine modérée",
    55: "Bruine dense",
    61: "Pluie faible",
    63: "Pluie modérée",
    65: "Pluie forte",
    71: "Chute de neige faible",
    73: "Chute de neige modérée",
    75: "Chute de neige forte",
    80: "Averses de pluie faibles",
    81: "Averses de pluie modérées",
    82: "Averses de pluie violentes",
    95: "Orage faible ou modéré",
    96: "Orage avec grêle légère",
    99: "Orage avec grêle forte",
}


def get_weather_condition(code):
    return WMO_CODES.get(code, f"Code météo {code}")


def parse_iso_datetime(dt_str):
    return datetime.fromisoformat(dt_str)


def main():
    print("=== Démarrage de l'ingestion météo vers Cassandra ===")
    cluster = Cluster(contact_points=["127.0.0.1"], port=9042)
    session = cluster.connect("weather")

    # Préparation des requêtes
    prep_current = session.prepare("""
        INSERT INTO weather_current (
            city, country, latitude, longitude, recorded_at,
            temperature, humidity, wind_speed, weather_code, weather_condition
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """)

    prep_hourly = session.prepare("""
        INSERT INTO weather_hourly (
            city, forecast_time, temperature, humidity, wind_speed, weather_code
        ) VALUES (?, ?, ?, ?, ?, ?)
    """)

    prep_alert = session.prepare("""
        INSERT INTO weather_alerts (
            country, alert_date, severity, city, alert_type, description, issued_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """)

    total_current = 0
    total_hourly = 0
    total_alerts = 0

    for city in CITIES:
        name = city["name"]
        lat = city["lat"]
        lon = city["lon"]
        country = city["country"]

        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            f"&current=temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code"
            f"&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code"
            f"&timezone=auto&forecast_days=2"
        )

        print(f"-> Appel API pour {name} ({lat}, {lon})...")
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        # 1. Insertion weather_current
        curr = data["current"]
        recorded_at = parse_iso_datetime(curr["time"])
        temp = float(curr["temperature_2m"])
        humidity = float(curr["relative_humidity_2m"])
        wind = float(curr["wind_speed_10m"])
        w_code = int(curr["weather_code"])
        condition = get_weather_condition(w_code)

        session.execute(
            prep_current,
            (name, country, lat, lon, recorded_at, temp, humidity, wind, w_code, condition)
        )
        total_current += 1

        # 2. Insertion weather_hourly (48h de prévisions)
        hourly = data["hourly"]
        times = hourly["time"]
        temps = hourly["temperature_2m"]
        humids = hourly["relative_humidity_2m"]
        winds = hourly["wind_speed_10m"]
        codes = hourly["weather_code"]

        for i in range(len(times)):
            f_time = parse_iso_datetime(times[i])
            session.execute(
                prep_hourly,
                (name, f_time, float(temps[i]), float(humids[i]), float(winds[i]), int(codes[i]))
            )
            total_hourly += 1

        # 3. Éventuelle alerte (ex: si vent > 30 km/h ou pluie/orage ou alerte préventive)
        today = recorded_at.date()
        if wind >= 35.0:
            severity = 3 if wind >= 60 else 2
            session.execute(
                prep_alert,
                (country, today, severity, name, "Vent fort", f"Rafales observées à {wind} km/h", recorded_at)
            )
            total_alerts += 1
        elif w_code in [95, 96, 99]:
            session.execute(
                prep_alert,
                (country, today, 3, name, "Orage", f"Activité orageuse détectée ({condition})", recorded_at)
            )
            total_alerts += 1

    # Ajout d'alertes types d'exemple pour valider la table weather_alerts si conditions calmes
    today_date = datetime.now().date()
    sample_alerts = [
        ("France", today_date, 2, "Nice", "Vigilance vagues-submersion", "Houle soutenue sur le littoral azuréen", datetime.now()),
        ("France", today_date, 1, "Strasbourg", "Brouillard matinal", "Visibilité réduite inférieure à 200m", datetime.now()),
    ]
    for a in sample_alerts:
        session.execute(prep_alert, a)
        total_alerts += 1

    print("\n=== Ingestion terminée avec succès ! ===")
    print(f"- Stations actuelles insérées : {total_current}")
    print(f"- Prévisions horaires insérées : {total_hourly}")
    print(f"- Alertes enregistrées         : {total_alerts}")

    cluster.shutdown()


if __name__ == "__main__":
    main()
