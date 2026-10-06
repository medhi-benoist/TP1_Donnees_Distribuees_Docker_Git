# Modélisation Cassandra — TP2 Météo

## M2 Big Data & IA — Données distribuées

Dans Cassandra, la logique de modélisation est différente d'une base relationnelle. On ne part pas des données pour définir les tables, mais des **requêtes que l'application va faire**. Chaque table est donc conçue pour répondre à un type d'accès précis, ce qui évite d'avoir recours à `ALLOW FILTERING` ou à des jointures (qui n'existent pas dans Cassandra).

---

## 1. Vue d'ensemble du modèle

Le keyspace `weather` contient 3 tables :

```
weather_current    → météo actuelle, une ligne par ville
weather_hourly     → prévisions heure par heure, organisées par ville et par temps
weather_alerts     → alertes météo, regroupées par pays et par date
```

Chaque table correspond à un besoin d'accès différent.

---

## 2. Détail des tables

### Table `weather_current`

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

**Clé de partition :** `city`

J'ai choisi `city` comme clé de partition parce que la requête principale sur cette table est "donne-moi la météo actuelle de telle ville". Avec cette clé, Cassandra sait directement sur quel nœud aller chercher la donnée, sans parcourir les autres.

Il n'y a pas de clé de clustering car on ne stocke qu'une seule ligne par ville — le snapshot courant. À chaque ingestion, la ligne est mise à jour (UPSERT).

---

### Table `weather_hourly`

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

**Clé de partition :** `city`  
**Clé de clustering :** `forecast_time DESC`

Cette table est faite pour les requêtes de type "donne-moi les prévisions des dernières 24h pour Lyon". La clé de partition est `city` pour regrouper toutes les données d'une même ville ensemble. La clé de clustering `forecast_time` permet de faire des requêtes sur des plages de temps (`WHERE forecast_time BETWEEN ...`) directement dans Cassandra, sans tri supplémentaire côté application.

L'ordre `DESC` fait que les données les plus récentes apparaissent en premier, ce qui est pratique pour afficher un graphique ou les dernières mesures.

---

### Table `weather_alerts`

```cql
CREATE TABLE weather_alerts (
    country    text,
    alert_date date,
    severity   int,
    city       text,
    alert_type   text,
    description  text,
    issued_at    timestamp,
    PRIMARY KEY ((country, alert_date), severity, city)
) WITH CLUSTERING ORDER BY (severity DESC, city ASC);
```

**Clé de partition :** `(country, alert_date)` — composite  
**Clé de clustering :** `severity DESC`, `city ASC`

Pour les alertes, le besoin principal est "donne-moi toutes les alertes en France pour aujourd'hui, de la plus grave à la moins grave". J'ai utilisé une clé de partition composite `(country, alert_date)` pour que toutes les alertes d'un pays pour un jour donné soient stockées dans la même partition — ça évite d'interroger plusieurs nœuds pour une même requête.

Le clustering sur `severity DESC` fait remonter automatiquement les alertes rouges (niveau 3) avant les oranges (2) et les jaunes (1), sans avoir à trier après coup.

---

## 3. Les 5 besoins métier

### REQ-01 — Consulter la météo actuelle d'une ville

**Besoin :** afficher les conditions météo en cours pour une ville donnée.

```cql
SELECT city, country, temperature, humidity, wind_speed,
       weather_condition, recorded_at
FROM weather_current
WHERE city = 'Paris';
```

La clé de partition `city` permet un accès direct à la donnée. Pas de ALLOW FILTERING, pas de scan de table.

---

### REQ-02 — Historique horaire des dernières 24h

**Besoin :** tracer un graphique d'évolution de la température sur 24h pour une ville.

```cql
SELECT city, forecast_time, temperature, humidity, wind_speed
FROM weather_hourly
WHERE city = 'Lyon'
  AND forecast_time >= '2025-01-01 00:00:00'
  AND forecast_time <= '2025-01-02 00:00:00';
```

La requête utilise la partition key `city` et une plage sur la clustering key `forecast_time`. Les données étant triées physiquement par temps dans le SSTable, la lecture est séquentielle et rapide.

---

### REQ-03 — Toutes les prévisions disponibles d'une ville

**Besoin :** récupérer l'ensemble des prévisions pour alimenter un affichage sur plusieurs jours.

```cql
SELECT city, forecast_time, temperature, humidity, wind_speed, weather_code
FROM weather_hourly
WHERE city = 'Marseille';
```

On lit toute la partition de la ville en une seule passe. Efficace car les données sont co-localisées.

---

### REQ-04 — Alertes du jour, triées par niveau de gravité

**Besoin :** un opérateur veut voir en priorité les alertes les plus graves pour la France aujourd'hui.

```cql
SELECT country, alert_date, severity, city, alert_type, description, issued_at
FROM weather_alerts
WHERE country = 'France'
  AND alert_date = '2025-01-01';
```

La clé composite `(country, alert_date)` concentre toutes les alertes du jour dans une seule partition. Le tri par `severity DESC` est automatique grâce au CLUSTERING ORDER défini à la création de la table.

---

### REQ-05 — Comparer la météo entre plusieurs villes

**Besoin :** afficher côte à côte les conditions météo des grandes villes françaises.

```cql
SELECT city, temperature, humidity, wind_speed, weather_condition, recorded_at
FROM weather_current
WHERE city IN ('Paris', 'Lyon', 'Marseille', 'Bordeaux', 'Toulouse',
               'Nantes', 'Strasbourg', 'Lille', 'Nice', 'Rennes');
```

La clause `IN` sur la partition key est acceptable dans Cassandra quand le nombre de valeurs est limité. Chaque ville est lue directement sur son nœud, sans scan global de la table.

---

## 4. Ce qu'on a évité

- Pas de `ALLOW FILTERING` : toutes les requêtes s'appuient sur des partition keys ou des clustering keys.
- Pas de jointures : les tables sont dénormalisées pour éviter ce besoin.
- Pas de partitions "chaudes" : la partition `(country, alert_date)` est bornée dans le temps — on n'accumule pas tout l'historique dans une seule partition.

---

## 5. Source des données

- **API :** Open-Meteo (https://open-meteo.com/) — gratuite, sans authentification
- **Script d'ingestion :** `script/get_weather_api.py`
- **Volume ingéré :** ~480 prévisions horaires + 9 snapshots météo courants + 2 alertes actives
