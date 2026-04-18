#!/usr/bin/env bash
#
# coletar_dados_repos.sh — Coleta metadados de repositórios Git para o TCC
#
# Uso:
#   ./coletar_dados_repos.sh                  # processa todos os 45
#   ./coletar_dados_repos.sh --dry-run        # mostra o que faria, sem gravar
#   ./coletar_dados_repos.sh --limit 3        # processa apenas os 3 primeiros
#
set -euo pipefail

BASE_DIR="/home/mateus/Documentos/artigos-tcc/repos/tcc"
CLONE_DIR="$BASE_DIR/projetos-clonados"
SCRIPTS_DIR="$BASE_DIR/scripts-tcc"
CSV_FILE="$SCRIPTS_DIR/projetos-tcc-dataset.csv"
MANUAL_REVIEW="$SCRIPTS_DIR/manual-review.md"
HEADER="id,nome,empresa,arquetipo,status,url,tag,commit_sha,data_commit,loc_total,loc_java,pct_java,contribuidores,idade_anos,sonar_status,sonar_project_key,notas"

DRY_RUN=false
LIMIT=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run) DRY_RUN=true; shift ;;
        --limit)   LIMIT="$2"; shift 2 ;;
        *)         echo "Argumento desconhecido: $1"; exit 1 ;;
    esac
done

# Data de referência: 2026-01-01
CUTOFF_DATE="2026-01-01"
CUTOFF_EPOCH=$(date -d "$CUTOFF_DATE" +%s)
# Data de hoje para cálculo de status
TODAY_EPOCH=$(date +%s)

# Inicializa CSV se não existe ou está vazio
if [[ ! -f "$CSV_FILE" ]]; then
    echo "$HEADER" > "$CSV_FILE"
    echo "[INFO] CSV criado: $CSV_FILE"
fi

# Inicializa manual-review.md
cat > "$MANUAL_REVIEW" <<'MEOF'
# Revisão Manual Necessária

Projetos que precisaram de decisão humana durante a coleta de dados.

| Projeto | Empresa | Motivo |
|---------|---------|--------|
MEOF

# Contador sequencial por empresa (lê os que já existem no CSV)
declare -A SEQ_COUNTER
while IFS=, read -r id _rest; do
    if [[ "$id" == "id" ]]; then continue; fi
    # Extrai empresa e sequencial do id (ex: netflix-ribbon-01)
    empresa_key=$(echo "$id" | sed 's/-[0-9]*$//' | sed 's/-[^-]*$//')
    seq_num=$(echo "$id" | grep -oP '\d+$')
    seq_num=$((10#$seq_num))  # remove zero à esquerda
    current=${SEQ_COUNTER[$empresa_key]:-0}
    if (( seq_num > current )); then
        SEQ_COUNTER[$empresa_key]=$seq_num
    fi
done < "$CSV_FILE"

# ========== LISTA DE REPOSITÓRIOS ==========
# Formato: "nome|empresa|arquetipo|url"
REPOS=(
    "tomcat|Apache|apache|https://github.com/apache/tomcat"
    "zookeeper|Apache|apache|https://github.com/apache/zookeeper"
    "kafka|Apache|apache|https://github.com/apache/kafka"
    "cassandra|Apache|apache|https://github.com/apache/cassandra"
    "flink|Apache|apache|https://github.com/apache/flink"
    "commons-lang|Apache|apache|https://github.com/apache/commons-lang"
    "commons-io|Apache|apache|https://github.com/apache/commons-io"
    "commons-collections|Apache|apache|https://github.com/apache/commons-collections"
    "maven|Apache|apache|https://github.com/apache/maven"
    "lucene|Apache|apache|https://github.com/apache/lucene"
    "camel|Apache|apache|https://github.com/apache/camel"
    "curator|Apache|apache|https://github.com/apache/curator"
    "dubbo|Apache|apache|https://github.com/apache/dubbo"
    "pulsar|Apache|apache|https://github.com/apache/pulsar"
    "mina|Apache|apache|https://github.com/apache/mina"
    "guava|Google|google|https://github.com/google/guava"
    "gson|Google|google|https://github.com/google/gson"
    "dagger|Google|google|https://github.com/google/dagger"
    "auto|Google|google|https://github.com/google/auto"
    "grpc-java|Google|google|https://github.com/grpc/grpc-java"
    "error-prone|Google|google|https://github.com/google/error-prone"
    "truth|Google|google|https://github.com/google/truth"
    "tink|Google|google|https://github.com/google/tink"
    "jib|Google|google|https://github.com/GoogleContainerTools/jib"
    "closure-compiler|Google|google|https://github.com/google/closure-compiler"
    "j2objc|Google|google|https://github.com/google/j2objc"
    "protobuf|Google|google|https://github.com/protocolbuffers/protobuf"
    "flatbuffers|Google|google|https://github.com/google/flatbuffers"
    "google-java-format|Google|google|https://github.com/google/google-java-format"
    "jimfs|Google|google|https://github.com/google/jimfs"
    "hollow|Netflix|descentralizado|https://github.com/Netflix/hollow"
    "mantis|Netflix|descentralizado|https://github.com/Netflix/mantis"
    "conductor|Netflix|descentralizado|https://github.com/Netflix/conductor"
    "EVCache|Netflix|descentralizado|https://github.com/Netflix/EVCache"
    "spectator|Netflix|descentralizado|https://github.com/Netflix/spectator"
    "metacat|Netflix|descentralizado|https://github.com/Netflix/metacat"
    "dgs-framework|Netflix|descentralizado|https://github.com/Netflix/dgs-framework"
    "NullAway|Uber|descentralizado|https://github.com/uber/NullAway"
    "AutoDispose|Uber|descentralizado|https://github.com/uber/AutoDispose"
    "jvm-profiler|Uber|descentralizado|https://github.com/uber-common/jvm-profiler"
    "h3-java|Uber|descentralizado|https://github.com/uber/h3-java"
    "RIBs|Uber|descentralizado|https://github.com/uber/RIBs"
    "github-java-client|Spotify|descentralizado|https://github.com/spotify/github-java-client"
    "completable-futures|Spotify|descentralizado|https://github.com/spotify/completable-futures"
    "cruise-control|LinkedIn|descentralizado|https://github.com/linkedin/cruise-control"
)

processed=0

for entry in "${REPOS[@]}"; do
    IFS='|' read -r nome empresa arquetipo url <<< "$entry"

    if (( LIMIT > 0 && processed >= LIMIT )); then
        break
    fi

    echo ""
    echo "============================================"
    echo "[$(( processed + 1 ))] Processando: $empresa/$nome"
    echo "============================================"

    # Chave para o sequencial (empresa em minúsculo)
    empresa_lower=$(echo "$empresa" | tr '[:upper:]' '[:lower:]')
    # Verifica se já existe no CSV
    if grep -q ",$nome,$empresa," "$CSV_FILE" 2>/dev/null; then
        echo "[SKIP] $nome já existe no CSV, pulando."
        (( processed++ )) || true
        continue
    fi

    # Incrementa sequencial
    current_seq=${SEQ_COUNTER[$empresa_lower]:-0}
    new_seq=$(( current_seq + 1 ))
    SEQ_COUNTER[$empresa_lower]=$new_seq
    id=$(printf "%s-%s-%02d" "$empresa_lower" "$nome" "$new_seq" | tr '[:upper:]' '[:lower:]')

    repo_dir="$CLONE_DIR/$nome"

    # ---- Passo 1: Clone ----
    if [[ -d "$repo_dir/.git" ]]; then
        echo "[OK] Repo já clonado: $repo_dir"
    else
        echo "[CLONE] Clonando $url ..."
        if $DRY_RUN; then
            echo "[DRY-RUN] git clone $url $repo_dir"
        else
            if ! git clone "$url" "$repo_dir" 2>&1; then
                echo "[ERRO] Falha ao clonar $url"
                echo "| $nome | $empresa | Clone falhou |" >> "$MANUAL_REVIEW"
                (( processed++ )) || true
                continue
            fi
        fi
    fi

    if $DRY_RUN; then
        echo "[DRY-RUN] Pulando extração de dados para $nome"
        (( processed++ )) || true
        continue
    fi

    cd "$repo_dir"

    # ---- Passo 2: Fetch tags e encontrar tag estável ----
    echo "[TAGS] Buscando tags..."
    git fetch --all --tags --quiet 2>/dev/null || true

    # Filtra tags: exclui rc, alpha, beta, M[0-9], SNAPSHOT, dev, preview
    # Ordena por data do commit da tag, pega as antes de CUTOFF_DATE
    best_tag=""
    best_tag_date=""
    best_tag_epoch=0

    while IFS= read -r line; do
        tag_date=$(echo "$line" | cut -d'|' -f1)
        tag_name=$(echo "$line" | cut -d'|' -f2)

        # Ignora tags instáveis (case-insensitive)
        if echo "$tag_name" | grep -qiE '(rc[0-9]?|alpha|beta|\.M[0-9]|SNAPSHOT|dev|preview|incubating)'; then
            continue
        fi

        # Verifica se a data é antes do cutoff
        tag_epoch=$(date -d "$tag_date" +%s 2>/dev/null || echo 0)
        if (( tag_epoch > 0 && tag_epoch < CUTOFF_EPOCH && tag_epoch > best_tag_epoch )); then
            best_tag="$tag_name"
            best_tag_date="$tag_date"
            best_tag_epoch=$tag_epoch
        fi
    done < <(git tag -l --format='%(creatordate:short)|%(refname:short)' 2>/dev/null | sort -t'|' -k1,1)

    if [[ -z "$best_tag" ]]; then
        echo "[WARN] Sem tags estáveis antes de $CUTOFF_DATE para $nome"
        echo "| $nome | $empresa | Sem tags estáveis antes de $CUTOFF_DATE |" >> "$MANUAL_REVIEW"
        notas="Sem tags estáveis — pulado"
        # Grava linha com campos vazios para tag
        echo "$id,$nome,$empresa,$arquetipo,,$url,,,,,,,,,$notas" >> "$CSV_FILE"
        cd "$BASE_DIR"
        (( processed++ )) || true
        continue
    fi

    echo "[TAG] Melhor tag: $best_tag ($best_tag_date)"

    # ---- Passo 3: Checkout e extração ----
    # --force necessário: repos clonados podem ter alterações locais de análises anteriores (ex: sonar)
    git checkout --force "$best_tag" --quiet 2>/dev/null || git checkout --force "$best_tag" 2>/dev/null

    commit_sha=$(git rev-parse HEAD)
    data_commit=$(git log -1 --pretty=format:"%ad" --date=short)
    primeiro_commit=$(set +o pipefail; git log --reverse --pretty=format:"%ad" --date=short | head -1)
    contribuidores=$(set +o pipefail; git shortlog -sn HEAD 2>/dev/null | wc -l | tr -d ' ')

    # Idade em anos (com 1 casa decimal)
    primeiro_epoch=$(date -d "$primeiro_commit" +%s 2>/dev/null || echo 0)
    tag_epoch_for_age=$best_tag_epoch
    if (( primeiro_epoch > 0 && tag_epoch_for_age > 0 )); then
        diff_seconds=$(( tag_epoch_for_age - primeiro_epoch ))
        # anos = dias / 365.25, com 1 casa decimal
        idade_anos=$(echo "scale=1; $diff_seconds / 86400 / 365.25" | bc)
    else
        idade_anos=""
    fi

    # ---- Passo 4: Status ----
    # Determina branch principal
    main_branch=""
    for candidate in origin/main origin/master origin/trunk; do
        if git rev-parse --verify "$candidate" &>/dev/null; then
            main_branch="$candidate"
            break
        fi
    done

    status_projeto=""
    if [[ -n "$main_branch" ]]; then
        last_commit_date=$(git log -1 "$main_branch" --pretty=format:"%ad" --date=short 2>/dev/null)
        last_commit_epoch=$(date -d "$last_commit_date" +%s 2>/dev/null || echo 0)
        diff_months=$(( (TODAY_EPOCH - last_commit_epoch) / 2592000 ))  # ~30 dias

        if (( diff_months < 6 )); then
            status_projeto="ativo"
        elif (( diff_months < 24 )); then
            status_projeto="manutenção"
        else
            status_projeto="arquivado"
        fi
    else
        status_projeto="desconhecido"
        echo "| $nome | $empresa | Branch principal não encontrado |" >> "$MANUAL_REVIEW"
    fi

    # ---- Passo 5: Notas ----
    notas=""
    if [[ "$status_projeto" == "arquivado" ]]; then
        notas="Arquivado desde ~${last_commit_date:-desconhecido}"
    fi
    # Projetos multi-linguagem
    if [[ "$nome" == "protobuf" || "$nome" == "flatbuffers" ]]; then
        if [[ -n "$notas" ]]; then
            notas="$notas; projeto multi-linguagem — verificar pct_java após SonarQube"
        else
            notas="projeto multi-linguagem — verificar pct_java após SonarQube"
        fi
    fi

    # ---- Passo 6: Grava no CSV ----
    # Campos vazios: loc_total, loc_java, pct_java, sonar_status, sonar_project_key
    csv_line="$id,$nome,$empresa,$arquetipo,$status_projeto,$url,$best_tag,$commit_sha,$data_commit,,,,${contribuidores},${idade_anos},,,$notas"
    echo "$csv_line" >> "$CSV_FILE"

    echo "[CSV] Gravado: $id | tag=$best_tag | status=$status_projeto | idade=${idade_anos}a | contrib=$contribuidores"

    # Volta ao diretório base
    cd "$BASE_DIR"
    (( processed++ )) || true
done

echo ""
echo "============================================"
echo "Concluído! Processados: $processed repositórios"
echo "CSV: $CSV_FILE"
echo "Revisão manual: $MANUAL_REVIEW"
echo "============================================"
