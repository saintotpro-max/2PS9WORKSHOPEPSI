#!/usr/bin/env bash



set -u
RACINE="$(cd "$(dirname "$0")/.." && pwd)"
SORTIE="${1:-$RACINE/Code.zip}"
cd "$RACINE" || exit 1

EXCLUS='(^\./\.git/|/\.venv/|/__pycache__/|/node_modules/|/cache/|/saves/|^\./coll|\.rpyc$|\.pyc$|\.db$|/Code\.zip$|~$)'
mapfile -t FICHIERS < <(find . -type f | grep -vE "$EXCLUS" | sed 's|^\./||')

if [ "${#FICHIERS[@]}" -eq 0 ]; then
  echo "ECHEC : aucun fichier a archiver." >&2
  exit 1
fi


MOTIFS='(BEGIN (RSA|OPENSSH|EC|DSA|PRIVATE) KEY|sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|xox[baprs]-[A-Za-z0-9-]{10,}|ghp_[A-Za-z0-9]{30,}|NANOGPT_API_KEY=.|api[_-]?key["'"'"' ]*[:=]["'"'"' ]*[A-Za-z0-9]{16,})'
TROUVE=$(grep -rIniE "$MOTIFS" "${FICHIERS[@]}" 2>/dev/null \
  | grep -viE '(exemple|example|placeholder|<[a-z_]+>|votre-cle|your-key|\.env\.example)' \
  | grep -vE '^scripts/livrer\.sh:' || true)

if [ -n "$TROUVE" ]; then
  echo "ECHEC : secret potentiel trouve, archive NON produite :" >&2
  echo "$TROUVE" | head -20 >&2
  exit 1
fi

rm -f "$SORTIE"
if ! command -v zip >/dev/null 2>&1; then
  echo "ECHEC : 'zip' absent (apt-get install zip)." >&2
  exit 1
fi
printf '%s\n' "${FICHIERS[@]}" | zip -q "$SORTIE" -@ >/dev/null
echo "OK : $SORTIE ($(du -h "$SORTIE" | cut -f1)), ${#FICHIERS[@]} fichiers, aucun secret detecte."
