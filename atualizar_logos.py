"""
Script para buscar logos dos times da API-Football e salvar no banco

COMO USAR:
1. Certifique-se de que sua API_FOOTBALL_KEY está no .env
2. Execute: python atualizar_logos.py
3. Aguarde (pode demorar alguns minutos)
"""

import os
import requests
import time as tempo
from dotenv import load_dotenv
from app import create_app, db
from app.models import Time

# Carrega variáveis de ambiente
load_dotenv()

API_KEY = os.getenv('API_FOOTBALL_KEY')
API_URL = 'https://v3.football.api-sports.io'

def buscar_logo_time(api_id):
    """
    Busca informações do time na API-Football
    Retorna: (logo_url, pais, liga_principal) ou (None, None, None)
    """
    if not api_id:
        return None, None, None
    
    headers = {
        'x-rapidapi-key': API_KEY,
        'x-rapidapi-host': 'v3.football.api-sports.io'
    }
    
    try:
        # Endpoint: teams?id={api_id}
        url = f'{API_URL}/teams'
        params = {'id': api_id}
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('response') and len(data['response']) > 0:
                team_data = data['response'][0]
                
                # Extrai informações
                logo_url = team_data['team'].get('logo', None)
                pais = team_data['team'].get('country', None)
                
                # Liga principal (primeira da lista, se houver)
                liga_principal = None
                if 'venue' in team_data and team_data['venue'].get('name'):
                    liga_principal = team_data['venue'].get('name')
                
                return logo_url, pais, liga_principal
        
        return None, None, None
        
    except Exception as e:
        print(f"❌ Erro ao buscar time {api_id}: {str(e)}")
        return None, None, None


def atualizar_logos():
    """
    Atualiza logos de todos os times que não têm logo_url
    """
    app = create_app()
    
    with app.app_context():
        # Busca times sem logo
        times_sem_logo = Time.query.filter(
            (Time.logo_url == None) | (Time.logo_url == '')
        ).filter(
            Time.api_id != None
        ).all()
        
        total = len(times_sem_logo)
        print(f"\n🔍 Encontrados {total} times sem logo")
        print(f"🔑 API Key: {API_KEY[:10]}..." if API_KEY else "❌ API Key não encontrada!")
        print("\n" + "="*60)
        
        sucesso = 0
        falhas = 0
        
        for idx, time in enumerate(times_sem_logo, 1):
            print(f"\n[{idx}/{total}] Processando: {time.nome} (API ID: {time.api_id})")
            
            # Busca logo na API
            logo_url, pais, liga = buscar_logo_time(time.api_id)
            
            if logo_url:
                # Atualiza no banco
                time.logo_url = logo_url
                if pais:
                    time.pais = pais
                if liga:
                    time.liga_principal = liga
                
                time.ultima_atualizacao = db.func.now()
                
                db.session.commit()
                
                print(f"   ✅ Logo salvo: {logo_url}")
                if pais:
                    print(f"   🌍 País: {pais}")
                
                sucesso += 1
            else:
                print(f"   ❌ Logo não encontrado na API")
                falhas += 1
            
            # Rate limiting (100 requests/min na API-Football)
            # Aguarda 0.7s entre requisições = ~85 req/min (seguro)
            if idx < total:
                tempo.sleep(0.7)
        
        print("\n" + "="*60)
        print(f"\n📊 RESUMO:")
        print(f"   ✅ Sucesso: {sucesso}")
        print(f"   ❌ Falhas: {falhas}")
        print(f"   📈 Total: {total}")
        print(f"\n🎉 Processo concluído!")


def atualizar_logo_individual(time_id):
    """
    Atualiza logo de um time específico
    
    USO: python atualizar_logos.py --time-id 18
    """
    app = create_app()
    
    with app.app_context():
        time = Time.query.get(time_id)
        
        if not time:
            print(f"❌ Time com ID {time_id} não encontrado")
            return
        
        print(f"🔍 Buscando logo para: {time.nome} (API ID: {time.api_id})")
        
        logo_url, pais, liga = buscar_logo_time(time.api_id)
        
        if logo_url:
            time.logo_url = logo_url
            if pais:
                time.pais = pais
            if liga:
                time.liga_principal = liga
            
            time.ultima_atualizacao = db.func.now()
            db.session.commit()
            
            print(f"✅ Logo salvo: {logo_url}")
        else:
            print(f"❌ Logo não encontrado")


if __name__ == '__main__':
    import sys
    
    # Verifica se tem argumento --time-id
    if len(sys.argv) > 2 and sys.argv[1] == '--time-id':
        time_id = int(sys.argv[2])
        atualizar_logo_individual(time_id)
    else:
        # Atualiza todos
        atualizar_logos()
