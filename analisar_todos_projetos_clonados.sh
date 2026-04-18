#!/bin/bash
set -e

# Carrega variáveis do .env
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

TOKEN="${SONAR_TOKEN}"
URL="${SONAR_URL}"

if [ -z "$TOKEN" ] || [ -z "$URL" ]; then
    echo "ERRO: SONAR_TOKEN e SONAR_URL precisam estar definidos no .env"
    exit 1
fi

# Caminhos absolutos baseados na pasta do script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPOS_DIR="$(realpath "$SCRIPT_DIR/../projetos-clonados")"
PLANILHA="$SCRIPT_DIR/projetos-tcc-dataset.csv"

if [ ! -f "$PLANILHA" ]; then
    echo "ERRO: planilha não encontrada em $PLANILHA"
    exit 1
fi

echo "Iniciando processamento..."
echo "Diretório de repositórios: $REPOS_DIR"

# Usamos o descritor 3 para evitar conflitos com stdin (git/sonar-scanner)
tail -n +2 "$PLANILHA" | while IFS=',' read -u 3 -r id nome empresa arquetipo status url tag commit_sha resto; do
    
    # Limpeza de caracteres indesejados (aspas e retornos de carro de arquivos Windows)
    nome=$(echo "$nome" | tr -d '"\r')
    tag=$(echo "$tag" | tr -d '"\r')
    commit_sha=$(echo "$commit_sha" | tr -d '"\r')

    projeto_dir="$REPOS_DIR/$nome"

    if [ ! -d "$projeto_dir" ]; then
        echo "--------------------------------------------------------"
        echo "AVISO: diretório $projeto_dir não existe, pulando..."
        continue
    fi

    echo "--------------------------------------------------------"
    echo "Analisando: $nome | Tag: $tag | Commit: ${commit_sha:0:7}"
    
    # Entra no diretório, executa e volta (usando parênteses para criar um subshell)
    (
        cd "$projeto_dir"
        
        # Checkout seguro
        git fetch --all --tags --quiet
        git checkout "$tag" --quiet || { echo "ERRO no checkout de $tag"; exit 1; }

        rm -rf .scannerwork
        sha7="${commit_sha:0:7}"

        sonar-scanner \
            -Dsonar.projectKey="$nome" \
            -Dsonar.projectName="$nome" \
            -Dsonar.projectVersion="$tag-$sha7" \
            -Dsonar.sources=. \
            -Dsonar.host.url="$URL" \
            -Dsonar.token="$TOKEN" \
            -Dsonar.scm.disabled=true \
            -Dsonar.qualitygate.wait=false
    )

done 3< <(tail -n +2 "$PLANILHA") # Redireciona o CSV para o descritor 3

echo "========================================================"
echo "Análise concluída com sucesso!"
echo "========================================================"