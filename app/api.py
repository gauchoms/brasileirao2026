import os
import requests
from config import Config

BASE_URL = "https://v3.football.api-sports.io"

headers = {
    "x-apisports-key": Config.API_FOOTBALL_KEY
}


# ── Helpers para times com ID indefinido (placeholders de fase eliminatória) ──

def _api_id_placeholder(nome):
    """Gera api_id sintético para times ainda indefinidos (ex: 'Winner Group A')."""
    return 9000000 + (hash(nome) % 999999)

def _nome_placeholder_br(nome):
    """Traduz nomes de placeholder da API Football para português."""
    import re
    mapa = {
        'Winner': 'Vencedor', 'Runner-up': '2º colocado',
        'Group': 'Grupo', 'winner': 'vencedor',
    }
    resultado = nome
    for en, pt in mapa.items():
        resultado = resultado.replace(en, pt)
    return resultado

def eh_placeholder(time):
    """Retorna True se o time é um placeholder indefinido."""
    if not time:
        return False
    return getattr(time, 'api_id', 0) >= 9000000


def garantir_time_placeholder(nome_original):
    """
    Busca ou cria um Time placeholder para times indefinidos.
    Usa api_id sintético baseado no nome.
    """
    from app.models import Time
    from app import db

    api_id = _api_id_placeholder(nome_original)
    nome_br = _nome_placeholder_br(nome_original)

    time = Time.query.filter_by(api_id=api_id).first()
    if not time:
        time = Time(
            api_id=api_id,
            nome=nome_br,
            logo_url=None,
            ativo=True
        )
        db.session.add(time)
        db.session.flush()
    return time


def configurar_cloudinary():
    import cloudinary
    cloudinary.config(
        cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
        api_key=os.getenv('CLOUDINARY_API_KEY'),
        api_secret=os.getenv('CLOUDINARY_API_SECRET')
    )

def upload_logo_cloudinary(api_id, logo_url_original):
    """Faz upload da logo para Cloudinary. Retorna URL ou None."""
    if not logo_url_original:
        return None
    try:
        import cloudinary.uploader
        configurar_cloudinary()
        resultado = cloudinary.uploader.upload(
            logo_url_original,
            public_id=f"logos/teams/{api_id}",
            overwrite=False,
            resource_type="image",
            transformation=[{"width": 120, "height": 120, "crop": "fit"}]
        )
        return resultado.get("secure_url")
    except Exception as e:
        print(f"[CLOUDINARY] Erro logo {api_id}: {e}")
        return None

def get_jogos_brasileirao():
    url = f"{BASE_URL}/fixtures"
    params = {"league": 71, "season": 2026}
    response = requests.get(url, headers=headers, params=params)
    return response.json()

def processar_jogos(data):
    """
    Processa fixtures da API Football.
    Times com id=null (fases eliminatórias indefinidas) recebem id sintético placeholder.
    """
    jogos = []
    for fixture in data.get('response', []):
        home = fixture['teams']['home']
        away = fixture['teams']['away']

        # Times indefinidos (ex: "Winner Group A") recebem id sintético
        home_id = home['id'] if home['id'] else _api_id_placeholder(home['name'])
        away_id = away['id'] if away['id'] else _api_id_placeholder(away['name'])

        jogo = {
            'api_id':           fixture['fixture']['id'],
            'rodada':           fixture['league']['round'],
            'grupo':            fixture['league'].get('group') or '',
            'time_casa':        home['name'],
            'time_fora':        away['name'],
            'time_casa_id':     home_id,
            'time_fora_id':     away_id,
            'logo_casa':        home.get('logo') or '',
            'logo_fora':        away.get('logo') or '',
            'casa_placeholder': home['id'] is None,
            'fora_placeholder': away['id'] is None,
            'data':             fixture['fixture']['date'],
            'gols_casa':        fixture['goals']['home'],
            'gols_fora':        fixture['goals']['away'],
        }
        jogos.append(jogo)
    return jogos

def get_resultados_brasileirao(league_id=71, season=2026):
    url = f"{BASE_URL}/fixtures"
    params = {"league": league_id, "season": season, "status": "FT"}
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
                is_ph   = jogo.get('casa_placeholder') if key == 'time_casa_id' else jogo.get('fora_placeholder')
                if api_id not in times_cadastrados:
                    if is_ph:
                        time = garantir_time_placeholder(nome)
                    else:
                        time = Time.query.filter_by(api_id=api_id).first()
                        if not time:
                            logo_cl = upload_logo_cloudinary(api_id, logo) if logo else None
                            time = Time(api_id=api_id, nome=nome, logo_url=logo_cl or logo, ativo=True)
                            db.session.add(time)
                            db.session.flush()
                        elif logo and not time.logo_url:
                            logo_cl = upload_logo_cloudinary(api_id, logo)
                            time.logo_url = logo_cl or logo
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
