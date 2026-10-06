-- =======================================================
-- TP2 : Requêtes métier — Données Météo (Open-Meteo API)
-- Keyspace : weather
-- =======================================================
-- Ces requêtes correspondent aux 5 besoins métier identifiés
-- pour une application météo de type dashboard ou alerting.
-- Chaque requête est conçue pour fonctionner SANS ALLOW FILTERING
-- grâce au modèle de données orienté-requêtes de Cassandra.
-- =======================================================

USE weather;

-- -------------------------------------------------------
-- REQ-01 : Conditions météo actuelles d'une ville donnée
-- -------------------------------------------------------
-- Besoin métier :
--   Un utilisateur consulte la météo actuelle d'une ville
--   précise (ex. depuis une application mobile ou un dashboard).
--
-- Clé de partition utilisée : city
--   → Accès direct en O(1) pour n'importe quelle ville.
--
-- Justification :
--   La table weather_current est conçue exactement pour ce
--   besoin : 1 ligne par ville, lecture instantanée.
-- -------------------------------------------------------

SELECT city, country, temperature, humidity, wind_speed,
       weather_condition, recorded_at
FROM weather_current
WHERE city = 'Paris';


-- -------------------------------------------------------
-- REQ-02 : Historique horaire des dernières 24h pour une ville
-- -------------------------------------------------------
-- Besoin métier :
--   Afficher un graphique d'évolution de la température
--   sur les dernières 24h pour une ville donnée.
--
-- Clé de partition utilisée : city
-- Clé de clustering        : forecast_time DESC
--   → Les données sont déjà triées du plus récent au plus
--     ancien dans le SSTable ; range query native Cassandra.
--
-- Justification :
--   La table weather_hourly est modélisée précisément pour
--   les séries temporelles par ville. Le CLUSTERING ORDER BY
--   DESC évite tout tri côté applicatif.
-- -------------------------------------------------------

SELECT city, forecast_time, temperature, humidity, wind_speed
FROM weather_hourly
WHERE city = 'Lyon'
  AND forecast_time >= '2025-01-01 00:00:00'
  AND forecast_time <= '2025-01-02 00:00:00';


-- -------------------------------------------------------
-- REQ-03 : Toutes les prévisions horaires d'une ville (ordre chronologique)
-- -------------------------------------------------------
-- Besoin métier :
--   Récupérer l'ensemble des prévisions disponibles pour
--   une ville afin d'alimenter un graphe multi-jours.
--
-- Clé de partition utilisée : city
-- Clé de clustering        : forecast_time (ordre inversé appliqué)
--
-- Justification :
--   On récupère toute la partition d'une ville en un seul
--   scan séquentiel sur le SSTable, sans filtrage secondaire.
-- -------------------------------------------------------

SELECT city, forecast_time, temperature, humidity, wind_speed, weather_code
FROM weather_hourly
WHERE city = 'Marseille';


-- -------------------------------------------------------
-- REQ-04 : Alertes météo pour un pays à une date donnée, triées par sévérité
-- -------------------------------------------------------
-- Besoin métier :
--   Un opérateur de sécurité civile doit voir en priorité
--   les alertes les plus graves pour la France ce jour.
--
-- Clé de partition utilisée : (country, alert_date) — composite
--   → La combinaison pays + date concentre toutes les alertes
--     du jour dans une même partition, évitant les scatter reads.
-- Clé de clustering        : severity DESC, city ASC
--   → Les alertes rouges (severity=3) remontent en premier
--     automatiquement grâce au CLUSTERING ORDER.
--
-- Justification :
--   Le modèle garantit que la requête la plus critique
--   (alertes graves du jour par pays) est optimale sans index.
-- -------------------------------------------------------

SELECT country, alert_date, severity, city, alert_type, description, issued_at
FROM weather_alerts
WHERE country = 'France'
  AND alert_date = '2025-01-01';


-- -------------------------------------------------------
-- REQ-05 : Comparaison de températures entre plusieurs villes à un instant donné
-- -------------------------------------------------------
-- Besoin métier :
--   Comparer la météo actuelle de plusieurs grandes villes
--   pour un widget "Top villes" dans un dashboard.
--
-- Clé de partition utilisée : city
--   → Chaque ville est lue indépendamment (IN clause).
--     Cassandra distribue les lectures en parallèle sur les nœuds.
--
-- Justification :
--   La clause IN avec la partition key city est la seule
--   utilisation efficace de IN dans Cassandra (accès direct
--   à chaque partition sans scatter-gather non contrôlé).
-- -------------------------------------------------------

SELECT city, temperature, humidity, wind_speed, weather_condition, recorded_at
FROM weather_current
WHERE city IN ('Paris', 'Lyon', 'Marseille', 'Bordeaux', 'Toulouse',
               'Nantes', 'Strasbourg', 'Lille', 'Nice', 'Rennes');
