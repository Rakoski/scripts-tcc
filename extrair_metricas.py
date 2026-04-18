#!/usr/bin/env python3
"""
extrair_metricas_sonar.py

Extrai métricas do SonarQube em dois níveis:
  - projeto (uma linha por projeto) -> dataset_projetos.csv
  - arquivo (uma linha por arquivo) -> dataset_arquivos.csv

Lê a lista de projetos e seus arquétipos de uma planilha mestre CSV.
"""

import os
import sys
import csv
from datetime import datetime
import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("SONAR_TOKEN")
URL = os.getenv("SONAR_URL", "http://localhost:9000")

if not TOKEN:
    sys.exit("ERRO: SONAR_TOKEN não definido no .env")

# Métricas coletadas em ambos os níveis
METRICS_PROJETO = [
    "ncloc",
    "ncloc_language_distribution",
    "complexity",
    "cognitive_complexity",
    "sqale_index",
    "sqale_debt_ratio",
    "sqale_rating",
    "code_smells",
    "bugs",
    "vulnerabilities",
    "reliability_rating",
    "security_rating",
    "duplicated_lines_density",
    "duplicated_blocks",
    "reliability_remediation_effort",
    "security_remediation_effort",
    "development_cost",
]

METRICS_ARQUIVO = [
    "ncloc",
    "complexity",
    "cognitive_complexity",
    "sqale_index",
    "code_smells",
    "bugs",
]


def get_project_measures(project_key):
    """Retorna um dict com as métricas no nível do projeto."""
    r = requests.get(
        f"{URL}/api/measures/component",
        params={"component": project_key, "metricKeys": ",".join(METRICS_PROJETO)},
        auth=(TOKEN, ""),
    )
    r.raise_for_status()
    measures = {m["metric"]: m.get("value", "") for m in r.json()["component"].get("measures", [])}
    return measures


def get_file_measures(project_key):
    """Retorna uma lista de dicts, um por arquivo, com métricas no nível de arquivo."""
    all_files = []
    page = 1
    while True:
        r = requests.get(
            f"{URL}/api/measures/component_tree",
            params={
                "component": project_key,
                "metricKeys": ",".join(METRICS_ARQUIVO),
                "qualifiers": "FIL",
                "ps": 500,
                "p": page,
            },
            auth=(TOKEN, ""),
        )
        r.raise_for_status()
        data = r.json()
        components = data.get("components", [])
        if not components:
            break
        for comp in components:
            row = {"arquivo": comp.get("path")}
            for m in comp.get("measures", []):
                row[m["metric"]] = m.get("value", "")
            all_files.append(row)
        page += 1
    return all_files

def parse_language_dist(dist_str):
    """Converte 'java=22845;xml=832' em {'java': 22845, 'xml': 832}"""
    if not dist_str:
        return {}
    return {k: int(v) for k, v in (pair.split("=") for pair in dist_str.split(";"))}

def pct_java(dist_str):
    langs = parse_language_dist(dist_str)
    total = sum(langs.values())
    return (langs.get("java", 0) / total * 100) if total > 0 else 0

def main():
    planilha = pd.read_csv("dados/projetos-tcc-dataset.csv")
    print(f"Carregados {len(planilha)} projetos da planilha mestre")

    linhas_projeto = []
    linhas_arquivo = []
    data_extracao = datetime.now().strftime("%Y-%m-%d")

    for _, proj in planilha.iterrows():
        key = proj["sonar_project_key"]
        print(f"Extraindo {key}...")
        try:
            medidas = get_project_measures(key)
        except requests.HTTPError as e:
            print(f"  ERRO em {key}: {e}")
            continue

        linha = {
            "data_extracao": data_extracao,
            "id": proj["id"],
            "nome": proj["nome"],
            "empresa": proj["empresa"],
            "arquetipo": proj["arquetipo"],
            "status": proj["status"],
            "tag": proj["tag"],
            "commit_sha": proj["commit_sha"],
        }
        for m in METRICS_PROJETO:
            linha[m] = medidas.get(m, "")
        linhas_projeto.append(linha)

        # Nível de arquivo (opcional - comenta se não quiser)
        try:
            arquivos = get_file_measures(key)
            for a in arquivos:
                a.update({
                    "id": proj["id"],
                    "nome": proj["nome"],
                    "arquetipo": proj["arquetipo"],
                })
                linhas_arquivo.append(a)
            print(f"  {len(arquivos)} arquivos extraídos")
        except requests.HTTPError as e:
            print(f"  ERRO arquivos em {key}: {e}")

    out_proj = f"dados/sonar-projetos-{data_extracao}.csv"
    pd.DataFrame(linhas_projeto).to_csv(out_proj, index=False)
    print(f"Salvo: {out_proj}")

    if linhas_arquivo:
        out_arq = f"dados/sonar-arquivos-{data_extracao}.csv"
        pd.DataFrame(linhas_arquivo).to_csv(out_arq, index=False)
        print(f"Salvo: {out_arq}")


if __name__ == "__main__":
    main()