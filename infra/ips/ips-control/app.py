"""Service de contrôle de la liste de blocage IPS — LAB.

Expose en lecture/écriture le set nftables `blocked` (famille bridge) alimenté par
la sonde. Permet au dashboard de LISTER les IP blacklistées et à l'opérateur (bouton
sur la page QR) de DÉBLOQUER une IP.

  GET  /blocklist   -> {"ips": [{"ip": "...", "expires_s": 123}], "count": N}
  POST /unblock     -> corps {"ip": "x.x.x.x"} : retire l'IP du set
  GET  /health      -> {"status": "ok"}

Tourne en network_mode host + CAP_NET_ADMIN (comme la sonde) pour voir la même table.
Sécurité : toute IP est validée (ipaddress) avant d'être passée à nft — pas d'injection.
"""
import ipaddress
import json
import os
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(os.environ.get("CONTROL_PORT", "9102"))
NFT_TABLE = os.environ.get("NFT_TABLE", "bridge ips")      # famille + table
NFT_SET = os.environ.get("NFT_SET", "blocked")


def log(level, message, **kw):
    print(json.dumps({"service": "ips-control", "level": level, "message": message, **kw}),
          flush=True)


def valide_ip(valeur):
    """Renvoie l'IP normalisée si valide, sinon None (anti-injection nft)."""
    try:
        return str(ipaddress.ip_address((valeur or "").strip()))
    except ValueError:
        return None


def lister():
    """Lit le set nftables et renvoie la liste des IP bloquées (+ délai restant)."""
    res = subprocess.run(["nft", "-j", "list", "set", *NFT_TABLE.split(), NFT_SET],
                         capture_output=True, text=True, timeout=5)
    if res.returncode != 0:
        log("error", "échec list set", stderr=res.stderr.strip())
        return []
    data = json.loads(res.stdout)
    ips = []
    for bloc in data.get("nftables", []):
        elems = bloc.get("set", {}).get("elem", [])
        for e in elems:
            if isinstance(e, dict) and "elem" in e:        # élément avec timeout
                val = e["elem"].get("val")
                ips.append({"ip": val, "expires_s": e["elem"].get("expires")})
            else:                                           # élément simple
                ips.append({"ip": e, "expires_s": None})
    return ips


def debloquer(ip):
    res = subprocess.run(["nft", "delete", "element", *NFT_TABLE.split(), NFT_SET, f"{{ {ip} }}"],
                         capture_output=True, text=True, timeout=5)
    ok = res.returncode == 0
    log("warning" if ok else "error", "déblocage IP" if ok else "échec déblocage",
        ip=ip, stderr=res.stderr.strip() or None)
    return ok, res.stderr.strip()


class H(BaseHTTPRequestHandler):
    def _j(self, obj, code=200):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/health":
            return self._j({"status": "ok"})
        if path == "/blocklist":
            try:
                ips = lister()
                return self._j({"ips": ips, "count": len(ips)})
            except (subprocess.SubprocessError, json.JSONDecodeError, OSError) as e:
                return self._j({"error": str(e), "ips": [], "count": 0}, 500)
        return self._j({"error": "not found"}, 404)

    def do_POST(self):
        path = self.path.split("?")[0]
        if path != "/unblock":
            return self._j({"error": "not found"}, 404)
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        except (ValueError, TypeError):
            return self._j({"error": "corps JSON invalide"}, 400)
        ip = valide_ip(body.get("ip"))
        if not ip:
            return self._j({"error": "ip invalide"}, 400)
        try:
            ok, detail = debloquer(ip)
            return self._j({"ok": ok, "ip": ip, "detail": detail}, 200 if ok else 500)
        except (subprocess.SubprocessError, OSError) as e:
            return self._j({"ok": False, "ip": ip, "detail": str(e)}, 500)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    log("info", "démarrage", port=PORT, table=NFT_TABLE, set=NFT_SET)
    ThreadingHTTPServer(("0.0.0.0", PORT), H).serve_forever()
