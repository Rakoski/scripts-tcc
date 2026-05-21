#!/bin/bash
# Patch cadence-java-client v3.12.4: força libthrift Java 0.13.0 (era 0.9.3)
# Razão: compiler Thrift 0.13 gera código com @org.apache.thrift.annotation.Nullable
# que não existe em libthrift 0.9.3 — conflito de versão entre compiler e runtime.
sed -i "s/version: '0.9.3'/version: '0.13.0'/" build.gradle
