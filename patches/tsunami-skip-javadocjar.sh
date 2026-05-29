#!/bin/bash
# Patch tsunami-security-scanner: desativa java.withJavadocJar() na config subprojects.
#
# Razão: Gradle 8.10 detecta dependência implícita não-declarada entre
# ':tsunami-proto:generateProto' (protoc) e ':tsunami-proto:javadocJar' e
# falha o build com "implicit_dependency". Desativar withJavadocJar() na
# config global de subprojects elimina a tarefa javadocJar onde ela não é
# necessária — sonar scan precisa de bytecode, não de javadoc jar.
#
# Idempotente: sed s|...| é no-op se o pattern já estiver comentado.
set -euo pipefail
sed -i 's|        java.withJavadocJar()|        // java.withJavadocJar() — desativado pelo patch (Gradle 8.10 implicit dep validation em :tsunami-proto)|' build.gradle
