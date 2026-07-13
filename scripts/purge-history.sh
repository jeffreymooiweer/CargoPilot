#!/usr/bin/env bash
#
# CargoPilot — git-historie opschonen (verwijdert het interne formulier
# en alle sporen ervan uit ALLE commits op GitHub).
#
# ⚠️  DESTRUCTIEF: alle commit-SHA's veranderen. Doe dit op een moment dat
#     niemand anders aan de repo werkt. Bestaande clones moeten daarna
#     opnieuw gecloned worden.
#
# Vereisten:
#   - git 2.36+
#   - git-filter-repo:  pip install git-filter-repo   (of: brew install git-filter-repo)
#   - Tijdelijk force-pushes toestaan op main als je branch protection hebt
#     (GitHub → Settings → Branches/Rulesets).
#
set -euo pipefail

REPO_URL="https://github.com/jeffreymooiweer/CargoPilot.git"
WORKDIR="$(mktemp -d)"
echo "Werkmap: $WORKDIR"
cd "$WORKDIR"

# ── 1. Verse mirror-clone (git-filter-repo eist een verse clone) ─────────────
git clone --mirror "$REPO_URL" cargopilot-mirror
cd cargopilot-mirror

# ── 2. Bestanden uit de VOLLEDIGE historie verwijderen ───────────────────────
#     (alle paden waar het formulier of bijbehorende code ooit heeft gestaan)
git filter-repo --force \
  --invert-paths \
  --path Appendix_A1D_template.xlsx \
  --path templates/Appendix_A1D_template.xlsx \
  --path backend/app/config/appendix_mapping.json \
  --path backend/app/services/exporter/appendix_exporter.py \
  --path backend/app/services/exporter \
  --path frontend/src/components/AppendixQuestionsWizard.tsx \
  --path frontend/src/components/AppendixFlagsPanel.tsx \
  --path backend/tests/test_exporter.py \
  --path backend/tests/test_exporter_template.py

# ── 3. Tekstsporen scrubben in alle overgebleven historische bestanden ──────
#     (verwijdert de formuliernaam en de defensie-URL uit oude versies van
#      README, i18n, configs, commits enz.)
cat > ../replacements.txt <<'RTXT'
regex:https?://doscoportal\.mindef\.nl[^\s"']*==>[verwijderd]
Appendix_A1D_template==>intern-formulier
Appendix A1/D==>intern formulier
Appendix A1==>intern formulier
Appendix D==>DG-stap
appendix A1==>intern formulier
appendix D==>DG-stap
appendix_a1d==>intern_formulier
RTXT
git filter-repo --force --replace-text ../replacements.txt

# ── 4. Terugpushen (force) ───────────────────────────────────────────────────
git remote add origin "$REPO_URL"
git push origin --force --all
git push origin --force --tags

# ── 5. Oude werkbranch met vervuilde historie opruimen ──────────────────────
git push origin --delete claude/project-analysis-odutve 2>/dev/null || true

echo ""
echo "✅ Klaar. Historie herschreven en gepusht."
echo ""
echo "Vergeet niet (handmatig):"
echo "  1. Branch protection op main weer aanzetten."
echo "  2. Alle lokale clones weggooien en opnieuw clonen"
echo "     (git pull werkt NIET meer na een history-rewrite)."
echo "  3. GitHub bewaart oude PR-diffs en cached views server-side."
echo "     Vraag GitHub Support om die te wissen: Settings → Support,"
echo "     of via https://support.github.com — verwijs naar"
echo "     'Removing sensitive data from a repository' en vraag om"
echo "     verwijdering van cached views + dangling commits (gc)."
echo "  4. Controleer dat de GitHub Release-tags (v1.0.0 t/m v1.4.0) nog"
echo "     kloppen — de zipballs worden automatisch geregenereerd."
