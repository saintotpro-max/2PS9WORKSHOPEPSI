#!/usr/bin/env python3
"""Mock du WAF pour le MIROIR local du lab : HTTPS, certificat autosigne, routage.

Reproduit l'unique point d'entree de l'infra reelle :
  /, /health, /auth/token, /transactions, /metrics  -> plateforme de paiement
  /dashboard/api/remediation/*                      -> vrai moteur de remediation
  /dashboard/api/prom/query                         -> sonde Prometheus (miroir)
  /dashboard/api/escalade                           -> 501 (relais INFRA, bonus)

Le certificat autosigne est voulu : c'est lui qui fait passer le jeu par le
chemin TLS ignore (pont.rpy _CTX_TLS), comme devant le vrai WAF du lab.
Stdlib uniquement.
"""
import os
import ssl
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(os.environ.get("PORT", "8783"))
CERT = os.environ.get("CERT", "/tmp/miroir-cert.pem")
CLE = os.environ.get("KEY", "/tmp/miroir-cle.pem")
PLATEFORME = os.environ.get("UPSTREAM_PLATEFORME", "http://127.0.0.1:8780")
REMEDIATION = os.environ.get("UPSTREAM_REMEDIATION", "http://127.0.0.1:8781")
PROM = os.environ.get("UPSTREAM_PROM", "http://127.0.0.1:8782")


def transferer(upstream, chemin, methode, corps, en_tetes):
    req = urllib.request.Request(upstream + chemin, data=corps, method=methode,
                                 headers={k: v for k, v in en_tetes.items()
                                          if k.lower() in ("content-type", "authorization", "accept")})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:
        return 502, ('{"detail":"miroir : amont injoignable (%s)"}' % e).encode()


class Handler(BaseHTTPRequestHandler):
    def _route(self):
        longueur = int(self.headers.get("Content-Length") or 0)
        corps = self.rfile.read(longueur) if longueur else None
        if self.path.startswith("/dashboard/api/remediation/"):
            code, brut = transferer(REMEDIATION, self.path[len("/dashboard/api/remediation"):],
                                    self.command, corps, self.headers)
        elif self.path.startswith("/dashboard/api/prom/query"):
            code, brut = transferer(PROM, "/api/v1/query" + "?" + self.path.split("?", 1)[-1]
                                    if "?" in self.path else "/api/v1/query",
                                    self.command, corps, self.headers)
        elif self.path.startswith("/dashboard/api/escalade"):
            code, brut = 501, b'{"detail":"relais escalade : a fournir par INFRA (bonus)"}'
        else:
            code, brut = transferer(PLATEFORME, self.path, self.command, corps, self.headers)
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(brut)))
        self.end_headers()
        self.wfile.write(brut)

    do_GET = do_POST = do_PUT = do_DELETE = _route

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(CERT, CLE)
    serveur = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    serveur.socket = ctx.wrap_socket(serveur.socket, server_side=True)
    print("waf mock miroir (https) sur %d -> %s | %s | %s" % (PORT, PLATEFORME, REMEDIATION, PROM), flush=True)
    serveur.serve_forever()
