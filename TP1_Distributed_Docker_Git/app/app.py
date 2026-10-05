import json
import os
import time
import urllib.error
import urllib.request
from flask import Flask, jsonify, request

app = Flask(__name__)

NODE_NAME = os.getenv("NODE_NAME", "node")
ROLE = os.getenv("ROLE", "follower")
PORT = int(os.getenv("PORT", "8080"))

LEADER_URL = os.getenv("LEADER_URL", "").strip()
FOLLOWERS_ENV = os.getenv("FOLLOWERS", "").strip()
FOLLOWERS = [f.strip() for f in FOLLOWERS_ENV.split(",") if f.strip()]

# Demo data stored in memory for the TP.
DATA = []


def replicate_to_follower(follower_url, item):
    target = f"{follower_url.rstrip('/')}/data"
    data_bytes = json.dumps(item).encode("utf-8")
    req = urllib.request.Request(
        target,
        data=data_bytes,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=2) as response:
            if 200 <= response.status < 300:
                return "success"
            return f"failed (status {response.status})"
    except urllib.error.HTTPError as e:
        return f"failed (HTTP {e.code})"
    except urllib.error.URLError as e:
        return f"failed (unreachable: {e.reason})"
    except Exception as e:
        return f"failed ({type(e).__name__}: {e})"


def sync_from_leader(leader_url, max_retries=5, retry_delay=2):
    if not leader_url:
        return
    url = f"{leader_url.rstrip('/')}/data"
    print(f"[{NODE_NAME}] Synchronisation initiale avec le leader ({url})...", flush=True)

    for attempt in range(1, max_retries + 1):
        try:
            req = urllib.request.Request(
                url,
                headers={"Accept": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=2) as response:
                if response.status == 200:
                    payload = json.loads(response.read().decode("utf-8"))
                    leader_data = payload.get("data", [])
                    DATA.clear()
                    DATA.extend(leader_data)
                    print(f"[{NODE_NAME}] Synchronisation réussie : {len(DATA)} éléments récupérés.", flush=True)
                    return
                print(f"[{NODE_NAME}] Tentative {attempt}/{max_retries} : code HTTP {response.status}", flush=True)
        except Exception as e:
            print(f"[{NODE_NAME}] Tentative {attempt}/{max_retries} échouée ({e})", flush=True)

        if attempt < max_retries:
            time.sleep(retry_delay)

    print(f"[{NODE_NAME}] Impossible de synchroniser avec le leader après {max_retries} tentatives. Démarrage avec stockage local.", flush=True)


@app.get("/")
def home():
    return jsonify({
        "node": NODE_NAME,
        "role": ROLE,
        "message": "Distributed Data TP"
    })


@app.get("/health")
def health():
    return jsonify({"status": "UP", "node": NODE_NAME, "role": ROLE})


@app.get("/data")
def get_data():
    return jsonify({
        "node": NODE_NAME,
        "role": ROLE,
        "count": len(DATA),
        "data": DATA
    })


@app.post("/data")
def add_data():
    payload = request.get_json(silent=True) or {}
    if "key" not in payload or "value" not in payload:
        return jsonify({"error": "key and value are required"}), 400

    item = {"key": str(payload["key"]), "value": payload["value"]}
    DATA.append(item)

    response_payload = {
        "message": "data stored",
        "node": NODE_NAME,
        "role": ROLE,
        "item": item
    }

    # Seul le leader réplique vers les followers (pas de boucle sur les followers)
    if ROLE == "leader" and FOLLOWERS:
        replication_results = {}
        for follower in FOLLOWERS:
            replication_results[follower] = replicate_to_follower(follower, item)
        response_payload["replication"] = replication_results

    return jsonify(response_payload), 201


@app.delete("/data")
def clear_data():
    DATA.clear()
    return jsonify({"message": "data cleared", "node": NODE_NAME})


if __name__ == "__main__":
    if ROLE == "follower" and LEADER_URL:
        sync_from_leader(LEADER_URL)
    app.run(host="0.0.0.0", port=PORT)
