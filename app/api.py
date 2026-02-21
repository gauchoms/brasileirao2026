
import requests
from config import Config

BASE_URL = "https://v3.football.api-sports.io"

headers = {
    "x-apisports-key": Config.API_FOOTBALL_KEY
}

def get_jogos_brasileirao():
    url = f"{BASE_URL}/fixtures"
    params = {
        "league": 71,
        "season": 2026
    }
    response = requests.get(url, headers=headers, params=params)
    data = response.json()
    return data

def processar_jogos(data):
    jogos = []
    for fixture in data['response']:
        jogo = {
            'api_id': fixture['fixture']['id'],
            'rodada': fixture['league']['round'],
            'time_casa': fixture['teams']['home']['name'],
            'time_fora': fixture['teams']['away']['name'],
            'time_casa_id': fixture['teams']['home']['id'],
            'time_fora_id': fixture['teams']['away']['id'],
            'data': fixture['fixture']['date'],
            'gols_casa': fixture['goals']['home'],
            'gols_fora': fixture['goals']['away'],
        }
        jogos.append(jogo)
    return jogos
def get_resultados_brasileirao():
    url = f"{BASE_URL}/fixtures"
    params = {
        "league": 71,
        "season": 2026,
        "status": "FT"  # FT = Full Time, jogos já encerrados
    }
    response = requests.get(url, headers=headers, params=params)
    data = response.json()
    return data

def listar_ligas_disponiveis(ano=2026):
    url = f"{BASE_URL}/leagues"
    params = {
        "season": ano
    }
    response = requests.get(url, headers=headers, params=params)
    data = response.json()
    
    ligas = []
    for item in data.get('response', []):
        liga = item['league']
        pais = item['country']
        
        ligas.append({
            'api_id': liga['id'],
            'nome': liga['name'],
            'pais': pais['name'],
            'logo': liga['logo'],
            'tipo': liga['type'],
            'temporadas': item['seasons']
        })
    
    return ligas

def get_jogos_competicao(league_id, season):
    url = f"{BASE_URL}/fixtures"
    params = {
        "league": league_id,
        "season": season
    }
    response = requests.get(url, headers=headers, params=params)
    data = response.json()
    return data