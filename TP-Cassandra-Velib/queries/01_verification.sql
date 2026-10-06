-- ========================================================
-- 01_verification.sql
-- Vérification de l'existence des tables et comptage des données
-- Keyspace : weather
-- ========================================================

USE weather;

-- 1. Lister les tables du keyspace
DESCRIBE TABLES;

-- 2. Compter le nombre de villes suivies (weather_current)
SELECT COUNT(*) AS total_cities FROM weather_current;

-- 3. Compter le nombre de prévisions horaires stockées (weather_hourly)
SELECT COUNT(*) AS total_hourly_forecasts FROM weather_hourly;

-- 4. Compter le nombre d'alertes météo enregistrées (weather_alerts)
SELECT COUNT(*) AS total_alerts FROM weather_alerts;

-- 5. Aperçu des données de weather_current
SELECT city, country, temperature, humidity, wind_speed, weather_condition 
FROM weather_current 
LIMIT 5;

-- 6. Aperçu des données de weather_hourly pour une ville
SELECT city, forecast_time, temperature, humidity, wind_speed 
FROM weather_hourly 
WHERE city = 'Paris' 
LIMIT 5;

-- 7. Aperçu des alertes météo
SELECT country, alert_date, severity, city, alert_type, description 
FROM weather_alerts;
