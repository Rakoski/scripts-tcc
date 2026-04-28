import csv
import json
import requests
import os
from datetime import datetime

SONAR_URL = "http://localhost:9000"
SONAR_TOKEN = os.environ.get("SONAR_TOKEN", "SEU_TOKEN_AQUI") 
CSV_PATH = "projetos-tcc-dataset.csv"
OUTPUT_DIR = "../dados/extracoes/"

METRICS = (
    "ncloc,ncloc_language_distribution,complexity,cognitive_complexity,"
    "sqale_index,sqale_debt_ratio,sqale_rating,code_smells,bugs,vulnerabilities,"
    "reliability_rating,security_rating,duplicated_lines_density,duplicated_blocks,"
    "reliability_remediation_effort,security_remediation_effort,development_cost"
)

def criar_diretorio():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

def ler_projetos_do_csv():
    projetos = []
    with open(CSV_PATH, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row['tag'].strip():
                projetos.append(row)
    return projetos

def extrair_metricas_projeto(project_key):
    url = f"{SONAR_URL}/api/measures/component"
    params = {
        "component": project_key,
        "metricKeys": METRICS
    }
    response = requests.get(url, params=params, auth=(SONAR_TOKEN, ''))
    response.raise_for_status()
    return response.json().get('component', {}).get('measures', [])

def extrair_metricas_arquivos(project_key):
    url = f"{SONAR_URL}/api/measures/component_tree"
    arquivos = []
    p = 1
    ps = 500
    
    while True:
        params = {
            "component": project_key,
            "metricKeys": METRICS,
            "qualifiers": "FIL",
            "p": p,
            "ps": ps
        }
        response = requests.get(url, params=params, auth=(SONAR_TOKEN, ''))
        response.raise_for_status()
        
        data = response.json()
        components = data.get('components', [])
        arquivos.extend(components)
        
        paging = data.get('paging', {})
        total = paging.get('total', 0)
        
        if p * ps >= total:
            break
        p += 1
        
    return arquivos

def main():
    print("Iniciando extração consolidada do SonarQube...")
    criar_diretorio()
    projetos = ler_projetos_do_csv()
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dataset_final = []

    for proj in projetos:
        project_key = proj['id'] 
        print(f"[{proj['arquetipo']}] Extraindo: {proj['nome']} ({project_key})...")
        
        try:
            medidas_projeto = extrair_metricas_projeto(project_key)
            medidas_arquivos = extrair_metricas_arquivos(project_key)
            
            dataset_final.append({
                "metadados_csv": proj,
                "metricas_projeto": medidas_projeto,
                "metricas_arquivos": medidas_arquivos
            })
            print(f"  └─ Sucesso! {len(medidas_arquivos)} arquivos extraídos.")
            
        except requests.exceptions.RequestException as e:
            print(f"  └─ ERRO ao extrair {proj['nome']}: {e}")
            print(f"     Status: Verifique se o scanner rodou e se a project_key bate.")

    output_file = os.path.join(OUTPUT_DIR, f"sonar_dataset_completo_{timestamp}.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(dataset_final, f, indent=2, ensure_ascii=False)
        
    print(f"\nExtração concluída! Dados salvos em: {output_file}")

if __name__ == "__main__":
    main()