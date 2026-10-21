"""Service de participation RESILIENCE-ALPHA — le COMPTEUR de la vague.

Rôle : afficher aux spectateurs une page « bouton » (QR code) et compter les clics.
Les téléphones ne touchent JAMAIS la plateforme : ils ne font qu'incrémenter ce
compteur. La charge, elle, est générée séparément depuis ra-attacker (vague bornée,
périmètre verrouillé sur la plateforme du lab).

Phases : repos -> (armer) décompte -> en_cours (durée bornée) -> termine -> repos.
Stdlib uniquement (aucune dépendance à installer).
"""
import json
import os
import re
import ssl
import subprocess
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

PORT = int(os.environ.get("PORT", "8088"))
DECOMPTE_S = int(os.environ.get("DECOMPTE_S", "5"))      # compte à rebours avant la vague
DUREE_S = int(os.environ.get("DUREE_S", "25"))           # durée de la vague
TITRE = os.environ.get("TITRE", "RESILIENCE-ALPHA")
# Journal de cloudflared : on en extrait l'URL publique courante pour le QR.
CLOUDFLARED_LOG = os.environ.get("CLOUDFLARED_LOG", "/opt/attack/cloudflared.log")
PUBLIC_URL = os.environ.get("PUBLIC_URL", "")           # force une URL fixe si définie
TUNNEL_SERVICE = os.environ.get("TUNNEL_SERVICE", "cloudflared")
# Contrôle IPS via le WAF (appel sortant, TLS autosigné du lab) : liste et déblocage
# des IP blacklistées, pour la blacklist et les boutons de la page QR.
PLATEFORME_URL = os.environ.get("ALPHA_PLATEFORME_URL", "").rstrip("/")
_SSL = ssl._create_unverified_context()


def _ipsctl(chemin, data=None):
    """GET (data=None) ou POST JSON vers le contrôle IPS exposé par le WAF."""
    corps = json.dumps(data).encode() if data is not None else None
    entetes = {"Content-Type": "application/json"} if data is not None else {}
    req = urllib.request.Request(PLATEFORME_URL + chemin, data=corps,
                                 method="POST" if data is not None else "GET", headers=entetes)
    with urllib.request.urlopen(req, timeout=6, context=_SSL) as r:
        return json.loads(r.read().decode() or "{}")


def tunnel_actif():
    try:
        r = subprocess.run(["systemctl", "is-active", TUNNEL_SERVICE],
                           capture_output=True, text=True, timeout=5)
        return r.stdout.strip() == "active"
    except (OSError, subprocess.SubprocessError):
        return False


def tunnel_action(verbe):
    """start / stop du tunnel (action déclenchée par l'opérateur via le bouton)."""
    try:
        r = subprocess.run(["sudo", "-n", "systemctl", verbe, TUNNEL_SERVICE],
                           capture_output=True, text=True, timeout=15)
        return r.returncode == 0, (r.stderr or r.stdout).strip()
    except (OSError, subprocess.SubprocessError) as e:
        return False, str(e)


def url_publique():
    """URL publique courante : PUBLIC_URL si fixée, sinon dernière vue dans le log."""
    if PUBLIC_URL:
        return PUBLIC_URL
    try:
        texte = open(CLOUDFLARED_LOG, encoding="utf-8", errors="replace").read()
    except OSError:
        return None
    vus = re.findall(r"https://[a-z0-9-]+\.trycloudflare\.com", texte)
    return vus[-1] if vus else None


def qr_png(url):
    """PNG du QR via qrencode (installé sur ra-attacker), ou None."""
    try:
        return subprocess.run(["qrencode", "-o", "-", "-s", "10", "-m", "2", url],
                              capture_output=True, timeout=5, check=True).stdout
    except (OSError, subprocess.SubprocessError):
        return None

_lock = threading.Lock()
etat = dict(total=0, phase="repos", debut=None, fin=None, cible=None)


def snapshot():
    with _lock:
        e = dict(etat)
    now = time.time()
    # Après le compte à rebours, la vague reste EN COURS jusqu'à l'arrêt par l'opérateur
    # (bouton Arrêter). Pas de fin automatique : c'est l'opérateur qui décide.
    if e["phase"] == "decompte" and e["debut"] and now >= e["debut"]:
        e["phase"] = "en_cours"
    e["decompte"] = max(0, int(e["debut"] - now)) if e["debut"] and now < e["debut"] else 0
    e["ecoule"] = int(now - e["debut"]) if e["debut"] and e["phase"] == "en_cours" else 0
    return e


class H(BaseHTTPRequestHandler):
    def _j(self, obj, code=200):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def _html(self, body):
        b = body.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def _png(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "image/png")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/", "/participation"):
            return self._html(PAGE)
        if path == "/participation/etat":
            return self._j(snapshot())
        if path == "/qr":                               # page projetable (QR + URL)
            u = url_publique()
            return self._html(QR_PAGE.replace("__URL__", u) if u else QR_ATTENTE)
        if path == "/qrcode.png":                       # image du QR de l'URL publique
            u = url_publique()
            png = qr_png(u) if u else None
            return self._png(png) if png else self._j({"detail": "tunnel non prêt"}, 503)
        if path == "/tunnel/etat":
            return self._j({"actif": tunnel_actif(), "url": url_publique()})
        if path == "/participation/blocklist":          # IP blacklistées par la sonde IPS
            try:
                return self._j(_ipsctl("/ipsctl/blocklist"))
            except (OSError, ValueError) as e:
                return self._j({"error": str(e), "ips": [], "count": 0}, 502)
        if path == "/health":
            return self._j({"status": "ok"})
        self._j({"detail": "not found"}, 404)

    def do_POST(self):
        path = self.path.split("?")[0]
        if path in ("/participation/clic", "/participation/rejoindre"):
            with _lock:
                etat["total"] += 1
            return self._j({"total": snapshot()["total"], "phase": snapshot()["phase"]})
        if path == "/participation/armer":              # opérateur : lance la vague
            # Cible optionnelle (?cible=10.60.64.36) choisie au cockpit. Le périmètre
            # est vérifié côté charge (ra-attacker) : une cible hors zone fait refuser.
            qs = parse_qs(urlparse(self.path).query)
            cible = (qs.get("cible", [None])[0] or None)
            with _lock:
                etat["debut"] = time.time() + DECOMPTE_S
                etat["fin"] = None                      # pas de fin auto : arrêt manuel
                etat["phase"] = "decompte"
                if cible:
                    etat["cible"] = cible.strip()
            return self._j(snapshot())
        if path == "/participation/stop":               # opérateur : arrête la vague en cours
            with _lock:
                etat["fin"] = time.time()
                if etat["phase"] != "repos":
                    etat["phase"] = "termine"
            return self._j(snapshot())
        if path == "/participation/reset":              # opérateur : remet à zéro
            with _lock:
                etat.update(total=0, phase="repos", debut=None, fin=None, cible=None)
            return self._j(snapshot())
        if path == "/participation/unblock":            # opérateur : débloque une IP (bouton)
            ip = (parse_qs(urlparse(self.path).query).get("ip", [""])[0]).strip()
            if not ip:
                return self._j({"error": "ip requise"}, 400)
            try:
                return self._j(_ipsctl("/ipsctl/unblock", {"ip": ip}))
            except (OSError, ValueError) as e:
                return self._j({"ok": False, "detail": str(e)}, 502)
        if path == "/tunnel/demarrer":                  # opérateur : ouvre le tunnel public
            ok, detail = tunnel_action("start")
            return self._j({"ok": ok, "detail": detail}, 200 if ok else 500)
        if path == "/tunnel/arreter":
            ok, detail = tunnel_action("stop")
            return self._j({"ok": ok, "detail": detail}, 200 if ok else 500)
        if path == "/tunnel/regenerer":                 # QR mort : nouvelle URL publique
            tunnel_action("stop")
            try:
                open(CLOUDFLARED_LOG, "w").close()      # purge l'ancienne URL du log
            except OSError:
                pass
            ok, detail = tunnel_action("start")
            return self._j({"ok": ok, "detail": detail}, 200 if ok else 500)
        self._j({"detail": "not found"}, 404)

    def log_message(self, *a):
        pass


PAGE = """<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITRE__ — Participez</title><style>
 :root{--noir:#0b0e17;--neon:#36f1cd;--accent:#ff5d73;--txt:#e6edf3;}
 *{box-sizing:border-box;-webkit-tap-highlight-color:transparent;}
 body{margin:0;background:var(--noir);color:var(--txt);font:16px/1.5 ui-monospace,Menlo,Consolas,monospace;
  display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:100vh;padding:20px;text-align:center;}
 h1{color:var(--neon);letter-spacing:.06em;margin:.2em 0;font-size:1.3rem;}
 .sub{color:var(--accent);text-transform:uppercase;letter-spacing:.2em;font-size:.75rem;margin-bottom:6px;}
 #etat{color:#8b97b5;min-height:2.2em;margin:10px 0;}
 button{margin-top:18px;width:min(78vw,300px);height:min(78vw,300px);border-radius:50%;border:0;cursor:pointer;
  background:radial-gradient(circle at 50% 38%,#ff8a99,var(--accent));color:#1a0309;font:inherit;font-weight:800;
  font-size:1.5rem;letter-spacing:.08em;box-shadow:0 0 0 6px #2a0a12,0 16px 50px rgba(255,93,115,.5);
  transition:transform .06s,filter .1s;}
 button:active{transform:scale(.92);filter:brightness(1.15);}
 button:disabled{filter:grayscale(.7) brightness(.7);cursor:not-allowed;box-shadow:none;}
 .cpt{font-size:2.6rem;color:var(--neon);font-weight:800;margin-top:14px;}
 .hint{color:#5d6b88;font-size:.8rem;margin-top:8px;max-width:340px;}
</style></head><body>
 <div class="sub">__TITRE__</div><h1>Déclenchez la vague</h1>
 <div id="etat">Chargement…</div>
 <button id="b">DDoS<br>!</button>
 <div class="cpt" id="c">0</div>
 <div class="hint">Cliquez autant que possible. Chaque clic renforce la vague de charge
  envoyée sur la plateforme de démonstration — et met à l'épreuve sa reprise automatique.</div>
<script>
let perso=0;
const b=document.getElementById('b'),c=document.getElementById('c'),et=document.getElementById('etat');
async function clic(){ perso++; c.textContent=perso; try{await fetch('/participation/clic',{method:'POST'});}catch(e){} }
b.addEventListener('click',clic);
async function maj(){ try{ const r=await fetch('/participation/etat'); const j=await r.json();
  const ph={repos:'En attente du lancement…',decompte:'Départ dans '+j.decompte+' s — cliquez !',
    en_cours:'🔥 VAGUE EN COURS ('+j.ecoule+' s) — continuez !',termine:'Vague terminée. Merci !'}[j.phase]||j.phase;
  et.innerHTML=ph+'<br><span style="color:#36f1cd">'+j.total+' clics au total</span>';
  b.disabled=(j.phase==='termine'); }catch(e){ et.textContent='Hors ligne'; } }
maj(); setInterval(maj,1000);
</script></body></html>""".replace("__TITRE__", TITRE)

QR_PAGE = """<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITRE__ — Scannez pour participer</title><style>
 body{margin:0;min-height:100vh;background:#0b0e17;color:#e6edf3;display:flex;flex-direction:column;
  align-items:center;justify-content:center;font:16px/1.4 ui-monospace,Menlo,Consolas,monospace;padding:24px;gap:10px;}
 .sub{color:#ff5d73;text-transform:uppercase;letter-spacing:.3em;font-size:.9rem;}
 h1{color:#36f1cd;letter-spacing:.04em;margin:.2em 0;text-align:center;}
 img{width:min(56vmin,400px);height:auto;background:#fff;padding:14px;border-radius:16px;
  box-shadow:0 20px 60px rgba(54,241,205,.25);}
 .url{color:#8b97b5;word-break:break-all;text-align:center;font-size:.85rem;}
 .ctrl{display:flex;gap:12px;flex-wrap:wrap;justify-content:center;margin-top:8px;}
 .ctrl button{padding:12px 22px;font:inherit;font-weight:800;letter-spacing:.04em;border:0;border-radius:9px;cursor:pointer;transition:filter .1s;}
 #on{background:#36f1cd;color:#031312;} #off{background:#ff5d73;color:#1a0309;} #rst{background:#30384f;color:#e6edf3;}
 #regen{padding:8px 18px;font:inherit;font-weight:700;border:1px solid #30384f;border-radius:8px;
  background:transparent;color:#8b97b5;cursor:pointer;transition:filter .1s;}
 #regen:hover{filter:brightness(1.3);} #regen:disabled{cursor:wait;opacity:.6;}
 .ctrl button:hover{filter:brightness(1.12);} .ctrl button:disabled{filter:grayscale(.6) brightness(.6);cursor:not-allowed;}
 #etat{min-height:1.5em;color:#e6edf3;font-weight:700;text-align:center;}
 .bl{width:min(92vw,460px);margin-top:10px;}
 .blh{color:#ff5d73;text-transform:uppercase;letter-spacing:.2em;font-size:.75rem;margin-bottom:6px;text-align:center;}
 .blr{display:flex;align-items:center;justify-content:space-between;gap:10px;background:#141a28;
  border:1px solid #26304a;border-radius:8px;padding:7px 12px;margin:5px 0;font-size:.9rem;}
 .blr span{color:#e6edf3;}
 .blr button{padding:6px 14px;font:inherit;font-weight:700;border:0;border-radius:7px;cursor:pointer;
  background:#36f1cd;color:#031312;transition:filter .1s;}
 .blr button:hover{filter:brightness(1.1);} .blr button:disabled{filter:grayscale(.6) brightness(.6);cursor:wait;}
</style></head><body>
 <div class="sub">__TITRE__</div>
 <h1>Scannez pour participer à la vague</h1>
 <img id="qr" src="/qrcode.png" alt="QR code">
 <div class="url" id="url">__URL__</div>
 <button id="regen" onclick="regen()">↻ Régénérer le QR</button>
 <div id="etat">—</div>
 <div class="ctrl">
   <button id="on"  onclick="act('armer')">▶ Armer la vague</button>
   <button id="off" onclick="act('stop')">■ Arrêter</button>
   <button id="rst" onclick="act('reset')">↺ Reset</button>
 </div>
 <div id="bl" class="bl"></div>
<script>
const et=document.getElementById('etat'), on=document.getElementById('on'), off=document.getElementById('off'),
      regenb=document.getElementById('regen'), qr=document.getElementById('qr'), urld=document.getElementById('url');
async function act(quoi){ try{ await fetch('/participation/'+quoi,{method:'POST'}); }catch(e){} maj(); }
async function regen(){
  regenb.disabled=true; const ancienne=urld.textContent.trim(); regenb.textContent='Régénération…';
  try{ const r=await fetch('/tunnel/regenerer',{method:'POST'}); const j=await r.json();
    if(!j.ok){ regenb.textContent='Échec — réessayer'; regenb.disabled=false; return; } }
  catch(e){ regenb.textContent='Erreur — réessayer'; regenb.disabled=false; return; }
  for(let i=0;i<40;i++){ await new Promise(r=>setTimeout(r,1500));
    try{ const s=await (await fetch('/tunnel/etat')).json();
      if(s.url && s.url!==ancienne){ location.reload(); return; } }catch(e){} }
  regenb.textContent='↻ Régénérer le QR'; regenb.disabled=false;
}
async function maj(){ try{ const j=await (await fetch('/participation/etat')).json();
  const t={repos:'Au repos — '+j.total+' clics en réserve',
    decompte:'Départ dans '+j.decompte+' s ('+j.total+' participants)',
    en_cours:'VAGUE EN COURS — '+j.ecoule+' s (Arrêter pour stopper)',
    termine:'Vague terminée'}[j.phase]||j.phase;
  et.textContent=t;
  const actif=(j.phase==='decompte'||j.phase==='en_cours');
  on.disabled=actif; off.disabled=!actif; }catch(e){ et.textContent='hors ligne'; } }
maj(); setInterval(maj,1000);
const bl=document.getElementById('bl');
async function majBl(){ try{ const j=await (await fetch('/participation/blocklist')).json();
  const ips=j.ips||[];
  if(!ips.length){ bl.innerHTML='<div class="blh">IP blacklistées : aucune</div>'; return; }
  let h='<div class="blh">IP blacklistées ('+ips.length+')</div>';
  for(const e of ips){ const exp=(e.expires_s!=null)?(' · '+Math.round(e.expires_s)+' s'):'';
    h+='<div class="blr"><span>'+e.ip+exp+'</span><button class="deb" data-ip="'+e.ip+'">Débloquer</button></div>'; }
  bl.innerHTML=h; }catch(e){ bl.innerHTML='<div class="blh">blacklist indisponible</div>'; } }
bl.addEventListener('click',async ev=>{ const b=ev.target.closest('.deb'); if(!b) return;
  b.disabled=true; b.textContent='…'; try{ await fetch('/participation/unblock?ip='+encodeURIComponent(b.dataset.ip),{method:'POST'}); }catch(e){} majBl(); });
majBl(); setInterval(majBl,2000);
</script></body></html>""".replace("__TITRE__", TITRE)

QR_ATTENTE = """<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>QR — tunnel</title>
<style>
 body{margin:0;min-height:100vh;background:#0b0e17;color:#e6edf3;display:flex;flex-direction:column;
  align-items:center;justify-content:center;font:18px ui-monospace,Menlo,Consolas,monospace;text-align:center;padding:24px;gap:18px;}
 h1{color:#36f1cd;letter-spacing:.04em;}
 button{padding:16px 34px;font:inherit;font-weight:800;letter-spacing:.06em;border:0;border-radius:10px;
  background:#36f1cd;color:#031312;cursor:pointer;transition:filter .1s;}
 button:hover{filter:brightness(1.12);} button:disabled{filter:grayscale(.6) brightness(.7);cursor:wait;}
 #msg{color:#8b97b5;min-height:1.5em;}
</style></head><body>
 <h1>QR de participation</h1>
 <div id="msg">Le tunnel public n'est pas démarré.</div>
 <button id="b" onclick="demarrer()">Démarrer le tunnel et générer le QR</button>
<script>
const b=document.getElementById('b'), msg=document.getElementById('msg');
async function demarrer(){
  b.disabled=true; msg.textContent='Démarrage du tunnel…';
  try{ const r=await fetch('/tunnel/demarrer',{method:'POST'}); const j=await r.json();
    if(!j.ok){ msg.textContent='Échec : '+(j.detail||'')+' — vérifiez cloudflared.'; b.disabled=false; return; } }
  catch(e){ msg.textContent='Erreur : '+e; b.disabled=false; return; }
  msg.textContent='Tunnel démarré, attribution de l\\'URL publique…';
  for(let i=0;i<40;i++){ await new Promise(r=>setTimeout(r,1500));
    try{ const s=await (await fetch('/tunnel/etat')).json();
      if(s.url){ msg.textContent='Prêt ! Redirection…'; location.href='/qr'; return; } }catch(e){} }
  msg.textContent='URL pas encore disponible. Réessayez dans un instant.'; b.disabled=false;
}
// si le tunnel est déjà actif avec une URL, aller directement au QR
fetch('/tunnel/etat').then(r=>r.json()).then(s=>{ if(s.url) location.href='/qr'; });
</script></body></html>"""

if __name__ == "__main__":
    print(json.dumps({"service": "participation", "message": "démarrage", "port": PORT}), flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), H).serve_forever()
