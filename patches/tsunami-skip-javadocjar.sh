#!/bin/bash
set -euo pipefail
sed -i 's|        java.withJavadocJar()|        // java.withJavadocJar() — desativado pelo patch (Gradle 8.10 implicit dep validation em :tsunami-proto)|' build.gradle
