#!/bin/bash
# Patch netflix-genie: dois fixes combinados.
#
# Fix 1 — gradle/gradle-daemon-jvm.properties:
#   Remove a linha 'toolchainVendor=azul' (no HEAD do repo) ou 'toolchainVendor=adoptium'.
#   Razão: Gradle daemon exige vendor exato; o ambiente da coleta usa o JDK
#   apontado por JAVA_HOME (env_com_jdk), sem garantia de vendor específico.
#   Removendo a linha, Gradle aceita qualquer Java 17 disponível.
#
# Fix 2 — genie-ui/build.gradle:
#   Remove 'dependsOn npmInstall' (no task bundle) e 'dependsOn bundle' (no
#   task jar). Razão: npm 5.8.0 baixado pelo plugin nebula.node está quebrado
#   (write after end no registry moderno). Sem essas dependências, o módulo
#   :genie-ui continua produzindo seu jar com as classes Java (consumido por
#   :genie-app via implementation(project(":genie-ui"))), apenas sem o bundle
#   de frontend — irrelevante pro NCLOC Java/SQALE da coleta.
#
# Idempotente: /pattern/d é no-op se o pattern já foi removido.
set -euo pipefail

# Fix 1
sed -i '/^toolchainVendor=/d' gradle/gradle-daemon-jvm.properties

# Fix 2
sed -i '/^    dependsOn npmInstall$/d' genie-ui/build.gradle
sed -i '/^    dependsOn bundle$/d' genie-ui/build.gradle
