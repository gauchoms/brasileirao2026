import os
import requests
from config import Config

BASE_URL = "https://v3.football.api-sports.io"

headers = {
    "x-apisports-key": Config.API_FOOTBALL_KEY
}

def get_jogos_brasileirao():
    url = f"{BASE_URL}/fixtures"
    params = {"league": 71, "season": 2026}
    response = requests.get(url, headers=headers, params=params)
    return response.json()

def processar_jogos(data):
    """Processa fixtures da API Football, incluindo logos e grupo."""
    jogos = []
    for fixture in data.get('response', []):
        jogo = {
            'api_id':       fixture['fixture']['id'],
            'rodada':       fixture['league']['round'],
            'grupo':        fixture['league'].get('group') or '',   # ← NOVO: "Group A", "Group B", etc.
            'time_casa':    fixture['teams']['home']['name'],
            'time_fora':    fixture['teams']['away']['name'],
            'time_casa_id': fixture['teams']['home']['id'],
            'time_fora_id': fixture['teams']['away']['id'],
            'logo_casa':    fixture['teams']['home'].get('logo') or '',  # ← NOVO
            'logo_fora':    fixture['teams']['away'].get('logo') or '',  # ← NOVO
            'data':         fixture['fixture']['date'],
            'gols_casa':    fixture['goals']['home'],
            'gols_fora':    fixture['goals']['away'],
        }
        jogos.append(jogo)
    return jogos

def get_resultados_brasileirao(league_id=71, season=2026):
    url = f"{BASE_URL}/fixtures"
    params = {"league": league_id, "season": season, "status": "FT-AET-PEN"}
    response = requests.get(url, headers=headers, params=params)
    return response.json()

def listar_ligas_disponiveis(ano=2026):
    url = f"{BASE_URL}/leagues"
    params = {"season": ano}
    response = requests.get(url, headers=headers, params=params)
    data = response.json()
    ligas = []
    for item in data.get('response', []):
        liga = item['league']
        pais = item['country']
        ligas.append({
            'api_id':     liga['id'],
            'nome':       liga['name'],
            'pais':       pais['name'],
            'logo':       liga['logo'],
            'tipo':       liga['type'],
            'temporadas': item['seasons']
        })
    return ligas

def get_jogos_competicao(league_id, season):
    url = f"{BASE_URL}/fixtures"
    params = {"league": league_id, "season": season}
    response = requests.get(url, headers=headers, params=params)
    return response.json()

def get_competicoes_time(time_api_id, ano):
    api_key = os.getenv('API_FOOTBALL_KEY')
    url = f'https://v3.football.api-sports.io/fixtures'
    h = {'x-apisports-key': api_key}
    params = {'team': time_api_id, 'season': ano}
    response = requests.get(url, headers=h, params=params)
    if response.status_code == 200:
        data = response.json()
        competicoes = {}
        for fixture in data.get('response', []):
            league = fixture['league']
            league_id = league['id']
            if league_id not in competicoes:
                competicoes[league_id] = {
                    'api_id': league_id,
                    'nome': f"{league['name']} {ano}",
                    'tipo': league.get('type', 'league').lower(),
                    'ano': ano,
                    'logo': league['logo']
                }
        return list(competicoes.values())
    return []

def importar_jogos_time_ano(time_api_id, ano):
    from app.models import Competicao, Time, Jogo
    from app import db

    competicoes_api = get_competicoes_time(time_api_id, ano)
    total_jogos_importados = 0
    competicoes_criadas = []

    for comp_data in competicoes_api:
        competicao = Competicao.query.filter_by(
            api_league_id=comp_data['api_id'], ano=ano
        ).first()
        if not competicao:
            competicao = Competicao(
                nome=comp_data['nome'],
                ano=ano,
                tipo=comp_data.get('tipo', 'league'),
                api_league_id=comp_data['api_id'],
                uso='bolao'
            )
            db.session.add(competicao)
            db.session.flush()
            competicoes_criadas.append(competicao.nome)

        jogos_data = get_jogos_competicao(comp_data['api_id'], ano)
        jogos = processar_jogos(jogos_data)
        times_cadastrados = {}

        for jogo in jogos:
            for key in ['time_casa_id', 'time_fora_id']:
                api_id  = jogo[key]
                nome    = jogo['time_casa'] if key == 'time_casa_id' else jogo['time_fora']
                logo    = jogo['logo_casa'] if key == 'time_casa_id' else jogo['logo_fora']
                if api_id not in times_cadastrados:
                    time = Time.query.filter_by(api_id=api_id).first()
                    if not time:
                        time = Time(api_id=api_id, nome=nome, logo_url=logo, ativo=True)
                        db.session.add(time)
                        db.session.flush()
                    elif logo and not time.logo_url:
                        time.logo_url = logo
                    times_cadastrados[api_id] = time.id

            jogo_existente = Jogo.query.filter_by(api_id=jogo['api_id']).first()
            if not jogo_existente:
                novo_jogo = Jogo(
                    api_id=jogo['api_id'],
                    competicao_id=competicao.id,
                    rodada=jogo['rodada'],
                    grupo=jogo.get('grupo', ''),
                    time_casa_id=times_cadastrados[jogo['time_casa_id']],
                    time_fora_id=times_cadastrados[jogo['time_fora_id']],
                    data=jogo['data'],
                    gols_casa=jogo['gols_casa'],
                    gols_fora=jogo['gols_fora']
                )
                db.session.add(novo_jogo)
                total_jogos_importados += 1
            else:
                # Atualiza grupo se vier vazio
                if jogo.get('grupo') and not getattr(jogo_existente, 'grupo', None):
                    try:
                        jogo_existente.grupo = jogo['grupo']
                    except Exception:
                        pass

    db.session.commit()
    return {'competicoes_criadas': competicoes_criadas, 'total_jogos': total_jogos_importados}
