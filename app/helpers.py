# helpers.py - Funções auxiliares para tradução e formatação
# Usado como filtros Jinja2 e funções de template no Brasileirão 2026

# ============================================================
# TRADUÇÃO DE PAÍSES (inglês → português)
# ============================================================

TRADUCAO_PAISES = {
    # América
    "Brazil": "Brasil",
    "Argentina": "Argentina",
    "Uruguay": "Uruguai",
    "Colombia": "Colômbia",
    "Chile": "Chile",
    "Peru": "Peru",
    "Paraguay": "Paraguai",
    "Bolivia": "Bolívia",
    "Ecuador": "Equador",
    "Venezuela": "Venezuela",
    "Mexico": "México",
    "United States": "Estados Unidos",
    "USA": "EUA",
    "Canada": "Canadá",

    # Europa
    "Germany": "Alemanha",
    "France": "França",
    "Spain": "Espanha",
    "Italy": "Itália",
    "England": "Inglaterra",
    "Portugal": "Portugal",
    "Netherlands": "Holanda",
    "Belgium": "Bélgica",
    "Switzerland": "Suíça",
    "Austria": "Áustria",
    "Sweden": "Suécia",
    "Norway": "Noruega",
    "Denmark": "Dinamarca",
    "Poland": "Polônia",
    "Czech Republic": "República Tcheca",
    "Croatia": "Croácia",
    "Serbia": "Sérvia",
    "Greece": "Grécia",
    "Turkey": "Turquia",
    "Russia": "Rússia",
    "Ukraine": "Ucrânia",
    "Scotland": "Escócia",
    "Wales": "País de Gales",
    "Hungary": "Hungria",
    "Romania": "Romênia",
    "Slovakia": "Eslováquia",
    "Slovenia": "Eslovênia",
    "Finland": "Finlândia",
    "Ireland": "Irlanda",

    # África
    "Morocco": "Marrocos",
    "Senegal": "Senegal",
    "Nigeria": "Nigéria",
    "Cameroon": "Camarões",
    "Ghana": "Gana",
    "Egypt": "Egito",
    "South Africa": "África do Sul",
    "Ivory Coast": "Costa do Marfim",
    "Cape Verde Islands": "Ilhas Cabo Verde",
    "Tunisia": "Tunísia",
    "Algeria": "Argélia",

    # Ásia / Oceania
    "Japan": "Japão",
    "South Korea": "Coreia do Sul",
    "Uzbekistan":"Usbequistão",
    "China": "China",
    "Australia": "Austrália",
    "Saudi Arabia": "Arábia Saudita",
    "Iran": "Irã",
    "Qatar": "Catar",
    "New Zealand":"Nova Zelândia",
    "Jordan":"Jordânia",
    "United Arab Emirates": "Emirados Árabes",

    # World
    "World": "Mundial",
}

# ============================================================
# NOMES DE SELEÇÕES NACIONAIS (para detectar se é seleção)
# ============================================================

SELECOES_NACIONAIS = set(TRADUCAO_PAISES.keys()) | set(TRADUCAO_PAISES.values())

# Adiciona variações comuns usadas pela API-Football
SELECOES_NACIONAIS.update([
    "Brazil", "Brasil", "Argentina", "France", "Germany", "Alemanha",
    "Spain", "Espanha", "England", "Inglaterra", "Portugal", "Italy",
    "Itália", "Netherlands", "Holanda", "Belgium", "Bélgica",
    "Croatia", "Croácia", "Uruguay", "Uruguai", "Colombia", "Colômbia",
    "Mexico", "México", "Japan", "Japão", "South Korea", "Coreia do Sul",
    "Morocco", "Marrocos", "Senegal", "Nigeria", "Nigéria",
    "Switzerland", "Suíça", "Denmark", "Dinamarca", "Poland", "Polônia",
    "Australia", "Austrália", "USA", "United States", "Estados Unidos",
    "Ecuador", "Equador", "Chile", "Peru", "Paraguay", "Paraguai",
    "Bolivia", "Bolívia", "Venezuela", "Serbia", "Sérvia",
    "Turkey", "Turquia", "Sweden", "Suécia", "Wales", "País de Gales",
    "Scotland", "Escócia", "Austria", "Áustria", "Iran", "Irã",
    "Saudi Arabia", "Arábia Saudita", "Qatar", "Catar",
    "Ghana", "Gana", "Cameroon", "Camarões", "Tunisia", "Tunísia",
    "Cape Verde Islands", "Ilhas Cabo Verde",
])


def traduzir_pais(nome):
    """
    Traduz nome de país/seleção do inglês para o português.
    Se não encontrar tradução, retorna o nome original.
    
    Uso no template: {{ traduzir_pais(time.pais) }}
    Ou como filtro:  {{ time.pais | nome_br }}
    """
    if not nome:
        return nome
    return TRADUCAO_PAISES.get(nome, nome)


def eh_selecao(nome):
    """
    Verifica se o nome de um time é uma seleção nacional.
    Retorna True se for seleção, False se for clube.
    
    Uso no template:
    {% if eh_selecao(jogo.time_casa.nome) %}
        {{ traduzir_pais(jogo.time_casa.nome) }}
    {% else %}
        {{ jogo.time_casa.nome }}
    {% endif %}
    """
    if not nome:
        return False
    return nome in SELECOES_NACIONAIS


def formatar_rodada(rodada_str):
    """
    Formata string de rodada da API-Football para exibição.
    Ex: 'Regular Season - 1' → 'Rodada 1'
    """
    if not rodada_str:
        return rodada_str
    rodada_str = rodada_str.replace('Regular Season - ', 'Rodada ')
    return rodada_str


# ============================================================
# REGISTRO DOS FILTROS NO JINJA2
# Adicione isso no app/__init__.py dentro de create_app():
#
#   from app.helpers import traduzir_pais, eh_selecao, formatar_rodada
#   app.jinja_env.filters['nome_br'] = traduzir_pais
#   app.jinja_env.globals['traduzir_pais'] = traduzir_pais
#   app.jinja_env.globals['eh_selecao'] = eh_selecao
#   app.jinja_env.globals['formatar_rodada'] = formatar_rodada
# ============================================================
def obter_logo_time(time):
    if not time:
        return None
    return time.logo_url or None


def obter_bandeira_selecao(nome, tamanho=40):
    return None


def obter_logo_ou_bandeira(time, tamanho=40):
    if not time:
        return None
    return time.logo_url or None