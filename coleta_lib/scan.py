from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

from .io_utils import ColetaError, ProjetoError, SonarClient

JDK_FALLBACK_ORDER: list[int] = [21, 17, 11, 8]

JDK_FALLBACKS: dict[int, str] = {
    8:  "/usr/lib/jvm/temurin-8-jdk-amd64",
    11: "/usr/lib/jvm/temurin-11-jdk-amd64",
    17: "/usr/lib/jvm/java-17-openjdk-amd64",
    21: "/usr/lib/jvm/temurin-21-jdk-amd64",
}

def _primeiro_jdk_disponivel() -> str:
    for v in JDK_FALLBACK_ORDER:
        p = jdk_path_para(v)
        if p:
            return p
    raise ColetaError("Nenhum JDK encontrado em /usr/lib/jvm")

EXCLUSIONS = (
    "**/build/**,**/target/**,**/out/**,**/buildSrc/**,"
    "**/examples/**,**/example/**,**/samples/**,**/sample/**,"
    "**/test/data/**,**/testdata/**,**/.git/**,**/node_modules/**"
)

STANDALONE_EXCLUSIONS = (
    "**/test/**,**/tests/**,**/build/**,**/target/**,**/out/**,**/buildSrc/**,"
    "**/examples/**,**/example/**,**/samples/**,**/sample/**,"
    "**/.git/**,**/node_modules/**"
)

GRADLE_INIT_SCRIPT = "sonar_init.gradle"

BINARY_PATTERNS = [
    "**/target/classes",
    "**/build/classes/java/main",
    "**/build/classes/main",
    "**/build/classes",
    "**/out/production/classes",
    "**/output/classes",
]

ANT_OUTPUT_DEFAULTS = {
    "cassandra": "build/classes/main",
    "tomcat":    "output/classes",
}

ANT_BUILD_PIPELINE: dict[str, list[list[str]]] = {
    "cassandra": [["build"]],
    "tomcat":    [["download-compile"], ["deploy"]],
}

ANT_BUILD_DIRS_TO_CLEAN: dict[str, list[str]] = {
    "apache-cassandra-04": ["build"],
    "apache-tomcat-01":    ["output"],
}

SOURCE_PATHS_PROJETOS: dict[str, list[str]] = {
    "apache-cassandra-04": ["src/java"],
    "apache-tomcat-01":    ["java"],
}

BAZEL_TARGETS_OVERRIDE: dict[str, list[str]] = {
    "google-j2cl-18": ["//transpiler/java/..."],
}

BAZEL_SOURCE_HINTS: dict[str, list[str]] = {
    "google-j2cl-18": [
        "transpiler/java",
        "tools/java",
        "junit/generator/java",
        "junit/emul/java",
        "benchmarking/java",
    ],
}

PATCHES_POST_CHECKOUT: dict[str, str] = {
    "uber-cadence-java-client-05": "cadence-libthrift.sh",
    "google-tsunami-14": "tsunami-skip-javadocjar.sh",
    "netflix-genie-12": "genie-skip-vendor-and-ui-npm.sh",
}

def _run(cmd: list[str], cwd: Path, env: dict, log_path: Path,
         timeout: int = 2400) -> int:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(f"\n$ {' '.join(cmd)}\n\n")
        try:
            r = subprocess.run(
                cmd, cwd=str(cwd), env=env, stdin=subprocess.DEVNULL,
                stdout=f, stderr=subprocess.STDOUT, timeout=timeout,
            )
            return r.returncode
        except subprocess.TimeoutExpired:
            f.write(f"\n[TIMEOUT após {timeout}s]\n")
            return 124

def detectar_build(repo: Path) -> tuple[str, str | None]:
    for special in ("build-pom.xml", "parent-pom.xml"):
        if (repo / special).exists():
            return "maven", special
    if (repo / "pom.xml").exists():
        return "maven", None
    for marker in ("build.gradle", "build.gradle.kts",
                   "settings.gradle", "settings.gradle.kts"):
        if (repo / marker).exists():
            return "gradle", None
    for marker in ("MODULE.bazel", "WORKSPACE", "WORKSPACE.bazel"):
        if (repo / marker).exists():
            return "bazel", None
    for build_marker in ("BUILD", "BUILD.bazel"):
        if (repo / build_marker).exists():
            return "bazel", None
    if (repo / "build.xml").exists():
        return "ant", None
    return "scanner", None

def detectar_jdk_declarado(repo: Path) -> int | None:
    pom = repo / "pom.xml"
    if pom.exists():
        try:
            content = pom.read_text(encoding="utf-8", errors="replace")
        except Exception:
            content = ""
        for tag in ("maven.compiler.source", "java.version",
                    "maven.compiler.release", "source"):
            m = re.search(rf"<{tag}>([\d.]+)</{tag}>", content)
            if m:
                v = m.group(1).split(".")[-1] if m.group(1).startswith("1.") else m.group(1).split(".")[0]
                try:
                    return int(v)
                except ValueError:
                    pass
    gradle = repo / "build.gradle"
    if not gradle.exists():
        gradle = repo / "build.gradle.kts"
    if gradle.exists():
        try:
            content = gradle.read_text(encoding="utf-8", errors="replace")
        except Exception:
            content = ""
        m = re.search(r"sourceCompatibility\s*=?\s*['\"]?(?:JavaVersion\.VERSION_)?(\d+(?:\.\d+)?)['\"]?",
                      content)
        if m:
            v = m.group(1)
            v = v.split(".")[-1] if v.startswith("1.") else v.split(".")[0]
            try:
                return int(v)
            except ValueError:
                pass
    return None

def jdk_path_para(versao: int | None) -> str | None:
    if versao is None:
        return None
    cand = JDK_FALLBACKS.get(versao)
    if cand and Path(cand).is_dir() and (Path(cand) / "bin" / "java").exists():
        return cand
    return None

def env_com_jdk(jdk_home: str) -> dict:
    env = os.environ.copy()
    env["JAVA_HOME"] = jdk_home
    env["PATH"] = f"{jdk_home}/bin:" + env.get("PATH", "")
    env.setdefault("SONAR_SCANNER_OPTS", "-Xss64m -Xmx4g")
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GIT_SSH_COMMAND"] = "ssh -o BatchMode=yes -o StrictHostKeyChecking=no"
    env["GRADLE_OPTS"] = (env.get("GRADLE_OPTS", "")
                          + " -Dorg.gradle.console=plain").strip()
    return env

def find_java_binaries(repo: Path) -> str:
    found: list[str] = []
    for pat in BINARY_PATTERNS:
        for d in repo.glob(pat):
            if d.is_dir() and any(d.rglob("*.class")):
                found.append(str(d.resolve()))
    return ",".join(found)

def find_main_sources(repo: Path, project_key: str | None = None) -> str:
    found: list[str] = []
    override = SOURCE_PATHS_PROJETOS.get(project_key) if project_key else None
    if override:
        for rel in override:
            d = repo / rel
            if d.is_dir() and any(d.rglob("*.java")):
                found.append(str(d.resolve()))
    else:
        for sub in ("java", "kotlin"):
            for d in repo.glob(f"**/src/main/{sub}"):
                if d.is_dir():
                    found.append(str(d.resolve()))
    return ",".join(found)

def find_bazel_sources(repo: Path, project_key: str | None = None) -> str:
    found: list[str] = []
    hints = BAZEL_SOURCE_HINTS.get(project_key) if project_key else None
    if hints:
        for rel in hints:
            d = repo / rel
            if d.is_dir() and any(d.rglob("*.java")):
                found.append(str(d.resolve()))
        if found:
            return ",".join(found)

    maven_like = find_main_sources(repo, project_key=project_key)
    if maven_like:
        return maven_like

    EXCLUDED = {"bazel-bin", "bazel-out", "bazel-testlogs", "external",
                "third_party", "javatests", "test", "tests", "node_modules",
                ".git"}
    EXCLUDED_PREFIXES = ("bazel-",)

    def is_excluded(path: Path) -> bool:
        rel = path.relative_to(repo)
        for part in rel.parts:
            if part in EXCLUDED:
                return True
            if any(part.startswith(p) for p in EXCLUDED_PREFIXES):
                return True
            if "javatests" in part or part.endswith("_test"):
                return True
        return False

    cand = repo / "java"
    if cand.is_dir() and not is_excluded(cand) and any(cand.rglob("*.java")):
        found.append(str(cand.resolve()))

    for sub in repo.iterdir():
        if not sub.is_dir():
            continue
        if is_excluded(sub):
            continue
        cand = sub / "java"
        if cand.is_dir() and not is_excluded(cand) and any(cand.rglob("*.java")):
            found.append(str(cand.resolve()))

    return ",".join(found)

SNAPSHOT_TYPE_RELEASE_TAG = "release-tag-pre-2026"
SNAPSHOT_TYPE_HEAD = "head-of-main"
SNAPSHOT_TYPES_VALIDOS = {SNAPSHOT_TYPE_RELEASE_TAG, SNAPSHOT_TYPE_HEAD}

def git_checkout(repo: Path, tag: str, logger: logging.Logger,
                 snapshot_type: str = SNAPSHOT_TYPE_RELEASE_TAG,
                 branch_principal: str | None = None) -> str:
    if not (repo / ".git").exists():
        raise ColetaError(f"Repo não inicializado: {repo}")

    if snapshot_type not in SNAPSHOT_TYPES_VALIDOS:
        raise ColetaError(
            f"snapshot_type inválido: {snapshot_type!r} (esperado: "
            f"{sorted(SNAPSHOT_TYPES_VALIDOS)}) — ver protocolo v1.7 §A10/A13"
        )

    if snapshot_type == SNAPSHOT_TYPE_RELEASE_TAG:
        if not tag:
            raise ColetaError(
                f"snapshot_type=release-tag-pre-2026 requer tag para {repo} "
                f"(protocolo v1.5 §4.4)"
            )
        subprocess.run(["git", "fetch", "--all", "--tags", "--quiet"],
                       cwd=str(repo), check=False)
        r = subprocess.run(["git", "checkout", "--force", tag, "--quiet"],
                           cwd=str(repo))
        if r.returncode != 0:
            raise ColetaError(f"git checkout {tag} falhou em {repo}")
        rotulo = tag
    else:
        if not branch_principal:
            raise ColetaError(
                f"snapshot_type=head-of-main requer branch_principal para {repo} "
                f"(protocolo v1.7 §A10.4/A12)"
            )
        subprocess.run(
            ["git", "fetch", "origin", branch_principal, "--quiet"],
            cwd=str(repo), check=False,
        )
        ref = f"origin/{branch_principal}"
        r = subprocess.run(["git", "checkout", "--force", ref, "--quiet"],
                           cwd=str(repo))
        if r.returncode != 0:
            raise ColetaError(f"git checkout {ref} falhou em {repo}")
        rotulo = tag or f"HEAD-on-{branch_principal}"

    sha_full = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(repo),
                              capture_output=True, text=True).stdout.strip()
    sha7 = sha_full[:7]
    logger.info("git checkout %s (sha=%s) em %s", rotulo, sha7, repo.name)
    return sha7

def detectar_branch_principal(repo: Path, logger: logging.Logger) -> str:
    if not (repo / ".git").exists():
        raise ColetaError(f"Repo não inicializado: {repo}")

    r = subprocess.run(
        ["git", "symbolic-ref", "--short", "refs/remotes/origin/HEAD"],
        cwd=str(repo), capture_output=True, text=True,
    )
    if r.returncode == 0:
        ref = r.stdout.strip()
        if ref.startswith("origin/"):
            nome = ref[len("origin/"):]
            if nome:
                logger.info("branch_principal de %s: %s (via symbolic-ref)",
                            repo.name, nome)
                return nome

    for cand in ("main", "master"):
        rc = subprocess.run(
            ["git", "show-ref", "--verify", "--quiet",
             f"refs/remotes/origin/{cand}"],
            cwd=str(repo),
        ).returncode
        if rc == 0:
            logger.info("branch_principal de %s: %s (fallback show-ref)",
                        repo.name, cand)
            return cand

    raise ColetaError(
        f"branch_principal indeterminado para {repo} — nenhum de "
        f"origin/main, origin/master encontrado (protocolo v1.7 §A12)"
    )

def limpar_scannerwork(repo: Path) -> None:
    sw = repo / ".scannerwork"
    if sw.exists():
        shutil.rmtree(sw, ignore_errors=True)

def aplicar_patch_post_checkout(project_key: str, repo: Path,
                                base_dir: Path,
                                logger: logging.Logger) -> None:
    nome = PATCHES_POST_CHECKOUT.get(project_key)
    if not nome:
        return
    patch_script = base_dir / "scripts-tcc" / "patches" / nome
    if not patch_script.exists():
        raise ProjetoError(
            f"[{project_key}] patch script ausente: {patch_script}"
        )
    logger.info("[%s] aplicando patch: %s", project_key, nome)
    try:
        subprocess.run([str(patch_script)], cwd=str(repo), check=True)
    except subprocess.CalledProcessError as e:
        raise ProjetoError(
            f"[{project_key}] patch {nome} falhou (rc={e.returncode})"
        ) from e
    logger.info("[%s] patch aplicado", project_key)

def _sonar_props(project_key: str, project_name: str, tag: str, sha7: str,
                 sonar_url: str, sonar_token: str) -> list[str]:
    return [
        f"-Dsonar.projectKey={project_key}",
        f"-Dsonar.projectName={project_name}",
        f"-Dsonar.projectVersion={tag}-{sha7}",
        f"-Dsonar.host.url={sonar_url}",
        f"-Dsonar.token={sonar_token}",
        "-Dsonar.scm.disabled=true",
        "-Dsonar.qualitygate.wait=false",
        f"-Dsonar.exclusions={EXCLUSIONS}",
    ]

def _maven_completo(repo: Path, props: list[str], env: dict,
                    log_path: Path, pom_filename: str | None = None) -> int:
    cmd = ["mvn"]
    if pom_filename:
        cmd += ["-f", pom_filename]
    cmd += [
        "package", "sonar:sonar",
        "-DskipTests", "-fae",
        "-Dmaven.javadoc.skip=true",
        "-Dcheckstyle.skip=true",
        "-Dspotless.check.skip=true", "-Dspotless.apply.skip=true",
        "-Drat.skip=true", "-Denforcer.skip=true",
        *props,
    ]
    return _run(cmd, repo, env, log_path)

def _resolver_init_gradle(base_dir: Path) -> Path:
    caminho = base_dir / "scripts-tcc" / GRADLE_INIT_SCRIPT
    if not caminho.exists():
        raise ColetaError(f"init-script Gradle ausente: {caminho}")
    return caminho

def _gradle_completo(repo: Path, props: list[str], env: dict,
                     log_path: Path, init_script: Path) -> int:
    grad = repo / "gradlew"
    base = [str(grad)] if grad.exists() and os.access(grad, os.X_OK) else ["gradle"]
    cmd = [
        *base, "assemble", "sonar",
        "--init-script", str(init_script),
        "--no-daemon", "--warning-mode", "none",
        "-x", "test", "-x", "javadoc",
        *props,
    ]
    return _run(cmd, repo, env, log_path, timeout=480)

def _gradle_assemble_only(repo: Path, env: dict, log_path: Path) -> int:
    grad = repo / "gradlew"
    base = [str(grad)] if grad.exists() and os.access(grad, os.X_OK) else ["gradle"]
    cmd = [
        *base, "assemble",
        "--no-daemon", "--warning-mode", "none",
        "-x", "test", "-x", "javadoc",
    ]
    return _run(cmd, repo, env, log_path, timeout=480)

def _bazel_completo(repo: Path, props: list[str], env: dict,
                    scanner_bin: Path, log_path: Path,
                    logger: logging.Logger, project_key: str) -> int:
    targets = BAZEL_TARGETS_OVERRIDE.get(project_key, ["//..."])

    cmd_build = [
        "bazelisk", "build", *targets,
        "--noshow_progress",
        "--keep_going",
    ]
    logger.info("[%s] bazelisk build target(s): %s",
                project_key, " ".join(targets))
    rc_build = _run(cmd_build, repo, env, log_path, timeout=1800)
    if rc_build != 0:
        logger.warning("[%s] bazelisk build falhou (rc=%d) — usando JARs "
                       "parciais se houver", project_key, rc_build)

    bazel_bin = repo / "bazel-bin"
    if not bazel_bin.exists():
        logger.error("[%s] bazel-bin não existe — build falhou completamente",
                     project_key)
        return rc_build or 1

    jars = []
    TEST_PATH_PARTS = {"javatests", "tests", "test"}
    skipped_test = 0
    skipped_stale = 0
    for jar in bazel_bin.rglob("*.jar"):
        name = jar.name
        if name.endswith("-src.jar") or name.endswith("-hjar.jar"):
            continue
        if "header" in name or "source" in name:
            continue
        if any(p in TEST_PATH_PARTS for p in jar.parts):
            skipped_test += 1
            continue
        resolved = jar.resolve()
        if not resolved.exists():
            skipped_stale += 1
            continue
        jars.append(str(resolved))
    if skipped_test or skipped_stale:
        logger.info("[%s] filtrados: %d test JARs, %d symlinks stale",
                    project_key, skipped_test, skipped_stale)

    if not jars:
        logger.error("[%s] nenhum JAR utilizável em bazel-bin/", project_key)
        return 1

    logger.info("[%s] Bazel build OK: %d JARs em bazel-bin/",
                project_key, len(jars))
    binaries = ",".join(jars)

    bazel_sources = find_bazel_sources(repo, project_key=project_key)
    extra = [f"-Dsonar.projectBaseDir={repo}"]

    if bazel_sources:
        extra.append(f"-Dsonar.sources={bazel_sources}")
        excl = STANDALONE_EXCLUSIONS
        n_dirs = bazel_sources.count(",") + 1
        logger.info("[%s] Bazel: %d source dir(s) detectado(s)",
                    project_key, n_dirs)
    else:
        logger.error("[%s] Bazel: nenhum source dir detectado — "
                     "ABORTANDO scan (sources=. contaminaria com deps)",
                     project_key)
        return 1

    extra.append(f"-Dsonar.exclusions={excl}")

    props_file = repo / "sonar-project.properties"
    backup = (props_file.read_text(encoding="utf-8")
              if props_file.exists() else None)
    try:
        props_file.write_text(
            f"sonar.java.binaries={binaries}\n",
            encoding="utf-8",
        )
        return _run([str(scanner_bin), *props, *extra], repo, env, log_path)
    finally:
        if backup is not None:
            props_file.write_text(backup, encoding="utf-8")
        else:
            props_file.unlink(missing_ok=True)

def _limpar_build_dirs_ant(repo: Path, project_key: str,
                           logger: logging.Logger) -> None:
    dirs = ANT_BUILD_DIRS_TO_CLEAN.get(project_key, ["build"])
    logger.info("[%s] limpando %s antes do ant",
                project_key, ", ".join(f"{d}/" for d in dirs))
    for d in dirs:
        shutil.rmtree(repo / d, ignore_errors=True)

def _ant_completo(repo: Path, props: list[str], scanner_bin: Path,
                  log_path: Path, logger: logging.Logger,
                  project_key: str) -> tuple[int, int | None]:
    nome_repo = repo.name
    pipeline = ANT_BUILD_PIPELINE.get(nome_repo, [["build"]])

    for v in JDK_FALLBACK_ORDER:
        jpath = jdk_path_para(v)
        if not jpath:
            logger.info("[%s] JDK %d não instalado, pulando", project_key, v)
            continue
        logger.info("[%s] tentando JDK %d em %s", project_key, v, jpath)
        env = env_com_jdk(jpath)

        _limpar_build_dirs_ant(repo, project_key, logger)

        ant_ok = True
        for step in pipeline:
            passo = " ".join(step) or "(default)"
            rc_build = _run(["ant", *step], repo, env, log_path)
            if rc_build == 0:
                logger.info("[%s] ant %s OK com JDK %d",
                            project_key, passo, v)
            else:
                logger.warning("[%s] ant %s rc=%d com JDK %d (continuando)",
                               project_key, passo, rc_build, v)
                ant_ok = False
                break
        if not ant_ok:
            continue

        binaries = ""
        default_rel = ANT_OUTPUT_DEFAULTS.get(nome_repo)
        if default_rel:
            candidato = repo / default_rel
            if candidato.is_dir() and any(candidato.rglob("*.class")):
                binaries = str(candidato.resolve())
                logger.info("[%s] Ant: binários em %s (mapeamento default)",
                            project_key, default_rel)
        if not binaries:
            binaries = find_java_binaries(repo)
            if binaries:
                logger.info("[%s] Ant: %d dirs de binários via glob",
                            project_key, binaries.count(",") + 1)

        main_sources = find_main_sources(repo, project_key=project_key)
        extra: list[str] = [f"-Dsonar.projectBaseDir={repo}"]
        if main_sources:
            extra.append(f"-Dsonar.sources={main_sources}")
            excl = STANDALONE_EXCLUSIONS
            logger.info("[%s] Ant: %d src/main dir(s) detectado(s)",
                        project_key, main_sources.count(",") + 1)
        else:
            extra.append("-Dsonar.sources=.")
            excl = EXCLUSIONS
            logger.info("[%s] Ant: sem src/main padrão, fallback sonar.sources=.",
                        project_key)

        if binaries:
            extra.append(f"-Dsonar.java.binaries={binaries}")
        else:
            excl = f"{excl},**/*.java"
            logger.warning("[%s] Ant SEM binários — Java EXCLUÍDO da análise (degradado)",
                           project_key)

        extra.append(f"-Dsonar.exclusions={excl}")
        rc_scan = _run([str(scanner_bin), *props, *extra], repo, env, log_path)
        return rc_scan, v

    logger.error("[%s] ant falhou em todos os JDKs do fallback — não rodando scanner com binários antigos",
                 project_key)
    return 1, None

def _scanner_standalone(repo: Path, props: list[str], env: dict,
                        scanner_bin: Path, log_path: Path,
                        logger: logging.Logger,
                        project_key: str) -> int:
    binaries = find_java_binaries(repo)
    main_sources = find_main_sources(repo, project_key=project_key)

    extra: list[str] = [f"-Dsonar.projectBaseDir={repo}"]
    if main_sources:
        extra.append(f"-Dsonar.sources={main_sources}")
        excl = STANDALONE_EXCLUSIONS
        logger.info("[%s] standalone: %d src/main dir(s) detectado(s)",
                    project_key, main_sources.count(",") + 1)
    else:
        extra.append("-Dsonar.sources=.")
        excl = EXCLUSIONS
        logger.info("[%s] standalone: sem src/main padrão, fallback sonar.sources=.",
                    project_key)

    if binaries:
        extra.append(f"-Dsonar.java.binaries={binaries}")
        logger.info("[%s] standalone com %d dirs de binários", project_key,
                    binaries.count(",") + 1)
    else:
        excl = f"{excl},**/*.java"
        logger.warning("[%s] standalone SEM binários — Java EXCLUÍDO da análise (degradado)",
                       project_key)

    extra.append(f"-Dsonar.exclusions={excl}")
    return _run([str(scanner_bin), *props, *extra], repo, env, log_path)

def _scanner_path(base_dir: Path) -> Path:
    p = base_dir / "sonarqube-docker" / "sonar-scanner-5.0.1.3006-linux" / "bin" / "sonar-scanner"
    if not p.exists():
        raise ColetaError(f"sonar-scanner não encontrado: {p}")
    return p

def analisar_com_fallbacks(build_type: str, pom_filename: str | None,
                           repo: Path, project_key: str,
                           project_name: str, tag: str, sha7: str,
                           sonar_url: str, sonar_token: str,
                           base_dir: Path, log_dir: Path,
                           logger: logging.Logger) -> tuple[bool, str]:
    props = _sonar_props(project_key, project_name, tag, sha7,
                         sonar_url, sonar_token)
    log_path = log_dir / f"{project_key}.scan.log"
    log_path.write_text("", encoding="utf-8")
    scanner_bin = _scanner_path(base_dir)

    if build_type == "ant":
        rc, jdk_used = _ant_completo(repo, props, scanner_bin, log_path,
                                     logger, project_key)
        if rc == 0:
            return True, f"JDK {jdk_used} (ant build + scanner)"
        return False, "ant falhou em todos os JDKs do fallback"

    if build_type == "maven":
        nome = "mvn package sonar:sonar"
        if pom_filename:
            nome += f" -f {pom_filename}"
        def runner(env): return _maven_completo(repo, props, env, log_path,
                                                pom_filename)
    elif build_type == "gradle":
        init_script = _resolver_init_gradle(base_dir)
        logger.info("[%s] usando init-script: %s", project_key, init_script.name)
        nome = "gradle assemble sonar"
        def runner(env): return _gradle_completo(repo, props, env, log_path,
                                                 init_script)
    elif build_type == "bazel":
        nome = "bazel build //..."
        def runner(env): return _bazel_completo(repo, props, env, scanner_bin,
                                                log_path, logger, project_key)
    else:
        runner = None
        nome = "scanner-standalone"

    if runner is not None:
        declarado = detectar_jdk_declarado(repo)
        if declarado is not None:
            logger.info("[%s] sourceCompatibility declarado=%d (informativo)",
                        project_key, declarado)

        for v in JDK_FALLBACK_ORDER:
            jpath = jdk_path_para(v)
            if not jpath:
                logger.info("[%s] JDK %d não instalado, pulando", project_key, v)
                continue
            logger.info("[%s] tentando JDK %d em %s", project_key, v, jpath)
            rc = runner(env_com_jdk(jpath))
            if rc == 0:
                return True, f"JDK {v} ({nome})"
            logger.warning("[%s] %s com JDK %d falhou (rc=%d)",
                           project_key, nome, v, rc)

        if build_type == "gradle":
            logger.warning("[%s] todos JDKs falharam para 'assemble sonar' — "
                           "tentando build-only para gerar binários",
                           project_key)
        else:
            logger.warning("[%s] todos JDKs do fallback falharam para %s — caindo para scanner standalone",
                           project_key, nome)

    if build_type == "gradle":
        for v in JDK_FALLBACK_ORDER:
            jpath = jdk_path_para(v)
            if not jpath:
                continue
            logger.info("[%s] tentando build-only JDK %d em %s",
                        project_key, v, jpath)
            env_v = env_com_jdk(jpath)
            rc_build = _gradle_assemble_only(repo, env_v, log_path)
            if rc_build != 0:
                logger.warning("[%s] gradle assemble com JDK %d falhou (rc=%d)",
                               project_key, v, rc_build)
                continue
            logger.info("[%s] gradle assemble com JDK %d OK (modo build-only)",
                        project_key, v)
            binaries = find_java_binaries(repo)
            if not binaries:
                logger.warning("[%s] build-only com JDK %d completou mas sem .class — "
                               "build falso, descartando", project_key, v)
                continue
            logger.info("[%s] modo híbrido: build nativo OK + scanner standalone "
                        "com binários reais (do build nativo)", project_key)
            rc_scan = _scanner_standalone(repo, props, env_v, scanner_bin,
                                          log_path, logger, project_key)
            if rc_scan == 0:
                return True, f"JDK {v} (gradle assemble + scanner híbrido)"
            logger.warning("[%s] build-only OK mas scanner standalone falhou (rc=%d)",
                           project_key, rc_scan)
            return False, "build-only OK mas scanner falhou"
        logger.warning("[%s] todos JDKs falharam até em build-only — "
                       "caindo para scanner standalone degradado", project_key)

    rc = _scanner_standalone(repo, props, env_com_jdk(_primeiro_jdk_disponivel()),
                             scanner_bin, log_path, logger, project_key)
    if rc == 0:
        binaries = find_java_binaries(repo)
        return True, ("standalone com binários" if binaries
                      else "standalone DEGRADADO (Java excluído)")
    return False, "todos fallbacks falharam"

def aguardar_processamento(client: SonarClient, project_key: str,
                           logger: logging.Logger,
                           timeout: float = 180.0,
                           intervalo: float = 3.0) -> bool:
    logger.info("[%s] aguardando processamento Sonar...", project_key)
    deadline = time.monotonic() + timeout
    proximo_log = time.monotonic() + 30.0
    fila_ok = False

    while time.monotonic() < deadline:
        r = client.get("/api/ce/component", component=project_key)
        if r.status_code == 200:
            try:
                data = r.json()
            except ValueError:
                data = None
            if data is not None:
                queue = data.get("queue", []) or []
                current = data.get("current")
                current_status = (current or {}).get("status")
                if not queue and (current is None or
                                  current_status in ("SUCCESS", "FAILED")):
                    fila_ok = True
                    break
                if time.monotonic() >= proximo_log:
                    logger.info("[%s] ainda processando (queue=%d tasks)...",
                                project_key, len(queue))
                    proximo_log = time.monotonic() + 30.0
        time.sleep(intervalo)

    if not fila_ok:
        logger.warning("[%s] timeout %.0fs aguardando processamento",
                       project_key, timeout)
        return False

    r = client.get("/api/measures/component", component=project_key,
                   metricKeys="ncloc")
    if r.status_code == 200:
        try:
            data = r.json()
            measures = {m["metric"]: m.get("value")
                        for m in data.get("component", {}).get("measures", [])}
            if measures.get("ncloc"):
                logger.info("[%s] processamento OK (ncloc=%s)",
                            project_key, measures["ncloc"])
                return True
        except ValueError:
            pass
    logger.warning("[%s] fila drenou mas ncloc ausente — análise pode ter falhado",
                   project_key)
    return False

def coletar_um_projeto(row: dict, repo: Path, base_dir: Path, log_dir: Path,
                       sonar_url: str, sonar_token: str,
                       client: SonarClient, logger: logging.Logger,
                       skip_existing: bool = False) -> dict:
    pid = row["id"]
    nome = row["nome"]
    tag = row.get("tag", "")
    sha = row.get("commit_sha", "")
    snapshot_type = (row.get("snapshot_type") or SNAPSHOT_TYPE_RELEASE_TAG).strip()
    branch_principal = (row.get("branch_principal") or "").strip() or None

    out = {"id": pid, "nome": nome, "scan_ok": False,
           "build_caminho": "?", "sha7": sha[:7] if sha else "?"}

    if skip_existing and client.projeto_existe(pid):
        logger.info("[SKIP_EXISTING] %s já existe no Sonar — pulando scan", pid)
        out["scan_ok"] = True
        out["build_caminho"] = "skip-existing"
        return out

    if not (repo.is_dir() and (repo / ".git").is_dir()):
        logger.error("[ERRO] repo ausente: %s", repo)
        out["build_caminho"] = "repo-ausente"
        return out

    sha7 = git_checkout(repo, tag, logger,
                        snapshot_type=snapshot_type,
                        branch_principal=branch_principal)
    out["sha7"] = sha7
    limpar_scannerwork(repo)
    aplicar_patch_post_checkout(pid, repo, base_dir, logger)

    build_type, pom_filename = detectar_build(repo)
    logger.info("[%s] build_type=%s%s", pid, build_type,
                f" (pom={pom_filename})" if pom_filename else "")

    sucesso, caminho = analisar_com_fallbacks(
        build_type, pom_filename, repo, pid, nome, tag, sha7,
        sonar_url, sonar_token, base_dir, log_dir, logger,
    )
    out["build_caminho"] = caminho
    out["scan_ok"] = sucesso
    if not sucesso:
        logger.error("[%s] análise FALHOU em todos os caminhos", pid)
        return out

    aguardar_processamento(client, pid, logger)
    return out
