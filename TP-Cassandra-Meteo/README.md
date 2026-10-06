# TP2 — Données météo avec Apache Cassandra

**M2 Big Data & IA — Données distribuées**

---

## Sujet

Pour ce TP, j'ai choisi de travailler sur des données météorologiques en utilisant l'API **Open-Meteo** (https://open-meteo.com/). C'est une API gratuite qui ne nécessite pas de clé d'authentification, et qui fournit des prévisions horaires ainsi que les conditions météo actuelles pour n'importe quelle ville dans le monde.

---

## Données récupérées

J'ai collecté les données pour **10 grandes villes françaises** : Paris, Lyon, Marseille, Bordeaux, Toulouse, Nantes, Strasbourg, Lille, Nice et Rennes.

Les informations récupérées sont :
- La météo actuelle (température, humidité, vitesse du vent, état du ciel)
- Les prévisions heure par heure sur 7 jours (~168 points par ville)
- Des alertes météo (vents, houle, brouillard…)

Principaux champs utilisés :
- `city` — nom de la ville
- `country` — pays
- `latitude`, `longitude` — coordonnées
- `recorded_at` / `forecast_time` — horodatage de la mesure ou prévision
- `temperature` — en °C
- `humidity` — en %
- `wind_speed` — en km/h
- `weather_code` — code WMO de la condition météo
- `severity` — niveau d'alerte (1=Jaune, 2=Orange, 3=Rouge)

---

## Modèle Cassandra

**Keyspace :** `weather`

J'ai créé 3 tables selon les types de requêtes que je voulais faire :

```
weather_current   → une ligne par ville, météo instantanée
weather_hourly    → séries temporelles (prévisions heure par heure)
weather_alerts    → alertes regroupées par pays et par date
```

Le schéma complet est dans `schema_weather.cql`.  
Les choix de modélisation sont expliqués dans `documentation/modelisation.md`.

---

## Requêtes métier

J'ai identifié 5 besoins principaux :

| ID | Besoin |
|----|--------|
| REQ-01 | Météo actuelle d'une ville précise |
| REQ-02 | Historique des dernières heures (pour un graphique) |
| REQ-03 | Toutes les prévisions d'une ville |
| REQ-04 | Alertes du jour par pays, triées par criticité |
| REQ-05 | Comparaison météo entre plusieurs villes |

Les requêtes CQL sont dans `queries/03_requetes_metier.sql`.

---

## Structure du projet

```
TP-Cassandra-Meteo/
│
├── README.md
├── docker-compose.yml          ← Cassandra en Docker (nœud unique)
├── schema_weather.cql          ← Création du keyspace et des tables
├── requirements.txt            ← Dépendances Python
│
├── script/
│   └── get_weather_api.py      ← Script d'ingestion des données météo
│
├── queries/
│   ├── 01_verification.sql     ← Vérification du schéma et des données
│   ├── 02_crud.sql             ← INSERT, SELECT, UPDATE, DELETE
│   └── 03_requetes_metier.sql  ← 5 requêtes métier commentées
│
└── documentation/
    ├── modelisation.md         ← Explication des choix de modélisation
    └── captures_resultats.md   ← Résultats des requêtes dans cqlsh
```

---

## Lancer le projet

### Démarrer Cassandra

```bash
docker-compose up -d
# Attendre environ 30 secondes
docker exec -it cassandra cqlsh -e "DESCRIBE KEYSPACES;"
```

### Appliquer le schéma

```bash
docker cp schema_weather.cql cassandra:/schema_weather.cql
docker exec -it cassandra cqlsh -f /schema_weather.cql
```

### Ingérer les données

```bash
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\python script/get_weather_api.py
```
