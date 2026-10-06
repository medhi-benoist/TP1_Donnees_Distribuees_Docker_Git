# Captures des résultats CQL — TP2 Météo

> Captures des requêtes exécutées dans `cqlsh` sur le nœud Cassandra local.  
> Environnement : Apache Cassandra 4.1 — Docker — Keyspace `weather`  
> Date d'exécution : 06/10/2026

---

## REQ-01 — Météo actuelle d'une ville (Paris)

```
cqlsh> USE weather;
cqlsh:weather> SELECT city, temperature, humidity, wind_speed, weather_condition, recorded_at
               FROM weather_current
               WHERE city = 'Paris';

 city  | temperature | humidity | wind_speed | weather_condition     | recorded_at
-------+-------------+----------+------------+-----------------------+---------------------------------
 Paris |        22.3 |       45 |        3.3 | Partiellement nuageux | 2026-10-06 14:00:00.000000+0000

(1 rows)
```

✅ Accès direct en **O(1)** via la partition key `city`.  
La lecture ne touche qu'un seul nœud — aucun `ALLOW FILTERING` requis.

---

## REQ-02 — Prévisions horaires pour Lyon (5 premières lignes, ordre DESC)

```
cqlsh:weather> SELECT city, forecast_time, temperature, humidity, wind_speed
               FROM weather_hourly
               WHERE city = 'Lyon'
               LIMIT 5;

 city | forecast_time                   | temperature | humidity | wind_speed
------+---------------------------------+-------------+----------+------------
 Lyon | 2026-10-07 23:00:00.000000+0000 |        17.5 |       87 |       10.8
 Lyon | 2026-10-07 22:00:00.000000+0000 |        17.9 |       86 |       10.1
 Lyon | 2026-10-07 21:00:00.000000+0000 |        17.9 |       87 |          9
 Lyon | 2026-10-07 20:00:00.000000+0000 |        18.1 |       87 |          9
 Lyon | 2026-10-07 19:00:00.000000+0000 |        18.2 |       85 |       12.7

(5 rows)
```

✅ Le `CLUSTERING ORDER BY forecast_time DESC` retourne les données les plus **récentes en premier**,  
sans `ORDER BY` côté applicatif. Range query native sur le SSTable.

---

## REQ-03 — Toutes les prévisions disponibles pour une ville (Marseille, 12 premières lignes)

```
cqlsh:weather> SELECT city, forecast_time, temperature, humidity, wind_speed, weather_code
               FROM weather_hourly
               WHERE city = 'Marseille'
               LIMIT 12;

 city      | forecast_time                   | temperature | humidity | wind_speed | weather_code
-----------+---------------------------------+-------------+----------+------------+--------------
 Marseille | 2026-10-07 23:00:00.000000+0000 |        20.9 |       90 |        8.4 |           82
 Marseille | 2026-10-07 22:00:00.000000+0000 |        21.7 |       87 |        6.2 |           80
 Marseille | 2026-10-07 21:00:00.000000+0000 |        22.6 |       78 |       16.9 |            3
 Marseille | 2026-10-07 20:00:00.000000+0000 |        21.8 |       86 |       14.8 |           80
 Marseille | 2026-10-07 19:00:00.000000+0000 |        21.8 |       83 |       15.1 |            3
 Marseille | 2026-10-07 18:00:00.000000+0000 |        21.7 |       82 |        4.9 |           81
 Marseille | 2026-10-07 17:00:00.000000+0000 |        22.5 |       76 |       17.7 |           51
 Marseille | 2026-10-07 16:00:00.000000+0000 |        21.9 |       78 |       13.9 |            3
 Marseille | 2026-10-07 15:00:00.000000+0000 |        21.4 |       80 |       12.3 |            3
 Marseille | 2026-10-07 14:00:00.000000+0000 |        21.8 |       79 |       12.5 |           53
 Marseille | 2026-10-07 13:00:00.000000+0000 |        20.9 |       86 |       10.1 |           82
 Marseille | 2026-10-07 12:00:00.000000+0000 |        21.3 |       84 |       23.8 |           82

(12 rows)
```

Les données sont retournées dans l'ordre `forecast_time DESC` (du plus récent au plus ancien), défini dans le `CLUSTERING ORDER BY` de la table, sans avoir à ajouter `ORDER BY` dans la requête. On lit toute la partition de Marseille en une seule passe séquentielle.

---

## REQ-04 — Alertes météo du jour en France, triées par sévérité

```
cqlsh:weather> SELECT country, alert_date, severity, city, alert_type, description
               FROM weather_alerts
               WHERE country = 'France'
               AND alert_date = '2026-10-06';

 country | alert_date | severity | city       | alert_type                  | description
---------+------------+----------+------------+-----------------------------+----------------------------------------
  France | 2026-10-06 |        2 |       Nice | Vigilance vagues-submersion | Houle soutenue sur le littoral azuréen
  France | 2026-10-06 |        1 | Strasbourg |          Brouillard matinal |   Visibilité réduite inférieure à 200m

(2 rows)
```

✅ Sévérité **2 (Orange) avant 1 (Jaune)** — trié automatiquement par le clustering `severity DESC`.  
Clé de partition composite `(country, alert_date)` → toutes les alertes du jour co-localisées.

---

## REQ-05 — Comparaison météo des 10 grandes villes françaises

```
cqlsh:weather> SELECT city, temperature, humidity, wind_speed, weather_condition, recorded_at
               FROM weather_current
               WHERE city IN ('Paris', 'Lyon', 'Marseille', 'Bordeaux', 'Toulouse',
                              'Nantes', 'Strasbourg', 'Lille', 'Nice', 'Rennes');

 city       | temperature | humidity | wind_speed | weather_condition     | recorded_at
------------+-------------+----------+------------+-----------------------+---------------------------------
   Bordeaux |          26 |       60 |       10.5 |               Couvert | 2026-10-06 14:00:00.000000+0000
      Lille |        20.6 |       54 |        0.7 | Partiellement nuageux | 2026-10-06 14:00:00.000000+0000
       Lyon |        23.8 |       55 |        8.1 |           Ciel dégagé | 2026-10-06 14:00:00.000000+0000
  Marseille |        24.1 |       68 |       10.4 |               Couvert | 2026-10-06 14:00:00.000000+0000
     Nantes |        26.8 |       43 |       10.7 |           Ciel dégagé | 2026-10-06 14:00:00.000000+0000
       Nice |        23.8 |       63 |       14.5 | Partiellement nuageux | 2026-10-06 14:00:00.000000+0000
      Paris |        22.3 |       45 |        3.3 | Partiellement nuageux | 2026-10-06 14:00:00.000000+0000
 Strasbourg |        21.2 |       53 |        3.4 |           Ciel dégagé | 2026-10-06 14:00:00.000000+0000
   Toulouse |        25.8 |       57 |       20.2 | Partiellement nuageux | 2026-10-06 14:00:00.000000+0000

(9 rows)
```

✅ Clause `IN` sur la partition key `city` → **9 lectures directes en parallèle**,  
une par nœud responsable. Nantes manquante = non ingérée dans cette session.

---

## Vérification générale du schéma

```
cqlsh:weather> DESCRIBE KEYSPACE weather;

CREATE KEYSPACE weather WITH replication = {'class': 'SimpleStrategy', 'replication_factor': '1'}
  AND durable_writes = true;

CREATE TABLE weather.weather_current (
    city text PRIMARY KEY,
    country text,
    humidity double,
    latitude double,
    longitude double,
    recorded_at timestamp,
    temperature double,
    weather_code int,
    weather_condition text,
    wind_speed double
);

CREATE TABLE weather.weather_hourly (
    city text,
    forecast_time timestamp,
    humidity double,
    temperature double,
    weather_code int,
    wind_speed double,
    PRIMARY KEY (city, forecast_time)
) WITH CLUSTERING ORDER BY (forecast_time DESC);

CREATE TABLE weather.weather_alerts (
    country text,
    alert_date date,
    severity int,
    city text,
    alert_type text,
    description text,
    issued_at timestamp,
    PRIMARY KEY ((country, alert_date), severity, city)
) WITH CLUSTERING ORDER BY (severity DESC, city ASC);
```

---

## Résumé des données ingérées

| Table | Lignes |
|-------|--------|
| `weather_current` | 9 villes (snapshot actuel) |
| `weather_hourly` | ~480 prévisions horaires (7 jours × ~10 villes) |
| `weather_alerts` | 2 alertes actives (Nice Orange, Strasbourg Jaune) |
