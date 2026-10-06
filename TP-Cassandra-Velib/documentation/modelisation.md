# Modélisation Cassandra — TP2 Météo

## M2 Big Data & IA — Données distribuées

> **Principe fondamental :** Dans Cassandra, on ne modélise pas les données,
> on modélise les **requêtes**. Chaque table est conçue pour répondre à un
> besoin d'accès précis, sans ALLOW FILTERING ni JOIN.

---

## 1. Vue d'ensemble du modèle

```text
API Open-Meteo
      ↓
┌─────────────────────────────────────────────────────────┐
│  Keyspace : weather  (SimpleStrategy, RF=1)             │
│                                                         │
│  ┌─────────────────────┐  ┌──────────────────────────┐ │
│  │  weather_current     │  │  weather_hourly           │ │
│  │  PK: city            │  │  PK: (city) + time DESC   │ │
│  │  1 ligne / ville     │  │  Séries temporelles       │ │
│  └─────────────────────┘  └──────────────────────────┘ │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │  weather_alerts                                  │   │
│  │  PK: (country, alert_date) + severity, city      │   │
│  │  Alertes triées par criticité                    │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

---

## 2. Tables et choix de modélisation

### 2.1 `weather_current` — Météo instantanée par ville

```cql
CREATE TABLE weather_current (
    city             text,
    country          text,
    latitude         double,
    longitude        double,
    recorded_at      timestamp,
    temperature      double,
    humidity         double,
    wind_speed       double,
    weather_code     int,
    weather_condition text,
    PRIMARY KEY (city)
);
```

| Composant | Valeur | Justification |
|-----------|--------|---------------|
| **Partition Key** | `city` | Accès O(1) par nom de ville — usage le plus fréquent |
| **Clustering Key** | aucune | Une seule ligne par ville (snapshot actuel) |
| **Cardinalité** | ~1 ligne/ville | Lecture ultra-rapide, pas de fan-out |

**Choix de conception :**
- On stocke une seule ligne "courante" par ville (UPSERT à chaque ingestion).
- Idéal pour les widgets "météo du moment" où la latence est critique.
- Si l'historique est nécessaire → utiliser `weather_hourly`.

---

### 2.2 `weather_hourly` — Séries temporelles horaires

```cql
CREATE TABLE weather_hourly (
    city          text,
    forecast_time timestamp,
    temperature   double,
    humidity      double,
    wind_speed    double,
    weather_code  int,
    PRIMARY KEY ((city), forecast_time)
) WITH CLUSTERING ORDER BY (forecast_time DESC);
```

| Composant | Valeur | Justification |
|-----------|--------|---------------|
| **Partition Key** | `city` | Toutes les données d'une ville dans une partition |
| **Clustering Key** | `forecast_time DESC` | Les données les plus récentes en tête de partition |
| **Cardinalité** | ~168 lignes/ville/semaine | Scans séquentiels rapides dans le SSTable |

**Choix de conception :**
- `CLUSTERING ORDER BY DESC` : les 24 dernières heures sont lues séquentiellement dès le début de la partition, sans parcourir tout l'historique.
- Range queries (`WHERE forecast_time BETWEEN ...`) sont efficaces car les données sont triées physiquement sur disque.
- Évite `ALLOW FILTERING` grâce au clustering key sur la dimension temps.

**Trade-off :**
- Si on voulait regrouper par pays, il faudrait une table dédiée `weather_hourly_by_country`. Ici on privilégie la requête par ville.

---

### 2.3 `weather_alerts` — Alertes météo par pays et date

```cql
CREATE TABLE weather_alerts (
    country    text,
    alert_date date,
    severity   int,   -- 1=Jaune, 2=Orange, 3=Rouge
    city       text,
    alert_type   text,
    description  text,
    issued_at    timestamp,
    PRIMARY KEY ((country, alert_date), severity, city)
) WITH CLUSTERING ORDER BY (severity DESC, city ASC);
```

| Composant | Valeur | Justification |
|-----------|--------|---------------|
| **Partition Key** | `(country, alert_date)` | Toutes les alertes d'un pays pour un jour → même nœud |
| **Clustering Key 1** | `severity DESC` | Les alertes rouges (3) apparaissent en premier |
| **Clustering Key 2** | `city ASC` | Tri alphabétique secondaire pour la lisibilité |

**Choix de conception :**
- **Clé de partition composite** `(country, alert_date)` : garantit que toutes les alertes du jour pour un pays donné sont co-localisées. Évite les requêtes scatter-gather multi-nœuds.
- **Severity DESC** dans le clustering : permet à un opérateur de sécurité de lire les alertes les plus critiques en premier, sans ORDER BY côté applicatif.
- Si on avait juste `country` comme partition key, une partition contiendrait toutes les alertes de l'historique → tombstones et partitions chaudes à éviter.

---

## 3. Les 5 besoins métier et leurs requêtes

### REQ-01 — Consulter la météo actuelle d'une ville

**Besoin :** Un utilisateur ouvre l'application et veut connaître la météo
actuelle de Paris (température, humidité, vent, condition).

```cql
SELECT city, country, temperature, humidity, wind_speed,
       weather_condition, recorded_at
FROM weather_current
WHERE city = 'Paris';
```

| | |
|---|---|
| **Partition Key utilisée** | `city = 'Paris'` |
| **Clustering Key** | N/A |
| **ALLOW FILTERING** | ❌ Non nécessaire |
| **Complexité** | O(1) — accès direct à la partition |

---

### REQ-02 — Historique des 24 dernières heures pour un graphique

**Besoin :** Un dashboard affiche l'évolution de la température heure par heure
sur les 24 dernières heures pour Lyon.

```cql
SELECT city, forecast_time, temperature, humidity, wind_speed
FROM weather_hourly
WHERE city = 'Lyon'
  AND forecast_time >= '2025-01-01 00:00:00'
  AND forecast_time <= '2025-01-02 00:00:00';
```

| | |
|---|---|
| **Partition Key utilisée** | `city = 'Lyon'` |
| **Clustering Key (range)** | `forecast_time BETWEEN ...` |
| **ALLOW FILTERING** | ❌ Non nécessaire (range sur clustering key) |
| **Complexité** | O(n) sur la plage horaire uniquement |

---

### REQ-03 — Toutes les prévisions disponibles pour une ville

**Besoin :** Une application de planification récupère tous les points de données
météo disponibles pour Marseille afin d'alimenter un graphe multi-jours.

```cql
SELECT city, forecast_time, temperature, humidity, wind_speed, weather_code
FROM weather_hourly
WHERE city = 'Marseille';
```

| | |
|---|---|
| **Partition Key utilisée** | `city = 'Marseille'` |
| **Clustering Key** | Scan complet de la partition (DESC) |
| **ALLOW FILTERING** | ❌ Non nécessaire |
| **Complexité** | O(n) sur la partition, séquentiel dans le SSTable |

---

### REQ-04 — Alertes du jour en France, triées par sévérité

**Besoin :** Un opérateur de sécurité civile consulte les alertes météo actives
en France aujourd'hui, en voyant en priorité les alertes rouges (les plus graves).

```cql
SELECT country, alert_date, severity, city, alert_type, description, issued_at
FROM weather_alerts
WHERE country = 'France'
  AND alert_date = '2025-01-01';
```

| | |
|---|---|
| **Partition Key utilisée** | `(country='France', alert_date='2025-01-01')` |
| **Clustering Key** | Lecture dans l'ordre `severity DESC` automatique |
| **ALLOW FILTERING** | ❌ Non nécessaire |
| **Complexité** | O(k) où k = nombre d'alertes du jour |

---

### REQ-05 — Comparaison météo entre plusieurs villes (widget Top 10)

**Besoin :** Un widget dashboard affiche côte à côte la météo actuelle des
10 plus grandes villes françaises pour comparer les conditions.

```cql
SELECT city, temperature, humidity, wind_speed, weather_condition, recorded_at
FROM weather_current
WHERE city IN ('Paris', 'Lyon', 'Marseille', 'Bordeaux', 'Toulouse',
               'Nantes', 'Strasbourg', 'Lille', 'Nice', 'Rennes');
```

| | |
|---|---|
| **Partition Key utilisée** | `city IN (...)` — 10 lectures directes |
| **Clustering Key** | N/A |
| **ALLOW FILTERING** | ❌ Non nécessaire |
| **Complexité** | O(1) × 10 = Cassandra peut paralléliser sur les nœuds |

> **Note :** La clause `IN` sur une partition key est l'usage recommandé dans
> Cassandra quand le nombre de valeurs est maîtrisé (< ~20). Chaque ville est
> lue directement sur son nœud responsable.

---

## 4. Récapitulatif des choix d'architecture

| Table | Pattern | Requête optimisée |
|-------|---------|-------------------|
| `weather_current` | Key-Value simple | Lecture par ville en O(1) |
| `weather_hourly` | Time Series | Range queries sur timestamp |
| `weather_alerts` | Partition composite + clustering multi-critères | Alertes groupées pays/date triées par criticité |

### Ce qu'on a évité :
- ❌ `ALLOW FILTERING` → filtrage côté Cassandra coûteux et non scalable
- ❌ `JOIN` → inexistant dans Cassandra, modèle dénormalisé volontairement
- ❌ Partition unique avec toutes les données → hot partition et lecture lente
- ❌ Clé primaire trop large → mauvaise localité des données

### Ce qu'on a appliqué :
- ✅ **Query-first design** : une table = un besoin d'accès
- ✅ **Clustering key pour les range queries** sur les séries temporelles
- ✅ **Partition composite** pour co-localiser les alertes par (pays, date)
- ✅ **CLUSTERING ORDER** pour éviter le tri applicatif sur la criticité

---

## 5. Source des données

- **API :** [Open-Meteo](https://open-meteo.com/) (gratuite, sans clé API)
- **Données ingérées :** Prévisions horaires sur 7 jours pour 10 villes françaises
- **Fréquence de mise à jour :** À la demande (script `script/get_weather_api.py`)
- **Volume :** ~480 prévisions horaires + météo courante + alertes synthétiques
