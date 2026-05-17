"""Fase 1 — checkout + análise Sonar via plugins nativos (mvn sonar:sonar / gradle sonar).

Estratégia:
- Maven  → uma única invocação `mvn package sonar:sonar` para que o plugin
  Maven autodescubra `target/classes/` e injete em `sonar.java.binaries`.
- Gradle → `./gradlew assemble sonar` com init-script (`sonar_init.gradle`)
  que aplica o plugin SonarQube a todos os subprojetos.
- Sem build file → `sonar-scanner` standalone com detecção de binários
  pré-existentes (target/classes, build/classes/java/main, etc.); se não
  houver `.class`, exclui Java da análise (modo degradado declarado).

Fallbacks §7.2: JDK 17 → JDK declarado → standalone-degradado.
"""
from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

from .io_utils import ColetaError, SonarClient

# Ordem estrita de tentativa: mais recente primeiro. Razão: projetos modernos
# (Gradle 9+, NullAway) exigem JDK 21+ para *rodar* o build tool, mesmo que
# declarem sourceCompatibility=11. Detectar declaração não basta.
JDK_FALLBACK_ORDER: list[int] = [21, 17, 11, 8]

JDK_FALLBACKS: dict[int, str] = {
    8:  "/usr/lib/jvm/temurin-8-jdk-amd64",
    11: "/usr/lib/jvm/temurin-11-jdk-amd64",
    17: "/usr/lib/jvm/java-17-openjdk-amd64",
    21: "/usr/lib/jvm/temurin-21-jdk-amd64",
}


def _primeiro_jdk_disponivel() -> str:
    """JDK genérico para tarefas que não dependem da versão (ex.: scanner
    standalone). Mais recente primeiro."""
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

# Exclusões aplicadas quando o scanner standalone usa src/main detectado.
# Inclui **/test/** e **/tests/** pois sonar.sources passa a apontar para
# diretórios concretos (não mais o repo inteiro): qualquer src/test/** que
# eventualmente case com o glob de detecção precisa ficar fora da análise
# para manter paridade com Maven/Gradle (apenas source set main).
STANDALONE_EXCLUSIONS = (
    "**/test/**,**/tests/**,**/build/**,**/target/**,**/out/**,**/buildSrc/**,"
    "**/examples/**,**/example/**,**/samples/**,**/sample/**,"
    "**/.git/**,**/node_modules/**"
)

GRADLE_INIT_DEFAULT = "sonar_init.gradle"

# Init-scripts específicos por projeto. NullAway tem subprojetos Android que
# conflitam com o plugin Sonar via initscript padrão; o init-script dedicado
# inclui AGP no classpath e exclui subprojetos Android via afterEvaluate.
GRADLE_INIT_SCRIPTS: dict[str, str] = {
    "uber-nullaway-01": "sonar_init_nullaway.gradle",
    # Dagger 2.57.2 também tem subprojetos Android; sem AGP no classpath do
    # initscript, sonar quebra com NoClassDefFoundError: BaseExtension.
    "google-dagger-03": "sonar_init_nullaway.gradle",
}

BINARY_PATTERNS = [
    "**/target/classes",
    "**/build/classes/java/main",
    "**/build/classes/main",
    "**/build/classes",
    "**/out/production/classes",
    "**/output/classes",  # Tomcat (Ant)
]

# Mapping projetos Ant → diretório de output esperado.
# Confirmar empiricamente quando rodar.
ANT_OUTPUT_DEFAULTS = {
    "cassandra": "build/classes/main",
    "tomcat":    "output/classes",
}

# Pipeline de invocações Ant por projeto. Cada elemento da lista externa
# é uma chamada `ant <args...>` separada (Tomcat exige duas: download-compile
# antes de deploy). Projetos não-mapeados usam ["build"] como default.
ANT_BUILD_PIPELINE: dict[str, list[list[str]]] = {
    "cassandra": [["build"]],
    "tomcat":    [["download-compile"], ["deploy"]],
}

# Diretórios de build a limpar antes de cada tentativa de Ant (por JDK).
# Razão: build parcial cached pode levar o scanner a pegar .class antigos
# via glob de binários e mascarar uma falha de build como sucesso.
ANT_BUILD_DIRS_TO_CLEAN: dict[str, list[str]] = {
    "apache-cassandra-04": ["build"],
    "apache-tomcat-01":    ["output"],
}

# Override de sonar.sources para projetos cuja estrutura não segue o layout
# Maven (src/main/java). Comparabilidade da amostra exige analisar apenas o
# código de produção principal — testes, exemplos e webapps de demonstração
# ficam de fora via STANDALONE_EXCLUSIONS. Paths são relativos ao repo.
SOURCE_PATHS_PROJETOS: dict[str, list[str]] = {
    "apache-cassandra-04": ["src/java"],
    "apache-tomcat-01":    ["java"],
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
    """Retorna (build_type, pom_filename_se_nao_padrao).

    pom_filename é None exceto para Maven com pom não-padrão (build-pom.xml,
    parent-pom.xml), caso em que precisa ser passado via `mvn -f`.
    """
    for special in ("build-pom.xml", "parent-pom.xml"):
        if (repo / special).exists():
            return "maven", special
    if (repo / "pom.xml").exists():
        return "maven", None
    # Inclui settings.gradle{.kts} para projetos multi-módulo cuja raiz só
    # declara settings e delega o build aos sub-módulos (ex.: Dagger).
    for marker in ("build.gradle", "build.gradle.kts",
                   "settings.gradle", "settings.gradle.kts"):
        if (repo / marker).exists():
            return "gradle", None
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
    return env


def find_java_binaries(repo: Path) -> str:
    """Localiza diretórios de bytecode pré-compilados. Vazio se nenhum."""
    found: list[str] = []
    for pat in BINARY_PATTERNS:
        for d in repo.glob(pat):
            if d.is_dir() and any(d.rglob("*.class")):
                found.append(str(d.resolve()))
    return ",".join(found)


def find_main_sources(repo: Path, project_key: str | None = None) -> str:
    """Localiza diretórios de código de produção. CSV de absolutos; vazio se nenhum.

    Se project_key estiver em SOURCE_PATHS_PROJETOS, usa os paths explícitos
    declarados ali (estruturas Ant legadas tipo src/java ou java/). Só inclui
    paths que existem e contêm pelo menos um .java.

    Caso contrário, glob padrão Maven/Gradle: **/src/main/java e
    **/src/main/kotlin (suporta multi-módulo).
    """
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


# ---------------- git ----------------

def git_checkout(repo: Path, tag: str, logger: logging.Logger) -> str:
    if not (repo / ".git").exists():
        raise ColetaError(f"Repo não inicializado: {repo}")
    subprocess.run(["git", "fetch", "--all", "--tags", "--quiet"],
                   cwd=str(repo), check=False)
    r = subprocess.run(["git", "checkout", "--force", tag, "--quiet"],
                       cwd=str(repo))
    if r.returncode != 0:
        raise ColetaError(f"git checkout {tag} falhou em {repo}")
    sha_full = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(repo),
                              capture_output=True, text=True).stdout.strip()
    sha7 = sha_full[:7]
    logger.info("git checkout %s (sha=%s) em %s", tag, sha7, repo.name)
    return sha7


def limpar_scannerwork(repo: Path) -> None:
    sw = repo / ".scannerwork"
    if sw.exists():
        shutil.rmtree(sw, ignore_errors=True)


# ---------------- análises com plugin nativo ----------------

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


def _resolver_init_gradle(project_key: str, base_dir: Path) -> Path:
    nome = GRADLE_INIT_SCRIPTS.get(project_key, GRADLE_INIT_DEFAULT)
    caminho = base_dir / "scripts-tcc" / nome
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
    return _run(cmd, repo, env, log_path)


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
    """Roda pipeline Ant (ANT_BUILD_PIPELINE) em ordem decrescente de JDKs.
    Para cada JDK viável: limpa build dirs, tenta toda a pipeline; só prossegue
    para o scanner se TODOS os passos retornaram 0. Falha definitivamente se
    nenhum JDK consegue completar o build — NÃO cai para scanner com binários
    cached (Cassandra 5.0.6 rejeita JDK 21 e o build precisa de JDK 11; rodar
    o scanner sobre .class antigos de uma build local mascararia ncloc/issues
    inválidos como sucesso).

    Retorna (rc_scanner, jdk_version_usado). rc != 0 indica falha de todos JDKs.
    """
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
    """Fallback: scanner direto. Detecta src/main/{java,kotlin} para apontar
    sonar.sources (paridade com Maven/Gradle: só código de produção). Detecta
    binários pré-existentes; se não houver, exclui *.java para evitar erro
    fatal do SonarJava."""
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
    """Tenta build+sonar via plugin nativo (ou ant+scanner), com fallbacks §7.2.
    Retorna (sucesso, descricao_do_caminho_usado)."""
    props = _sonar_props(project_key, project_name, tag, sha7,
                         sonar_url, sonar_token)
    log_path = log_dir / f"{project_key}.scan.log"
    log_path.write_text("", encoding="utf-8")
    scanner_bin = _scanner_path(base_dir)

    if build_type == "ant":
        # Ant tem fallback de JDKs internalizado em _ant_completo e NÃO cai
        # para scanner standalone — rodar scanner sobre binários cached de
        # uma build manual anterior mascararia falha como sucesso.
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
        init_script = _resolver_init_gradle(project_key, base_dir)
        logger.info("[%s] usando init-script: %s", project_key, init_script.name)
        nome = "gradle assemble sonar"
        def runner(env): return _gradle_completo(repo, props, env, log_path,
                                                 init_script)
    else:
        runner = None
        nome = "scanner-standalone"

    if runner is not None:
        # Iteração estrita JDK_FALLBACK_ORDER (mais recente primeiro).
        # Declaração no pom.xml/build.gradle é só informativa — o JDK que
        # roda o build tool importa mais que o sourceCompatibility.
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

        logger.warning("[%s] todos JDKs do fallback falharam para %s — caindo para scanner standalone",
                       project_key, nome)

    # último recurso: scanner standalone (com detecção de binários)
    rc = _scanner_standalone(repo, props, env_com_jdk(_primeiro_jdk_disponivel()),
                             scanner_bin, log_path, logger, project_key)
    if rc == 0:
        binaries = find_java_binaries(repo)
        return True, ("standalone com binários" if binaries
                      else "standalone DEGRADADO (Java excluído)")
    return False, "todos fallbacks falharam"


# ---------------- aguardar processamento ----------------

def aguardar_processamento(client: SonarClient, project_key: str,
                           logger: logging.Logger,
                           timeout: float = 180.0,
                           intervalo: float = 3.0) -> bool:
    """Aguarda a fila do Compute Engine drenar antes de declarar análise pronta.

    Antes verificávamos só ncloc via /api/measures/component, mas issues e
    métricas derivadas demoram mais que ncloc para aparecer; resultado: o
    extract subsequente pegava 0 issues em projetos com centenas (NullAway
    chegou a reportar total=0 com ncloc=19099). Polling em /api/ce/component
    resolve: só seguimos quando queue==[] e current não está em IN_PROGRESS/
    PENDING. Sanity check final em ncloc para confirmar que o projeto existe
    de fato no servidor.
    """
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


# ---------------- pipeline por projeto ----------------

def coletar_um_projeto(row: dict, repo: Path, base_dir: Path, log_dir: Path,
                       sonar_url: str, sonar_token: str,
                       client: SonarClient, logger: logging.Logger,
                       skip_existing: bool = False) -> dict:
    pid = row["id"]
    nome = row["nome"]
    tag = row["tag"]
    sha = row.get("commit_sha", "")

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

    sha7 = git_checkout(repo, tag, logger)
    out["sha7"] = sha7
    limpar_scannerwork(repo)

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
