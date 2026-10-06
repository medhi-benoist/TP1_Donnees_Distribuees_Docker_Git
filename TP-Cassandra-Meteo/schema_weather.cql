-- =======================================================
-- TP2 : Exploitation des données Météo avec Apache Cassandra
-- Keyspace : weather
-- =======================================================

CREATE KEYSPACE IF NOT EXISTS weather
WITH replication = {
    'class': 'SimpleStrategy',
    'replication_factor': 1
};

USE weather;

-- -------------------------------------------------------
-- Table 1 : weather_current (Météo instantanée par ville)
-- Clé de partition : city
-- Permet de récupérer en O(1) les conditions actuelles d'une ville.
-- -------------------------------------------------------
CREATE TABLE IF NOT EXISTS weather_current (
    city text,
    country text,
    latitude double,
    longitude double,
    recorded_at timestamp,
    temperature double,
    humidity double,
    wind_speed double,
    weather_code int,
    weather_condition text,
    PRIMARY KEY (city)
);

-- -------------------------------------------------------
-- Table 2 : weather_hourly (Prévisions et séries temporelles)
-- Clé de partition : city
-- Clé de clustering : forecast_time (ordre décroissant)
-- Permet des requêtes de plages horaires (range queries) sans ALLOW FILTERING.
-- -------------------------------------------------------
CREATE TABLE IF NOT EXISTS weather_hourly (
    city text,
    forecast_time timestamp,
    temperature double,
    humidity double,
    wind_speed double,
    weather_code int,
    PRIMARY KEY ((city), forecast_time)
) WITH CLUSTERING ORDER BY (forecast_time DESC);

-- -------------------------------------------------------
-- Table 3 : weather_alerts (Alertes et conditions extrêmes par pays et date)
-- Clé de partition : (country, alert_date)
-- Clé de clustering : severity (DESC), city
-- Permet de lister les alertes d'un pays pour un jour donné par sévérité.
-- -------------------------------------------------------
CREATE TABLE IF NOT EXISTS weather_alerts (
    country text,
    alert_date date,
    severity int, -- 1: Jaune, 2: Orange, 3: Rouge
    city text,
    alert_type text,
    description text,
    issued_at timestamp,
    PRIMARY KEY ((country, alert_date), severity, city)
) WITH CLUSTERING ORDER BY (severity DESC, city ASC);
