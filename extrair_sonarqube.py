import os
import requests
import pandas as pd
from dotenv import load_dotenv


load_dotenv()

TOKEN = os.getenv("SONAR_TOKEN")
SERVER_URL = os.getenv("SONAR_URL")
PROJECT_KEY = "apache-kafka"  
OUTPUT_FILE = f"metrics_{PROJECT_KEY}.csv"

def get_all_measures(project_key):
    page = 1
    all_components = []
    
    while True:
        url = f"{SERVER_URL}/api/measures/component_tree"
        params = {
            "component": project_key,
            "metricKeys": "complexity,cognitive_complexity,sqale_index,reliability_remediation_effort",
            "ps": 500,  
            "p": page,
            "qualifiers": "FIL" 
        }
        
        response = requests.get(url, params=params, auth=(TOKEN, ""))
        data = response.json()
        
        components = data.get("components", [])
        if not components:
            break
            
        for comp in components:
            
            m_data = { "file": comp.get("path"), "project": project_key }
            for m in comp.get("measures", []):
                m_data[m["metric"]] = m.get("value")
            all_components.append(m_data)
        
        print(f"Página {page} processada...")
        page += 1
        
        
        if page > (data["paging"]["total"] // 500) + 1:
            break
            
    return all_components


print(f"Iniciando extração do projeto: {PROJECT_KEY}")
results = get_all_measures(PROJECT_KEY)
df = pd.DataFrame(results)


df.to_csv(OUTPUT_FILE, index=False)
print(f"Sucesso! {len(df)} arquivos extraídos e salvos em {OUTPUT_FILE}")