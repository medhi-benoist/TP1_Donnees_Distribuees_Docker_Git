"""Script d'ingestion de données réelles Vélib' vers Apache Cassandra.

Module : Données distribuées - TP Cassandra Vélib
"""

import requests
from cassandra.cluster import Cluster


def fetch_velib_data(limit=20):
    url = f"https://opendata.paris.fr/api/explore/v2.1/catalog/datasets/velib-emplacement-des-stations/records?limit={limit}"
    print(f"Récupération des données Vélib' (limite = {limit})...")
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    payload = response.json()
    records = payload.get("results", [])
    print(f"{len(records)} stations récupérées depuis l'API.")
    return records


def insert_stations_to_cassandra(records, contact_points=["127.0.0.1"], port=9042):
    print(f"Connexion au cluster Cassandra sur {contact_points}:{port}...")
    cluster = Cluster(contact_points=contact_points, port=port)
    session = cluster.connect("velib")

    query = """
    INSERT INTO stations (
        station_id,
        name,
        capacity,
        latitude,
        longitude,
        opening_hours
    )
    VALUES (?, ?, ?, ?, ?, ?)
    """
    prepared = session.prepare(query)

    print("Insertion des stations dans la table velib.stations...")
    for rec in records:
        station_id = str(rec.get("stationcode", "")).strip()
        name = rec.get("name")
        capacity = rec.get("capacity")
        coords = rec.get("coordonnees_geo") or {}
        latitude = coords.get("lat")
        longitude = coords.get("lon")
        opening_hours = rec.get("station_opening_hours")

        session.execute(
            prepared,
            (station_id, name, capacity, latitude, longitude, opening_hours),
        )
        print(f"Station importée : {station_id} - {name}")

    print("Import terminé avec succès !")
    cluster.shutdown()


if __name__ == "__main__":
    stations = fetch_velib_data(limit=20)
    insert_stations_to_cassandra(stations)
