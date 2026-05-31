#!/bin/bash
cd "$(dirname "${BASH_SOURCE[0]}")"

PROJETOS=(
  google-tsunami-14
  google-google-java-format-15
  google-open-location-code-16
  google-bundletool-17
  google-bindiff-18
  google-copybara-19
  google-firebase-android-sdk-21
  linkedin-dexmaker-04
  uber-autodispose-06
  uber-okbuck-07
  netflix-hystrix-07
  netflix-zuul-08
  netflix-ribbon-09
  netflix-maestro-10
  netflix-genie-12
  google-guice-13
  apache-jmeter-22
  apache-iceberg-24
  apache-rocketmq-16
  apache-seatunnel-23
  apache-skywalking-15
  apache-druid-21
  apache-shardingsphere-17
  apache-doris-19
  google-bazel-12
)

mkdir -p coleta_logs
for PROJ in "${PROJETOS[@]}"; do
  echo "===== $(date '+%Y-%m-%d %H:%M:%S') iniciando $PROJ ====="
  python3 coletar_dados_sonar.py --only "$PROJ" 2>&1 | tee "coleta_logs/${PROJ}.log"
  echo "===== $(date '+%Y-%m-%d %H:%M:%S') concluído $PROJ ====="
  sleep 5
done
echo "===== FIM DE TODOS ====="
