import os
import requests
import pandas as pd
from dotenv import load_dotenv


load_dotenv()

TOKEN = os.getenv("SONAR_TOKEN")
URL = os.getenv("SONAR_URL")

def extrair_tudo():
    search_url = f"{URL}/api/components/search?qualifiers=TRK"
    projects = requests.get(search_url, auth=(TOKEN, "")).json()['components']
    
    final_data = []
    
    for p in projects:
        print(f"Extraindo métricas de: {p['name']}...")
        
        measures_url = f"{URL}/api/measures/component_tree"
        params = {
            "component": p['key'],
            "metricKeys": "complexity,cognitive_complexity,sqale_index,ncloc",
            "ps": 500,
            "qualifiers": "FIL"
        }
        
        res = requests.get(measures_url, params=params, auth=(TOKEN, "")).json()
        
        for file_comp in res.get('components', []):
            row = {
                "projeto": p['name'],
                "arquivo": file_comp['path'],
                "complexidade_ciclomatica": 0,
                "complexidade_cognitiva": 0,
                "debito_tecnico_min": 0,
                "linhas_codigo": 0
            }
            
            for m in file_comp.get('measures', []):
                val = float(m['value']) if 'value' in m else 0
                if m['metric'] == 'complexity': row["complexidade_ciclomatica"] = val
                if m['metric'] == 'cognitive_complexity': row["complexidade_cognitiva"] = val
                if m['metric'] == 'sqale_index': row["debito_tecnico_min"] = val
                if m['metric'] == 'ncloc': row["linhas_codigo"] = val
            
            final_data.append(row)
            
    df = pd.DataFrame(final_data)
    df['governanca'] = df['projeto'].apply(lambda x: 
        'Apache' if any(n in x.lower() for n in ['kafka', 'cassandra', 'zookeeper', 'tomcat', 'flink'])
        else 'Google' if any(n in x.lower() for n in ['gson', 'guava', 'dagger', 'auto', 'grpc'])
        else 'Netflix'
    )
    
    df.to_csv("dataset_tcc_consolidado.csv", index=False)
    print("CSV gerado com sucesso!")

extrair_tudo()