# TP2 — Exploitation des données Météo avec Apache Cassandra

**M2 Big Data & IA — Données distribuées**  
**Sujet :** Données météorologiques en temps réel et prévisions horaires  
**API :** [Open-Meteo](https://open-meteo.com/) — Gratuite, sans clé API

---

## 1. Sujet

Ce projet exploite l'API **Open-Meteo** pour collecter des données météorologiques
sur les 10 plus grandes villes françaises et les stocker dans **Apache Cassandra**.

L'objectif est de démontrer la modélisation orientée-requêtes propre à Cassandra,
en opposition au modèle relationnel classique.

---

## 2. Données récupérées

| Catégorie | Description |
|-----------|-------------|
| **Météo courante** | Température, humidité, vitesse du vent, code météo |
| **Prévisions horaires** | Prévisions sur 7 jours (168 points par ville) |
| **Alertes** | Alertes simulées (ex. vague de chaleur, vents violents) |

**Villes couvertes :** Paris, Lyon, Marseille, Bordeaux, Toulouse, Nantes,
Strasbourg, Lille, Nice, Rennes

**Principaux champs :**
- `city` (text) — Nom de la ville
- `country` (text) — Pays
- `latitude`, `longitude` (double) — Coordonnées GPS
- `recorded_at` / `forecast_time` (timestamp) — Horodatage
- `temperature` (double) — En °C
- `humidity` (double) — En %
- `wind_speed` (double) — En km/h
- `weather_code` (int) — Code WMO standard
- `severity` (int) — Niveau d'alerte : 1=Jaune, 2=Orange, 3=Rouge

---

## 3. Modèle Cassandra

**Keyspace :** `weather` (SimpleStrategy, Replication Factor = 1)

```text
┌─────────────────────────────────────────────────────────┐
│                    Keyspace : weather                    │
│                                                         │
│  weather_current          weather_hourly                │
│  PK: city                 PK: (city) | forecast_time ↓  │
│  → Snapshot actuel        → Séries temporelles          │
│                                                         │
│  weather_alerts                                         │
│  PK: (country, alert_date) | severity ↓, city ↑        │
│  → Alertes par criticité                                │
└─────────────────────────────────────────────────────────┘
```

> Voir [`documentation/modelisation.md`](documentation/modelisation.md) pour
> les détails complets des choix de modélisation.

---

## 4. Requêtes métier principales

| ID | Besoin | Table |
|----|--------|-------|
| REQ-01 | Météo actuelle d'une ville | `weather_current` |
| REQ-02 | Historique des 24 dernières heures | `weather_hourly` |
| REQ-03 | Toutes les prévisions d'une ville | `weather_hourly` |
| REQ-04 | Alertes du jour par pays, triées par sévérité | `weather_alerts` |
| REQ-05 | Comparaison météo entre plusieurs villes | `weather_current` |

> Voir [`queries/03_requetes_metier.sql`](queries/03_requetes_metier.sql) pour
> les requêtes CQL complètes avec justifications.

---

## 5. Structure du dépôt

```text
TP-Cassandra-Velib/
│
├── README.md                          ← Ce fichier
├── docker-compose.yml                 ← Cassandra en Docker (node unique)
├── schema_weather.cql                 ← Keyspace + 3 tables
├── requirements.txt                   ← Dépendances Python
│
├── script/
│   └── get_weather_api.py             ← Ingestion Open-Meteo → Cassandra
│
├── queries/
│   ├── 01_verification.sql            ← Vérification du schéma et données
│   ├── 02_crud.sql                    ← INSERT, SELECT, UPDATE, DELETE
│   └── 03_requetes_metier.sql         ← 5 requêtes métier commentées
│
└── documentation/
    └── modelisation.md                ← Choix de modélisation, clés, justifications
```

---

## 6. Lancement rapide

### Prérequis
- Docker & Docker Compose
- Python 3.9+

### Démarrage Cassandra

```bash
cd TP-Cassandra-Velib
docker-compose up -d

# Attendre ~30s que Cassandra soit prêt
docker exec -it cassandra-tp cqlsh -e "DESCRIBE KEYSPACES;"
```

### Appliquer le schéma

```bash
docker cp schema_weather.cql cassandra-tp:/schema_weather.cql
docker exec -it cassandra-tp cqlsh -f /schema_weather.cql
```

### Ingestion des données

```bash
# Créer l'environnement virtuel (première fois)
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt

# Lancer l'ingestion
.\.venv\Scripts\python script/get_weather_api.py
```

### Vérification

```bash
docker exec -it cassandra-tp cqlsh -e "
USE weather;
SELECT city, temperature, humidity FROM weather_current LIMIT 10;
"
```

---

## 7. Technologie

| Composant | Technologie |
|-----------|-------------|
| Base de données | Apache Cassandra 4.1 |
| Langage | Python 3.x |
| Driver | `cassandra-driver` |
| API météo | Open-Meteo (open-meteo.com) |
| Orchestration | Docker Compose |
| Requêtes | CQL (Cassandra Query Language) |
