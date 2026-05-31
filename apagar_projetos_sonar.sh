#!/bin/bash

set -euo pipefail

SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPTS_DIR")"
CSV_FILE="$SCRIPTS_DIR/projetos-tcc-dataset-3.csv"
SONAR_URL="${SONAR_URL:-http://localhost:9000}"
SONAR_TOKEN="${SONAR_TOKEN:-sqa_0c5cfbfcb1d5613b1743f31698aa8580a746d83f}"

DRY_RUN=false
YES=false
while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run) DRY_RUN=true; shift ;;
        --yes|-y)  YES=true; shift ;;
        -h|--help)
            sed -n '2,12p' "$0" | sed 's/^# *//'
            exit 0 ;;
        *) echo "[ERRO] argumento desconhecido: $1" >&2; exit 2 ;;
    esac
done

if [[ ! -f "$CSV_FILE" ]]; then
    echo "[ERRO] CSV não encontrado: $CSV_FILE" >&2
    exit 1
fi

if ! curl -sf "$SONAR_URL/api/system/status" -u "$SONAR_TOKEN:" > /dev/null 2>&1; then
    echo "[ERRO] SonarQube não acessível em $SONAR_URL" >&2
    exit 1
fi

mapfile -t LINHAS < <(python3 - "$CSV_FILE" <<'PY'
import csv, sys
ARQS = {"apache", "google", "descentralizado"}
with open(sys.argv[1], newline="") as f:
    reader = csv.DictReader(f)
    for row in reader:
        arq = (row.get("arquetipo") or "").strip().lower()
        if arq not in ARQS:
            continue
        pid = (row.get("id") or "").strip()
        spk = (row.get("sonar_project_key") or "").strip()
        if not pid:
            continue
        diverg = "1" if (spk and spk != pid) else "0"
        print(f"{pid}\t{spk}\t{arq}\t{diverg}")
PY
)

if [[ ${#LINHAS[@]} -eq 0 ]]; then
    echo "[ERRO] Nenhuma linha elegível no CSV (arquetipo válido + id)" >&2
    exit 1
fi

echo "============================================"
echo "Sonar: $SONAR_URL"
echo "CSV:   $CSV_FILE"
echo "Linhas elegíveis: ${#LINHAS[@]}"
[[ "$DRY_RUN" == true ]] && echo "MODO: DRY-RUN (nada será apagado)" || echo "MODO: APAGAR"
echo "============================================"

divergiu=0
for entry in "${LINHAS[@]}"; do
    IFS=$'\t' read -r pid spk arq div <<< "$entry"
    if [[ "$div" == "1" ]]; then
        echo "[WARN] divergência id≠sonar_project_key — id=$pid spk=$spk (usando id)"
        divergiu=$(( divergiu + 1 ))
    fi
done
[[ "$divergiu" -gt 0 ]] && echo "[INFO] $divergiu divergências; id é a chave canônica."

if [[ "$DRY_RUN" == false && "$YES" == false ]]; then
    echo ""
    echo "Vai apagar ${#LINHAS[@]} projetos do SonarQube em $SONAR_URL."
    read -r -p "Digite EXATAMENTE 'apagar' para confirmar: " resp
    if [[ "$resp" != "apagar" ]]; then
        echo "[ABORTADO] Confirmação inválida."
        exit 0
    fi
fi

apagados=0
falhas=0
nao_encontrados=0

projeto_existe() {
    local key="$1"
    local code
    code=$(curl -s -o /dev/null -w "%{http_code}" \
        -u "$SONAR_TOKEN:" \
        "$SONAR_URL/api/measures/component?component=$key&metricKeys=ncloc")
    [[ "$code" == "200" ]]
}

for entry in "${LINHAS[@]}"; do
    IFS=$'\t' read -r pid spk arq div <<< "$entry"

    if ! projeto_existe "$pid"; then
        echo "[NOT_FOUND] $pid (arq=$arq) — não está no Sonar"
        nao_encontrados=$(( nao_encontrados + 1 ))
        continue
    fi

    if [[ "$DRY_RUN" == true ]]; then
        echo "[DRY-RUN] apagaria $pid (arq=$arq)"
        apagados=$(( apagados + 1 ))
        continue
    fi

    response=$(curl -s -o /tmp/sonar_delete_resp.$$ -w "%{http_code}" \
        -X POST -u "$SONAR_TOKEN:" \
        --data-urlencode "project=$pid" \
        "$SONAR_URL/api/projects/delete")
    body=$(cat /tmp/sonar_delete_resp.$$ 2>/dev/null || echo "")
    rm -f /tmp/sonar_delete_resp.$$

    case "$response" in
        204|200)
            echo "[OK] apagado: $pid (arq=$arq)"
            apagados=$(( apagados + 1 ))
            ;;
        401|403)
            echo "[ERRO_PERM] $pid — HTTP $response. Token sem permissão de admin."
            echo "             corpo: $body"
            falhas=$(( falhas + 1 ))
            echo "[FATAL] interrompendo: token inválido para deletar (gere um token de Global Admin)."
            exit 4
            ;;
        404)
            echo "[NOT_FOUND_API] $pid — HTTP 404 (sumiu entre check e delete)"
            nao_encontrados=$(( nao_encontrados + 1 ))
            ;;
        *)
            echo "[ERRO] $pid — HTTP $response — $body"
            falhas=$(( falhas + 1 ))
            ;;
    esac
done

echo ""
echo "============================================"
if [[ "$DRY_RUN" == true ]]; then
    echo "DRY-RUN concluído"
    echo "  Seriam apagados:  $apagados"
else
    echo "Apagamento concluído"
    echo "  Apagados:         $apagados"
fi
echo "  Não encontrados:  $nao_encontrados"
echo "  Falhas:           $falhas"
echo "============================================"

[[ "$falhas" -gt 0 ]] && exit 5
exit 0
