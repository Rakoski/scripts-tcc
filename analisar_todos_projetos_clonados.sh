#!/bin/bash
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

TOKEN="${SONAR_TOKEN}"
URL="${SONAR_URL}"
REPOS_DIR="../projetos-clonados"

DONE=("kafka" "cassandra" "archaius" "auto")

for dir in */; do
    project=${dir%/}
    
    if [[ "$project" == "sonarqube-docker" || " ${DONE[@]} " =~ " ${project} " ]]; then
        continue
    fi

    echo "========================================================"
    echo "Análise Estática Pura: $project"
    echo "========================================================"
    
    cd "$project"

    sonar-scanner \
      -Dsonar.projectKey="$project" \
      -Dsonar.projectName="$project" \
      -Dsonar.sources=. \
      -Dsonar.host.url=$URL \
      -Dsonar.token=$TOKEN \
      -Dsonar.java.binaries=. \
      -Dsonar.java.source=1.8 \
      -Dsonar.scm.disabled=true \
      -Dsonar.compiler.skip=true

    cd ..
done