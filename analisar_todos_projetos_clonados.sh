#!/bin/bash
set -e  # sai em caso de erro

# Carrega variáveis
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi
TOKEN="${SONAR_TOKEN}"
URL="${SONAR_URL}"

if [ -z "$TOKEN" ] || [ -z "$URL" ]; then
    echo "ERRO: SONAR_TOKEN e SONAR_URL precisam estar definidos"
    exit 1
fi

# Diretório absoluto dos repositórios
REPOS_DIR="$(realpath ../projetos-clonados)"
PLANILHA="$(realpath ../dados/projetos-tcc-dataset.csv)"

if [ ! -f "$PLANILHA" ]; then
    echo "ERRO: planilha não encontrada em $PLANILHA"
    exit 1
fi

# Lê cada linha da planilha (pula cabeçalho)
tail -n +2 "$PLANILHA" | while IFS=',' read -r id nome empresa arquetipo status url tag commit_sha resto; do
    # Remove aspas se existirem
    nome=$(echo "$nome" | tr -d '"')
    tag=$(echo "$tag" | tr -d '"')
    commit_sha=$(echo "$commit_sha" | tr -d '"')

    projeto_dir="$REPOS_DIR/$nome"

    if [ ! -d "$projeto_dir" ]; then
        echo "AVISO: diretório $projeto_dir não existe, pulando"
        continue
    fi

    echo "========================================================"
    echo "Analisando: $nome @ $tag ($commit_sha)"
    echo "========================================================"

    cd "$projeto_dir"

    # Fixa o commit
    git fetch --all --tags --quiet
    git checkout "$tag" --quiet || {
        echo "ERRO: checkout de $tag falhou em $nome"
        continue
    }

    # Limpa cache do scanner anterior
    rm -rf .scannerwork

    sha7="${commit_sha:0:7}"

    sonar-scanner \
        -Dsonar.projectKey="$nome" \
        -Dsonar.projectName="$nome" \
        -Dsonar.projectVersion="$tag-$sha7" \
        -Dsonar.sources=. \
        -Dsonar.host.url="$URL" \
        -Dsonar.token="$TOKEN" \
        -Dsonar.scm.disabled=true
done

echo "========================================================"
echo "Todas as análises concluídas"
echo "========================================================"