#!/bin/bash
cd "$(dirname "${BASH_SOURCE[0]}")"

PROJETOS=(
  google-java-docs-samples-16
  apache-shenyu-19
  apache-incubator-seata-18
  google-dataflow-templates-21
)

mkdir -p coleta_logs_v19
for PROJ in "${PROJETOS[@]}"; do
  echo "===== $(date '+%Y-%m-%d %H:%M:%S') iniciando $PROJ ====="
  python3 coletar_dados_sonar.py --only "$PROJ" 2>&1 | tee "coleta_logs_v19/${PROJ}.log"
  echo "===== $(date '+%Y-%m-%d %H:%M:%S') concluído $PROJ ====="
  sleep 5
done
echo "===== FIM BLOCO 1 ====="
