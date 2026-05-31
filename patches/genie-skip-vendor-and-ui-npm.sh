#!/bin/bash
set -euo pipefail

sed -i '/^toolchainVendor=/d' gradle/gradle-daemon-jvm.properties

sed -i '/^    dependsOn npmInstall$/d' genie-ui/build.gradle
sed -i '/^    dependsOn bundle$/d' genie-ui/build.gradle
