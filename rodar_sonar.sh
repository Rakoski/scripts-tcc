#!/bin/bash
set -euo pipefail

SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPTS_DIR")"
CLONE_DIR="$BASE_DIR"
CSV_FILE="$SCRIPTS_DIR"
SONAR_URL="${SONAR_URL}"
SONAR_TOKEN="${SONAR_TOKEN}"
SCANNER="$BASE_DIR/sonarqube-docker/sonar-scanner-5.0.1.3006-linux/bin/sonar-scanner"
INIT_GRADLE="$SCRIPTS_DIR/sonar_init.gradle"
LOG_DIR="$SCRIPTS_DIR/sonar-logs"

mkdir -p "$LOG_DIR"

LIMIT=0
ONLY=""
SKIP_EXISTING=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --limit)         LIMIT="$2"; shift 2 ;;
        --only)          ONLY="$2"; shift 2 ;;
        --skip-existing) SKIP_EXISTING=true; shift ;;
        *)               echo "Argumento desconhecido: $1"; exit 1 ;;
    esac
done

if ! curl -sf "$SONAR_URL/api/system/status" -u "$SONAR_TOKEN:" > /dev/null 2>&1; then
    echo "[ERRO] SonarQube não está acessível em $SONAR_URL"
    exit 1
fi
echo "[OK] SonarQube acessível em $SONAR_URL"

detect_build_type() {
    local dir="$1"
    if [[ -f "$dir/pom.xml" ]]; then
        echo "maven"
    elif [[ -f "$dir/build.gradle" || -f "$dir/build.gradle.kts" ]]; then
        echo "gradle"
    elif [[ -f "$dir/build.xml" ]]; then
        echo "ant"
    else
        echo "scanner"
    fi
}

find_java_sources() {
    local dir="$1"
    local sources=()
    
    while IFS= read -r src_dir; do
        
        [[ "$src_dir" == *"/build/"* || "$src_dir" == *"/target/"* ]] && continue
        [[ "$src_dir" == *"/examples/"* || "$src_dir" == *"/example/"* ]] && continue
        [[ "$src_dir" == *"/samples/"* || "$src_dir" == *"/sample/"* ]] && continue
        [[ "$src_dir" == *"/test/data/"* || "$src_dir" == *"/testdata/"* ]] && continue
        sources+=("$src_dir")
    done < <(find "$dir" -type d \( \
            -path "*/src/main/java" \
            -o -path "*/src/java" \
            -o -path "*/main/java" \
        \) 2>/dev/null | head -500)

    if [[ ${
        printf '%s,' "${sources[@]}" | sed 's/,$//'
    else
        
        echo "$dir"
    fi
}

find_java_binaries() {
    local dir="$1"
    local bins=()
    
    while IFS= read -r bin_dir; do
        bins+=("$bin_dir")
    done < <(find "$dir" -type d \( \
            -path "*/target/classes" \
            -o -path "*/build/classes/java/main" \
            -o -path "*/build/classes/java" \
            -o -path "*/build/classes" \
            -o -path "*/out/production/classes" \
        \) 2>/dev/null | head -500)

    if [[ ${
        printf '%s,' "${bins[@]}" | sed 's/,$//'
    else
        echo ""
    fi
}

project_exists_in_sonar() {
    local key="$1"
    local http_code
    http_code=$(curl -s -o /dev/null -w "%{http_code}" \
        -u "$SONAR_TOKEN:" \
        "$SONAR_URL/api/measures/component?component=$key&metricKeys=ncloc" 2>/dev/null)
    [[ "$http_code" == "200" ]]
}

run_scanner() {
    local project_key="$1"
    local project_name="$2"
    local project_dir="$3"
    local log_file="$LOG_DIR/${project_key}.log"

    local sources
    sources=$(find_java_sources "$project_dir")
    local binaries
    binaries=$(find_java_binaries "$project_dir")

    if [[ -z "$binaries" ]]; then
        local empty_bin="$LOG_DIR/_empty_bin_${project_key}"
        mkdir -p "$empty_bin"
        binaries="$empty_bin"
        echo "[WARN] Nenhum binário encontrado — usando diretório vazio (análise degradada)"
    fi

    local scanner_args=(
        -Dsonar.projectKey="$project_key"
        -Dsonar.projectName="$project_name"
        -Dsonar.host.url="$SONAR_URL"
        -Dsonar.token="$SONAR_TOKEN"
        -Dsonar.sources="$sources"
        -Dsonar.java.binaries="$binaries"
        -Dsonar.language=java
        -Dsonar.java.source=21
        -Dsonar.sourceEncoding=UTF-8
        -Dsonar.scm.disabled=true
        -Dsonar.projectBaseDir="$project_dir"
        -Dsonar.exclusions=**/build/**,**/target/**,**/out/**,**/buildSrc/**,**/examples/**,**/example/**,**/samples/**,**/sample/**,**/test/data/**,**/testdata/**,**/.git/**,**/node_modules/**
    )

    export SONAR_SCANNER_OPTS="-Xss64m -Xmx4g"

    echo "[SCANNER] Rodando sonar-scanner para $project_key..."
    if "$SCANNER" "${scanner_args[@]}" < /dev/null > "$log_file" 2>&1; then
        echo "[OK] Análise concluída: $project_key"
        return 0
    else
        echo "[ERRO] Falha na análise: $project_key (log: $log_file)"
        tail -5 "$log_file"
        return 1
    fi
}

run_maven() {
    local project_key="$1"
    local project_name="$2"
    local project_dir="$3"
    local log_file="$LOG_DIR/${project_key}.log"
    local build_log="$LOG_DIR/${project_key}.build.log"

    echo "[MAVEN] Rodando mvn package + sonar:sonar para $project_key..."
    cd "$project_dir"

    if mvn package -DskipTests \
            -Dmaven.javadoc.skip=true \
            -Dcheckstyle.skip=true \
            -Dspotless.check.skip=true \
            -Dspotless.apply.skip=true \
            -Drat.skip=true \
            -Denforcer.skip=true \
            < /dev/null > "$build_log" 2>&1; then
        if mvn sonar:sonar \
            -Dsonar.projectKey="$project_key" \
            -Dsonar.projectName="$project_name" \
            -Dsonar.host.url="$SONAR_URL" \
            -Dsonar.token="$SONAR_TOKEN" \
            -Dsonar.scm.disabled=true \
            -DskipTests \
            < /dev/null > "$log_file" 2>&1; then
            echo "[OK] Maven análise concluída: $project_key"
            cd "$BASE_DIR"
            return 0
        fi
    fi

    echo "[WARN] Maven falhou (ver $build_log), tentando scanner standalone para $project_key"
    cd "$BASE_DIR"
    run_scanner "$project_key" "$project_name" "$project_dir"
}

run_gradle() {
    local project_key="$1"
    local project_name="$2"
    local project_dir="$3"
    local log_file="$LOG_DIR/${project_key}.log"
    local build_log="$LOG_DIR/${project_key}.build.log"

    echo "[GRADLE] Rodando gradle assemble + sonar para $project_key..."
    cd "$project_dir"

    local gradle_cmd="./gradlew"
    if [[ ! -x "$gradle_cmd" ]]; then
        gradle_cmd="gradle"
    fi

    if "$gradle_cmd" assemble -x test -x javadoc --no-daemon --warning-mode none \
            < /dev/null > "$build_log" 2>&1; then
        if "$gradle_cmd" sonar \
            --init-script "$INIT_GRADLE" \
            -Dsonar.projectKey="$project_key" \
            -Dsonar.projectName="$project_name" \
            -Dsonar.host.url="$SONAR_URL" \
            -Dsonar.token="$SONAR_TOKEN" \
            -Dsonar.scm.disabled=true \
            --no-daemon < /dev/null > "$log_file" 2>&1; then
            echo "[OK] Gradle análise concluída: $project_key"
            cd "$BASE_DIR"
            return 0
        fi
    fi

    echo "[WARN] Gradle falhou (ver $build_log), tentando scanner standalone para $project_key"
    cd "$BASE_DIR"
    run_scanner "$project_key" "$project_name" "$project_dir"
}

processed=0
success=0
failed=0

while IFS=, read -r id nome empresa arquetipo status url tag commit_sha rest; do
    
    if [[ -z "$tag" ]]; then
        echo "[SKIP] $nome — sem tag"
        continue
    fi

    if [[ -n "$ONLY" && "$nome" != "$ONLY" ]]; then
        continue
    fi

    if (( LIMIT > 0 && processed >= LIMIT )); then
        break
    fi

    project_key="$id"
    repo_dir="$CLONE_DIR/$nome"

    processed=$(( processed + 1 ))

    echo ""
    echo "============================================"
    echo "[$processed] $empresa/$nome → $project_key"
    echo "============================================"

    if [[ ! -d "$repo_dir/.git" ]]; then
        echo "[ERRO] Repo não encontrado: $repo_dir"
        failed=$(( failed + 1 ))
        continue
    fi

    if $SKIP_EXISTING && project_exists_in_sonar "$project_key"; then
        echo "[SKIP] $project_key já existe no SonarQube"
        continue
    fi

    cd "$repo_dir"
    if ! git checkout --force "$tag" --quiet 2>/dev/null; then
        echo "[ERRO] Falha no checkout da tag $tag para $nome"
        cd "$BASE_DIR"
        failed=$(( failed + 1 ))
        continue
    fi
    cd "$BASE_DIR"

    build_type=$(detect_build_type "$repo_dir")
    echo "[BUILD] Tipo detectado: $build_type"

    case "$build_type" in
        maven)  run_maven  "$project_key" "$nome" "$repo_dir" && success=$(( success + 1 )) || failed=$(( failed + 1 )) ;;
        gradle) run_gradle "$project_key" "$nome" "$repo_dir" && success=$(( success + 1 )) || failed=$(( failed + 1 )) ;;
        *)      run_scanner "$project_key" "$nome" "$repo_dir" && success=$(( success + 1 )) || failed=$(( failed + 1 )) ;;
    esac

    sleep 2
done < <(tail -n+2 "$CSV_FILE")

echo ""
echo "============================================"
echo "SonarQube — Análise concluída"
echo "  Processados: $processed"
echo "  Sucesso:     $success"
echo "  Falha:       $failed"
echo "  Logs:        $LOG_DIR/"
echo "============================================"
