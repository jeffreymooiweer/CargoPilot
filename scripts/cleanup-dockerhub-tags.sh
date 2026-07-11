#!/usr/bin/env bash
# Verwijder oude Docker Hub-tags (behalve opgegeven keep-lijst).
# Gebruik: DOCKER_USERNAME=... DOCKER_TOKEN=... ./scripts/cleanup-dockerhub-tags.sh
# Dry-run: DRY_RUN=1 ./scripts/cleanup-dockerhub-tags.sh

set -euo pipefail

REPO="${DOCKER_REPO:-jeffersonmouze/cargopilot}"
KEEP_TAGS="${KEEP_TAGS:-latest,v1.0.0,1.0.0}"
TOKEN="${DOCKER_TOKEN:-${DOCKER_PASSWORD:-}}"

if [ -z "${DOCKER_USERNAME:-}" ] || [ -z "$TOKEN" ]; then
  echo "Zet DOCKER_USERNAME en DOCKER_TOKEN (of DOCKER_PASSWORD)." >&2
  exit 1
fi

HUB_TOKEN=$(curl -fsS -X POST "https://hub.docker.com/v2/users/login/" \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"${DOCKER_USERNAME}\",\"password\":\"${TOKEN}\"}" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")

IFS=',' read -ra KEEP <<< "$KEEP_TAGS"
keep_lower=""
for t in "${KEEP[@]}"; do
  keep_lower="${keep_lower} $(echo "$t" | tr '[:upper:]' '[:lower:]' | xargs)"
done

page=1
while true; do
  RESP=$(curl -fsS "https://hub.docker.com/v2/repositories/${REPO}/tags?page_size=100&page=${page}" \
    -H "Authorization: JWT ${HUB_TOKEN}")
  COUNT=$(echo "$RESP" | python3 -c "import sys,json; print(len(d.get('results',[])))")
  [ "$COUNT" -eq 0 ] && break

  while IFS= read -r tag; do
    [ -z "$tag" ] && continue
    tag_lc=$(echo "$tag" | tr '[:upper:]' '[:lower:]')
    if echo " ${keep_lower} " | grep -q " ${tag_lc} "; then
      echo "KEEP  ${tag}"
      continue
    fi
    if [ "${DRY_RUN:-0}" = "1" ]; then
      echo "WOULD DELETE ${tag}"
    else
      echo "DELETE ${tag}"
      curl -fsS -X DELETE "https://hub.docker.com/v2/repositories/${REPO}/tags/${tag}/" \
        -H "Authorization: JWT ${HUB_TOKEN}"
    fi
  done < <(echo "$RESP" | python3 -c "import sys,json; [print(r['name']) for r in json.load(sys.stdin).get('results',[])]")

  NEXT=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('next') or '')")
  [ -z "$NEXT" ] && break
  page=$((page + 1))
done

echo "Cleanup voltooid."
