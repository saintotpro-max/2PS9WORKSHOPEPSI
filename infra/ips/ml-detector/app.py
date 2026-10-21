"""ml-detector — service de prédiction de la sonde IPS.

Expose le modèle Random Forest fourni par l'équipe DEV/IA (UNSW-NB15, 3 classes :
Normal, DoS, Reconnaissance) selon le contrat de la demande ML :

  POST /predict   un flux  {"dur": ..., ..., "ct_dst_ltm": ...}  -> un objet
                  un lot   [{...}, {...}]                         -> une liste
  GET  /health    200 si le modèle est chargé

Réponse par flux :
  {"prediction": 1, "attack_type": "DoS", "dos_probability": 0.97,
   "probabilities": {"Normal": 0.02, "DoS": 0.97, "Reconnaissance": 0.01},
   "model_version": "experiment-e-rf-3classes"}

Le modèle est un pickle : son empreinte SHA-256 est vérifiée avant chargement.
"""
import hashlib
import json
import os
import sys
import time
import warnings
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import joblib
import numpy as np

MODEL_PATH = os.environ.get("MODEL_PATH", "/model/attack_detector_rf_3classes.joblib")
MODEL_SHA256 = os.environ.get("MODEL_SHA256", "")
PORT = int(os.environ.get("PORT", "8000"))
MAX_BATCH = int(os.environ.get("MAX_BATCH", "5000"))

# Le modèle a été entraîné sur un DataFrame nommé ; on lui passe un tableau dans le
# même ordre de colonnes (vérifié au démarrage), l'avertissement est donc sans objet.
warnings.filterwarnings("ignore", message="X does not have valid feature names")


def log(level, message, **kw):
    print(json.dumps({"timestamp": time.time(), "level": level, "service": "ml-detector",
                      "message": message, **kw}), flush=True)


def load():
    data = open(MODEL_PATH, "rb").read()
    digest = hashlib.sha256(data).hexdigest()
    if MODEL_SHA256 and digest != MODEL_SHA256:
        log("error", "empreinte du modèle invalide, refus de chargement",
            expected=MODEL_SHA256, actual=digest)
        sys.exit(1)
    bundle = joblib.load(MODEL_PATH)
    model = bundle["model"]
    model.n_jobs = 1   # enregistré avec -1 : un pool de threads par appel, inutile ici
    features = list(bundle["features"])
    if list(model.feature_names_in_) != features:
        log("error", "ordre des features incohérent dans le modèle")
        sys.exit(1)
    id_to_class = {v: k for k, v in bundle["class_to_id"].items()}
    classes = [id_to_class[int(c)] for c in model.classes_]
    log("info", "modèle chargé", version=bundle.get("version"), dataset=bundle.get("dataset"),
        classes=classes, features=features, sha256=digest)
    return model, features, classes, bundle.get("version", "inconnue")


MODEL, FEATURES, CLASSES, VERSION = load()
DOS_INDEX = CLASSES.index("DoS")


def predict(rows):
    X = np.array([[float(r[f]) for f in FEATURES] for r in rows], dtype=np.float64)
    proba = MODEL.predict_proba(X)
    out = []
    for p in proba:
        k = int(p.argmax())
        out.append({
            "prediction": int(MODEL.classes_[k]),
            "attack_type": CLASSES[k],
            "dos_probability": round(float(p[DOS_INDEX]), 4),
            "probabilities": {c: round(float(v), 4) for c, v in zip(CLASSES, p)},
            "model_version": VERSION,
        })
    return out


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body):
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/health":
            return self._send(200, {"status": "ok", "model_version": VERSION, "classes": CLASSES})
        self._send(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/predict":
            return self._send(404, {"error": "not found"})
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
            single = isinstance(body, dict)
            rows = [body] if single else body
            if not isinstance(rows, list) or not 0 < len(rows) <= MAX_BATCH:
                raise ValueError(f"un objet ou une liste de 1 à {MAX_BATCH} flux attendu")
            result = predict(rows)
        except KeyError as e:
            return self._send(422, {"error": f"feature manquante : {e.args[0]}", "expected": FEATURES})
        except (ValueError, TypeError) as e:
            return self._send(400, {"error": str(e)})
        self._send(200, result[0] if single else result)

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    log("info", "écoute", port=PORT)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
