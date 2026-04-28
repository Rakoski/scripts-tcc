#!/usr/bin/env bash
#
# extrair_metricas_sonar.sh — Extrai loc_total, loc_java, pct_java, sonar_status
# da API do SonarQube e atualiza o CSV
#
# Uso:
#   ./extrair_metricas_sonar.sh                # atualiza todos
#   ./extrair_metricas_sonar.sh --dry-run      # mostra sem gravar
#
set -euo pipefail

BASE_DIR="/home/mateus/Documentos/artigos-tcc/repos/tcc"
SCRIPTS_DIR="$BASE_DIR/scripts-tcc"
CSV_FILE="$SCRIPTS_DIR/projetos-tcc-dataset-3.csv"
CSV_TMP="$SCRIPTS_DIR/.projetos-tcc-dataset-3.csv.tmp"
SONAR_URL="http://localhost:9000"
SONAR_TOKEN="sqa_0c5cfbfcb1d5613b1743f31698aa8580a746d83f"

DRY_RUN=false
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=true

# Verifica SonarQube
if ! curl -sf "$SONAR_URL/api/system/status" -u "$SONAR_TOKEN:" > /dev/null 2>&1; then
    echo "[ERRO] SonarQube não acessível"; exit 1
fi

# Busca métricas de um projeto
get_metrics() {
    local key="$1"
    curl -sf -u "$SONAR_TOKEN:" \
        "$SONAR_URL/api/measures/component?component=$key&metricKeys=ncloc,ncloc_language_distribution" 2>/dev/null
}

# Busca quality gate status
get_quality_gate() {
    local key="$1"
    curl -sf -u "$SONAR_TOKEN:" \
        "$SONAR_URL/api/qualitygates/project_status?projectKey=$key" 2>/dev/null
}

# Extrai valor de uma métrica do JSON
extract_metric() {
    local json="$1"
    local metric="$2"
    echo "$json" | python3 -c "
import sys, json
data = json.load(sys.stdin)
measures = data.get('component', {}).get('measures', [])
for m in measures:
    if m['metric'] == '$metric':
        print(m['value'])
        break
" 2>/dev/null
}

echo "============================================"
echo "Extraindo métricas do SonarQube"
echo "============================================"
echo ""

# Copia header
head -1 "$CSV_FILE" > "$CSV_TMP"

updated=0
skipped=0
not_found=0

# Processa cada linha (pula header)
tail -n+2 "$CSV_FILE" | while IFS= read -r line; do
    # Parse campos — CSV simples (sem aspas com vírgulas internas, exceto notas no final)
    id=$(echo "$line" | cut -d, -f1)
    nome=$(echo "$line" | cut -d, -f2)
    tag=$(echo "$line" | cut -d, -f7)

    # Se não tem tag, copia linha sem alterar
    if [[ -z "$tag" ]]; then
        echo "$line" >> "$CSV_TMP"
        echo "[SKIP] $nome — sem tag"
        (( skipped++ )) || true
        continue
    fi

    project_key="$id"

    # Tenta buscar métricas
    metrics_json=$(get_metrics "$project_key" || echo "")

    # Resposta de erro do SonarQube tem a forma {"errors":[{"msg":"..."}]}.
    # Não usar substring "error" solto — casa com nomes tipo "error-prone".
    if [[ -z "$metrics_json" || "$metrics_json" == *'"errors":'* || "$metrics_json" == *"not found"* ]]; then
        echo "[NOT FOUND] $project_key — não encontrado no SonarQube"
        echo "$line" >> "$CSV_TMP"
        (( not_found++ )) || true
        continue
    fi

    # Extrai ncloc (total)
    loc_total=$(extract_metric "$metrics_json" "ncloc")
    loc_total=${loc_total:-""}

    # Extrai distribuição por linguagem e calcula loc_java
    lang_dist=$(extract_metric "$metrics_json" "ncloc_language_distribution")
    loc_java=""
    if [[ -n "$lang_dist" ]]; then
        # Formato: "java=123456;xml=789;..."
        loc_java=$(echo "$lang_dist" | tr ';' '\n' | grep "^java=" | cut -d= -f2)
    fi
    loc_java=${loc_java:-"0"}

    # Calcula pct_java
    pct_java=""
    if [[ -n "$loc_total" && "$loc_total" -gt 0 && -n "$loc_java" ]]; then
        pct_java=$(echo "scale=1; $loc_java * 100 / $loc_total" | bc)
    fi

    # Quality gate
    qg_json=$(get_quality_gate "$project_key" || echo "")
    sonar_status=""
    if [[ -n "$qg_json" ]]; then
        sonar_status=$(echo "$qg_json" | python3 -c "
import sys, json
data = json.load(sys.stdin)
status = data.get('projectStatus', {}).get('status', '')
print('Passed' if status == 'OK' else 'Failed' if status else '')
" 2>/dev/null)
    fi

    # Reconstrói a linha CSV
    # Campos: id,nome,empresa,arquetipo,status,url,tag,commit_sha,data_commit,loc_total,loc_java,pct_java,contribuidores,idade_anos,sonar_status,sonar_project_key,notas
    f_empresa=$(echo "$line" | cut -d, -f3)
    f_arquetipo=$(echo "$line" | cut -d, -f4)
    f_status=$(echo "$line" | cut -d, -f5)
    f_url=$(echo "$line" | cut -d, -f6)
    f_commit_sha=$(echo "$line" | cut -d, -f8)
    f_data_commit=$(echo "$line" | cut -d, -f9)
    f_contribuidores=$(echo "$line" | cut -d, -f13)
    f_idade_anos=$(echo "$line" | cut -d, -f14)
    # notas pode conter vírgulas, pega tudo a partir do campo 17
    f_notas=$(echo "$line" | cut -d, -f17-)

    new_line="$id,$nome,$f_empresa,$f_arquetipo,$f_status,$f_url,$tag,$f_commit_sha,$f_data_commit,$loc_total,$loc_java,$pct_java,$f_contribuidores,$f_idade_anos,$sonar_status,$project_key,$f_notas"

    if $DRY_RUN; then
        echo "[DRY-RUN] $nome: loc_total=$loc_total loc_java=$loc_java pct_java=$pct_java sonar_status=$sonar_status"
    fi

    echo "$new_line" >> "$CSV_TMP"
    echo "[OK] $nome: loc_total=$loc_total | loc_java=$loc_java | pct_java=$pct_java | sonar=$sonar_status"
    (( updated++ )) || true
done

if $DRY_RUN; then
    echo ""
    echo "[DRY-RUN] Nenhuma alteração gravada. Removendo temp."
    rm -f "$CSV_TMP"
else
    # Substitui o CSV original
    mv "$CSV_TMP" "$CSV_FILE"
    echo ""
    echo "[OK] CSV atualizado: $CSV_FILE"
fi

echo ""
echo "============================================"
echo "Extração concluída"
echo "  Atualizados:    $updated"
echo "  Pulados:        $skipped"
echo "  Não encontrados: $not_found"
echo "============================================"
