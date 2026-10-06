-- Script de création du schéma pour le TP Cassandra Vélib'

-- Étape 7 : Création du Keyspace
CREATE KEYSPACE IF NOT EXISTS velib
WITH replication = {
    'class': 'SimpleStrategy',
    'replication_factor': 1
};

-- Utilisation du Keyspace
USE velib;

-- Étape 9 : Création de la table stations
CREATE TABLE IF NOT EXISTS stations (
    station_id text PRIMARY KEY,
    name text,
    capacity int,
    latitude double,
    longitude double,
    opening_hours text
);
