# TP — Installation et première prise en main d’Apache Cassandra avec Vélib’

**Module :** Données distribuées — M2 Big Data & IA  
**Travail :** Individuel  
**Technologies :** Docker · Docker Compose · Apache Cassandra 4.1 · CQL · Python · API Vélib’

---

## 1. Objectif

Cette première manipulation permet de découvrir Cassandra progressivement avant de travailler sur un véritable cluster distribué.

Vous allez :

1. installer Cassandra avec Docker ;
2. démarrer un premier nœud ;
3. vérifier Cassandra ;
4. utiliser `cqlsh` ;
5. créer un keyspace ;
6. créer une table ;
7. manipuler les données avec CQL ;
8. récupérer des données réelles depuis l’API Vélib’ ;
9. envoyer ces données dans Cassandra avec Python ;
10. observer le schéma obtenu.

> **Important :** pour cette première étape, nous travaillons volontairement avec **un seul nœud Cassandra**. Le cluster multi-nœuds, la réplication, le RF, les racks et la gestion des pannes seront étudiés ensuite.

---

# 2. Préparer le projet

Créer un dossier :

```bash
mkdir TP-Cassandra-Velib
cd TP-Cassandra-Velib
```

Créer le fichier :

```bash
nano docker-compose.yml
```

Copier-coller :

```yaml
services:

  cassandra:
    image: cassandra:4.1
    container_name: cassandra
    hostname: cassandra

    ports:
      - "9042:9042"

    environment:
      CASSANDRA_CLUSTER_NAME: tp-cassandra
      CASSANDRA_DC: dc1
      CASSANDRA_RACK: rack1
      CASSANDRA_ENDPOINT_SNITCH: GossipingPropertyFileSnitch
      CASSANDRA_NUM_TOKENS: 16

      MAX_HEAP_SIZE: 512M
      HEAP_NEWSIZE: 128M

    volumes:
      - cassandra_data:/var/lib/cassandra

volumes:
  cassandra_data:
```

Enregistrer puis quitter :

```text
CTRL + O
Entrée
CTRL + X
```

---

# 3. Installer et démarrer Cassandra

Lancer :

```bash
docker compose up -d
```

Vérifier :

```bash
docker ps
```

Vous devez voir le conteneur `cassandra` avec :

```text
0.0.0.0:9042->9042/tcp
```

Vérifier les logs :

```bash
docker logs cassandra --tail 30
```

Cassandra peut prendre quelques instants avant d’être complètement disponible.

---

# 4. Vérifier le nœud Cassandra

Exécuter :

```bash
docker exec cassandra nodetool status
```

Vous devez obtenir quelque chose ressemblant à :

```text
Datacenter: dc1
===============

Status=Up/Down
|/ State=Normal/Leaving/Joining/Moving

--  Address      Load       Tokens  Owns
UN  172.x.x.x    ...        16      ...
```

À retenir :

- `U` = **Up** : nœud actif ;
- `N` = **Normal** : état normal ;
- `UN` = nœud actif et opérationnel ;
- `dc1` = datacenter logique ;
- `rack1` = rack logique ;
- `16` = nombre de tokens configurés.

---

# 5. Entrer dans Cassandra avec cqlsh

Exécuter :

```bash
docker exec -it cassandra cqlsh
```

Vous devez obtenir :

```text
Connected to tp-cassandra at 127.0.0.1:9042
cqlsh>
```

Vous êtes maintenant dans **CQLSH**, le client permettant d’envoyer des requêtes CQL à Cassandra.

---

# 6. Observer les keyspaces existants

```sql
DESCRIBE KEYSPACES;
```

Vous verrez plusieurs keyspaces système :

```text
system
system_auth
system_schema
system_traces
...
```

Ils sont utilisés par Cassandra.

---

# 7. Créer le keyspace Vélib’

Exécuter :

```sql
CREATE KEYSPACE velib
WITH replication = {
    'class': 'SimpleStrategy',
    'replication_factor': 1
};
```

Puis :

```sql
DESCRIBE KEYSPACES;
```

Vous devez maintenant voir :

```text
velib
```

Sélectionner le keyspace :

```sql
USE velib;
```

Le prompt devient :

```text
cqlsh:velib>
```

---

# 8. Comprendre KEYSPACE et TABLE

On peut représenter simplement :

```text
Keyspace
   │
   ├── Table
   ├── Table
   └── Table
```

Pour ce TP :

```text
Keyspace Cassandra ≈ espace de données
Table Cassandra   ≈ table de données
```

Le keyspace `velib` contiendra nos tables.

---

# 9. Créer une première table Vélib’

Nous allons utiliser les champs réellement présents dans le jeu de données Vélib’ :

- `stationcode`
- `name`
- `capacity`
- `coordonnees_geo.lat`
- `coordonnees_geo.lon`
- `station_opening_hours`

Créer la table :

```sql
CREATE TABLE stations (
    station_id text PRIMARY KEY,
    name text,
    capacity int,
    latitude double,
    longitude double,
    opening_hours text
);
```

Vérifier :

```sql
DESCRIBE TABLES;
```

Puis :

```sql
DESCRIBE TABLE stations;
```

---

# 10. Comprendre le schéma

Le schéma de notre table est :

```text
stations
│
├── station_id      text       PRIMARY KEY
├── name            text
├── capacity        int
├── latitude        double
├── longitude       double
└── opening_hours   text
```

La clé primaire est :

```sql
PRIMARY KEY (station_id)
```

Dans cette table simple :

```text
station_id = Partition Key
```

Il n’y a pas encore de clustering key.

---

# 11. Insérer manuellement une station

Avant Python, faisons une insertion manuelle.

```sql
INSERT INTO stations (
    station_id,
    name,
    capacity,
    latitude,
    longitude,
    opening_hours
)
VALUES (
    '10115',
    'Granges aux Belles',
    27,
    48.8761373390584,
    2.3680844979417,
    null
);
```

Vérifier :

```sql
SELECT * FROM stations;
```

---

# 12. Modifier et supprimer une donnée

Modifier la capacité :

```sql
UPDATE stations
SET capacity = 30
WHERE station_id = '10115';
```

Vérifier :

```sql
SELECT * FROM stations
WHERE station_id = '10115';
```

Supprimer la station :

```sql
DELETE FROM stations
WHERE station_id = '10115';
```

Puis :

```sql
SELECT * FROM stations;
```

---

# 13. Comprendre le CRUD

Vous venez de manipuler les quatre opérations fondamentales :

| Opération | CQL |
|---|---|
| Create | `INSERT` |
| Read | `SELECT` |
| Update | `UPDATE` |
| Delete | `DELETE` |

---

# 14. Tester l’API Vélib’

Sortir de `cqlsh` :

```sql
exit;
```

Tester l’API :

```bash
curl "https://opendata.paris.fr/api/explore/v2.1/catalog/datasets/velib-emplacement-des-stations/records?limit=1"
```

La réponse contient notamment :

```json
{
  "results": [
    {
      "stationcode": "10115",
      "name": "Granges aux Belles",
      "capacity": 27,
      "coordonnees_geo": {
        "lon": 2.3680844979417,
        "lat": 48.8761373390584
      },
      "station_opening_hours": null
    }
  ]
}
```

Correspondance API → Cassandra :

| API Vélib’ | Cassandra |
|---|---|
| `stationcode` | `station_id` |
| `name` | `name` |
| `capacity` | `capacity` |
| `coordonnees_geo.lat` | `latitude` |
| `coordonnees_geo.lon` | `longitude` |
| `station_opening_hours` | `opening_hours` |

---

# 15. Installer les bibliothèques Python

Installer :

```bash
pip3 install requests cassandra-driver
```

Vérifier :

```bash
python3 --version
```

Créer le dossier :

```bash
mkdir -p script
```

Créer le script :

```bash
nano script/getapi.py
```

---

# 16. Script Python complet — API Vélib’ → Cassandra

Crer le  script** :

```python
import requests
from cassandra.cluster import Cluster


# 17. Exécuter le script

Lancer :

```bash
python3 script/getapi.py
```

Vous devez obtenir :

```text
Récupération des données Vélib'...
20 stations récupérées.
Station importée : 10115 - Granges aux Belles
Station importée : 12128 - Pyramide - Ecole du Breuil
Station importée : ...
Import terminé.
```

Le flux réalisé est :

```text
API Vélib’
     │
     │ HTTP
     ▼
  Python
     │
     │ cassandra-driver
     ▼
 Cassandra
     │
     ▼
 velib.stations
```

---

# 18. Vérifier les données importées

Entrer dans Cassandra :

```bash
docker exec -it cassandra cqlsh
```

Puis :

```sql
USE velib;
```

Compter les stations :

```sql
SELECT COUNT(*) FROM stations;
```

Vous devez obtenir environ :

```text
 count
-------
    20
```

Afficher les données :

```sql
SELECT * FROM stations LIMIT 10;
```

---

# 19. Observer le schéma final

Exécuter :

```sql
DESCRIBE KEYSPACE velib;
```

Puis :

```sql
DESCRIBE TABLE stations;
```

Le modèle obtenu est :

```text
┌─────────────────────────────────────┐
│             stations                │
├─────────────────────────────────────┤
│ station_id       text   PK          │
│ name             text               │
│ capacity         int                │
│ latitude         double             │
│ longitude        double             │
│ opening_hours    text               │
└─────────────────────────────────────┘
```

---

# 20. Comprendre la clé de partition

Notre table contient :

```sql
PRIMARY KEY (station_id)
```

Donc :

```text
PRIMARY KEY
     │
     ▼
station_id
     │
     ▼
Partition Key
```

Par exemple :

```text
10115 → partition de la station 10115
12009 → partition de la station 12009
13041 → partition de la station 13041
```

C’est un point essentiel pour la suite du cours.

---

# 21. Comprendre le Query-Driven Design

Dans Cassandra, on ne conçoit pas uniquement les tables à partir des données.

On part des requêtes que l’application doit exécuter :

```text
Besoin métier
      ↓
Requête
      ↓
Données nécessaires
      ↓
Partition Key
      ↓
Clustering Key éventuelle
      ↓
Table Cassandra
```

Exemple :

> « Donner les informations de la station 10115. »

Requête :

```sql
SELECT *
FROM stations
WHERE station_id = '10115';
```

La requête utilise directement la partition key :

```text
station_id
```

---

# 22. Ce que vous devez retenir

À la fin de cette manipulation, vous devez comprendre :

- comment installer Cassandra avec Docker ;
- comment démarrer et vérifier un nœud ;
- le rôle de `cqlsh` ;
- le rôle du port `9042` ;
- ce qu’est un keyspace ;
- ce qu’est une table Cassandra ;
- ce qu’est un schéma ;
- ce qu’est une clé primaire ;
- ce qu’est une partition key ;
- comment utiliser `INSERT`, `SELECT`, `UPDATE` et `DELETE` ;
- comment récupérer des données depuis une API ;
- comment connecter Python à Cassandra ;
- comment importer les données Vélib’ ;
- pourquoi le modèle Cassandra doit être pensé à partir des requêtes.

---

# 23. Préparation à la suite

Cette première manipulation utilise :

```text
1 nœud
1 datacenter
1 rack
RF = 1
```

La prochaine étape permettra de construire :

```text
                 Cluster Cassandra
                        │
             ┌──────────┼──────────┐
             ▼          ▼          ▼
           Node 1     Node 2     Node 3
           rack1      rack2      rack3
             │          │          │
             └──────────┼──────────┘
                        │
                  Partitioning
                        │
                    Réplication
                        │
                Replication Factor
                        │
                 Consistency Level
                        │
                  Tolérance panne
```

> **Cette première partie constitue donc la base avant d’aborder le véritable cluster Cassandra distribué.**

---

# 24. Nettoyage

Arrêter Cassandra :

```bash
docker compose down
```

Les données sont conservées dans le volume Docker :

```text
cassandra_data
```

Pour supprimer complètement le conteneur **et les données du TP** :

```bash
docker compose down -v
```

> **Attention : `-v` supprime le volume et donc les données Cassandra.**
