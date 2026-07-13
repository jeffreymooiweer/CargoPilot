#!/usr/bin/env bash
#
# CargoPilot — git-historie opschonen (verwijdert het interne militaire
# formulier en alle sporen ervan uit ALLE commits op GitHub).
#
# Status: reeds uitgevoerd (juli 2026). Bewaar dit als naslag / herhaal-
# procedure. Op een schone historie is opnieuw draaien meestal niet nodig.
#
# ⚠️  DESTRUCTIEF: alle commit-SHA's veranderen. Bestaande clones daarna
#     opnieuw clonen. Force-push naar main vereist tijdelijk uitgezette
#     branch protection.
#
# Vereisten: git 2.36+, git-filter-repo, push-rechten met force.
#
set -euo pipefail

REPO_SSH_OR_HTTPS="${REPO_URL:-https://github.com/jeffreymooiweer/CargoPilot.git}"
if [[ -n "${GH_TOKEN:-${GITHUB_TOKEN:-}}" ]]; then
  TOKEN="${GH_TOKEN:-$GITHUB_TOKEN}"
  PUSH_URL="https://x-access-token:${TOKEN}@github.com/jeffreymooiweer/CargoPilot.git"
elif [[ "$REPO_SSH_OR_HTTPS" == *"x-access-token:"* ]]; then
  PUSH_URL="$REPO_SSH_OR_HTTPS"
else
  PUSH_URL="$REPO_SSH_OR_HTTPS"
fi

WORKDIR="$(mktemp -d)"
echo "Werkmap: $WORKDIR"
cd "$WORKDIR"

echo "==> 1. Verse mirror-clone"
git clone --mirror "$PUSH_URL" cargopilot-mirror
cd cargopilot-mirror

echo "==> 2. Formulierbestanden en -code uit alle commits verwijderen"
# Historische padnamen (vóór civiele opschoning). Globs vangen hernoemingen.
git filter-repo --force \
  --invert-paths \
  --path-glob '*Appendix_A1D*' \
  --path-glob '*appendix_mapping*' \
  --path-glob '*appendix_exporter*' \
  --path-glob '*AppendixQuestionsWizard*' \
  --path-glob '*AppendixFlagsPanel*' \
  --path backend/app/services/exporter \
  --path backend/tests/test_exporter.py \
  --path backend/tests/test_exporter_template.py

echo "==> 3. Tekstsporen scrubben (defensie-URL + formuliervormen)"
cat > ../replacements.txt <<'RTXT'
regex:https?://doscoportal\.mindef\.nl[^\s"'<>)]*==>[verwijderd]
regex:Appendix[_ ]?A1[/D]*==>intern formulier
regex:appendix_a1d==>intern_formulier
RTXT
git filter-repo --force --replace-text ../replacements.txt

echo "==> 4. Force-push alle branches + tags"
git remote add origin "$PUSH_URL"
git push origin --force --all
git push origin --force --tags

echo "==> 5. Vervuilde agent-branch opruimen (indien aanwezig)"
git push origin --delete claude/project-analysis-odutve 2>/dev/null || true

echo ""
echo "✅ Klaar. Historie herschreven en gepusht."
echo ""
echo "Handmatig:"
echo "  1. Branch protection op main weer aanzetten (indien nodig)."
echo "  2. Lokale clones weggooien en opnieuw clonen."
echo "  3. GitHub Support vragen om cached views/dangling commits te wissen"
echo "     ('Removing sensitive data from a repository')."
