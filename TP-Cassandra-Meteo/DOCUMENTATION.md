# Documentation — TP Apache Cassandra & Vélib'

**Module :** Données distribuées — M2 Big Data & IA  
**Technologies :** Docker · Apache Cassandra 4.1 · CQL · Python (`requests`, `cassandra-driver`) · OpenData Paris (API Vélib')

---

## 1. Architecture & Démarrage

### Configuration Docker (`docker-compose.yml`)
Le conteneur Cassandra est déployé avec les paramètres suivants :
- **Image :** `cassandra:4.1`
- **Nom du conteneur / Hostname :** `cassandra`
- **Port exposé :** `9042` (port standard pour les clients CQL natifs)
- **Cluster Name :** `tp-cassandra`
- **Datacenter & Rack :** `dc1` / `rack1`
- **Snitch :** `GossipingPropertyFileSnitch`
- **Mémoire Heap :** `MAX_HEAP_SIZE=512M`, `HEAP_NEWSIZE=128M`
- **Persistance :** Volume Docker nommé `cassandra_data` monté sur `/var/lib/cassandra`.

### Statut du nœud (`nodetool status`)
Le nœud est opérationnel sous l'état **UN** (*Up / Normal*) :
```text
Datacenter: dc1
===============
Status=Up/Down
|/ State=Normal/Leaving/Joining/Moving
--  Address     Load        Tokens  Owns (effective)  Host ID                               Rack 
UN  172.20.0.2  104.34 KiB  16      100.0%            2120b326-b07e-467e-8d7e-984ae8f2bfea  rack1
```

---

## 2. Modèle de Données & Schéma CQL (`schema.cql`)

### Keyspace `velib`
Le keyspace est l'équivalent d'une base de données logique :
```sql
CREATE KEYSPACE IF NOT EXISTS velib
WITH replication = {
    'class': 'SimpleStrategy',
    'replication_factor': 1
};
```
- `SimpleStrategy` : Stratégie de placement adaptée aux déploiements mono-datacenter.
- `replication_factor: 1` : Un seul exemplaire des données sur le cluster (suffisant pour le TP mono-nœud).

### Table `stations`
```sql
USE velib;

CREATE TABLE IF NOT EXISTS stations (
    station_id text PRIMARY KEY,
    name text,
    capacity int,
    latitude double,
    longitude double,
    opening_hours text
);
```

### Rôle de la Clé Primaire
- `PRIMARY KEY (station_id)` :
  - `station_id` sert de **Partition Key**.
  - Cassandra utilise une fonction de hachage (par défaut `Murmur3Partitioner`) sur cette clé pour déterminer sur quel nœud ou token stocker la partition.
  - Dans cette première table, il n'y a pas de clustering key : chaque partition contient exactement une ligne.

---

## 3. Manipulation CQL (CRUD validé)

| Opération | Exemple de requête CQL |
|---|---|
| **Create (INSERT)** | `INSERT INTO stations (station_id, name, capacity, latitude, longitude, opening_hours) VALUES ('10115', 'Granges aux Belles', 27, 48.87614, 2.36808, null);` |
| **Read (SELECT)** | `SELECT * FROM stations WHERE station_id = '10115';` |
| **Update (UPDATE)** | `UPDATE stations SET capacity = 30 WHERE station_id = '10115';` |
| **Delete (DELETE)** | `DELETE FROM stations WHERE station_id = '10115';` |

---

## 4. Ingestion Automatique via Python (`script/getapi.py`)

### Environnement virtuel (`.venv`) et dépendances
Un environnement virtuel Python a été initialisé dans le projet avec [requirements.txt](file:///c:/Users/medhi/Documents/SupDeVinci_Cours/Donnees_Distribuees/TP1_Donnees_Distribuees_Docker_Git/TP-Cassandra-Velib/requirements.txt) :
- `requests>=2.31.0` (pour interroger l'API REST OpenData Paris)
- `cassandra-driver>=3.29.0` (pilote officiel DataStax Python)

**Commandes pour activer l'environnement :**
- Sous **Git Bash** :
  ```bash
  source .venv/Scripts/activate
  ```
- Sous **PowerShell** :
  ```powershell
  .\.venv\Scripts\Activate.ps1
  ```

### Fonctionnement du script
1. **Appel API :** Récupération de 20 stations en JSON depuis :
   `https://opendata.paris.fr/api/explore/v2.1/catalog/datasets/velib-emplacement-des-stations/records?limit=20`
2. **Connexion Cassandra :** Connexion au cluster sur `127.0.0.1:9042` avec sélection du keyspace `velib`.
3. **Prepared Statement :** Préparation de la requête `INSERT` pour optimiser les performances réseau et l'exécution côté Cassandra.
4. **Insertion en boucle :** Correspondance automatique des champs (`stationcode` -> `station_id`, `coordonnees_geo.lat` -> `latitude`, etc.).

### Résultat de l'importation
- **20 stations réelles** insérées avec succès dans `velib.stations`.
- Vérifiable avec :
  ```bash
  docker exec -it cassandra cqlsh -e "SELECT COUNT(*) FROM velib.stations;"
  docker exec -it cassandra cqlsh -e "SELECT * FROM velib.stations LIMIT 5;"
  ```

---

## 5. Notions Fondamentales du Cours à Retenir

1. **Query-Driven Design :**
   Dans Cassandra, on ne normalise pas comme en SQL relationnel. Le schéma de la table découle directement des besoins de lecture applicatifs (`WHERE station_id = ?`).
2. **Avertissement Full Scan :**
   Exécuter `SELECT COUNT(*)` sans partition key provoque un warning Cassandra :
   `Aggregation query used without partition key`. Sur un vrai cluster distribué à grande échelle, cela force à interroger tous les nœuds de l'anneau (très coûteux).
3. **Persistance Docker :**
   Les données résident dans le volume Docker `tp-cassandra-velib_cassandra_data` et ne sont pas supprimées lors d'un `docker compose down` classique.

---

## 6. Commandes Utiles

- **Lancer le client interactif CQLSH :**
  ```bash
  docker exec -it cassandra cqlsh
  ```
- **Vérifier l'état de l'anneau :**
  ```bash
  docker exec cassandra nodetool status
  ```
- **Relancer l'ingestion Python :**
  ```bash
  python script/getapi.py
  ```
- **Arrêter le conteneur en conservant les données :**
  ```bash
  docker compose down
  ```
