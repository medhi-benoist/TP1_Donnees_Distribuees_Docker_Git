-- ========================================================
-- 02_crud.sql
-- Démonstration des opérations fondamentales CRUD avec CQL
-- Keyspace : weather
-- ========================================================

USE weather;

-- --------------------------------------------------------
-- C - CREATE (Insertion d'une nouvelle station météo : Rennes)
-- --------------------------------------------------------
INSERT INTO weather_current (
    city,
    country,
    latitude,
    longitude,
    recorded_at,
    temperature,
    humidity,
    wind_speed,
    weather_code,
    weather_condition
) VALUES (
    'Rennes',
    'France',
    48.1173,
    -1.6778,
    toTimestamp(now()),
    18.5,
    62.0,
    14.2,
    2,
    'Partiellement nuageux'
);

-- --------------------------------------------------------
-- R - READ (Consultation de la donnée nouvellement insérée)
-- Utilise la clé de partition : city = 'Rennes'
-- --------------------------------------------------------
SELECT * FROM weather_current WHERE city = 'Rennes';

-- --------------------------------------------------------
-- U - UPDATE (Mise à jour de la température et condition météo)
-- Exemple : augmentation de la température et passage en ensoleillé
-- --------------------------------------------------------
UPDATE weather_current
SET temperature = 21.0,
    weather_condition = 'Ensoleillé et dégagé'
WHERE city = 'Rennes';

-- Vérification après modification
SELECT city, temperature, weather_condition FROM weather_current WHERE city = 'Rennes';

-- --------------------------------------------------------
-- D - DELETE (Suppression de la station météo de test)
-- --------------------------------------------------------
DELETE FROM weather_current WHERE city = 'Rennes';

-- Vérification après suppression (doit renvoyer 0 ligne)
SELECT * FROM weather_current WHERE city = 'Rennes';
