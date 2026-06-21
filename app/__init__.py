from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from config import Config

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()

# ──────────────────────────────────────────────
# Seleções nacionais conhecidas na API Football
# (nomes em inglês, como vêm da API)
# ──────────────────────────────────────────────
SELECOES = {
    "Afghanistan","Albania","Algeria","Andorra","Angola","Antigua and Barbuda",
    "Argentina","Armenia","Australia","Austria","Azerbaijan","Bahamas","Bahrain",
    "Bangladesh","Barbados","Belarus","Belgium","Belize","Benin","Bhutan","Bolivia",
    "Bosnia and Herzegovina","Botswana","Brazil","Brunei","Bulgaria","Burkina Faso",
    "Burundi","Cabo Verde","Cambodia","Cameroon","Canada","Central African Republic",
    "Chad","Chile","China","Colombia","Comoros","Congo","Costa Rica","Croatia",
    "Cuba","Cyprus","Czech Republic","DR Congo","Denmark","Djibouti","Dominican Republic",
    "Ecuador","Egypt","El Salvador","England","Equatorial Guinea","Eritrea","Estonia",
    "Eswatini","Ethiopia","Fiji","Finland","France","Gabon","Gambia","Georgia",
    "Germany","Ghana","Greece","Grenada","Guatemala","Guinea","Guinea-Bissau","Guyana",
    "Haiti","Honduras","Hungary","Iceland","India","Indonesia","Iran","Iraq","Ireland",
    "Israel","Italy","Ivory Coast","Jamaica","Japan","Jordan","Kazakhstan","Kenya",
    "Kosovo","Kuwait","Kyrgyzstan","Laos","Latvia","Lebanon","Lesotho","Liberia",
    "Libya","Liechtenstein","Lithuania","Luxembourg","Madagascar","Malawi","Malaysia",
    "Maldives","Mali","Malta","Mauritania","Mauritius","Mexico","Moldova","Monaco",
    "Mongolia","Montenegro","Morocco","Mozambique","Myanmar","Namibia","Nepal",
    "Netherlands","New Zealand","Nicaragua","Niger","Nigeria","North Korea",
    "North Macedonia","Northern Ireland","Norway","Oman","Pakistan","Palestine",
    "Panama","Papua New Guinea","Paraguay","Peru","Philippines","Poland","Portugal",
    "Qatar","Republic of Ireland","Romania","Russia","Rwanda","Saint Kitts and Nevis",
    "Saint Lucia","Saint Vincent and the Grenadines","San Marino","Saudi Arabia",
    "Scotland","Senegal","Serbia","Sierra Leone","Singapore","Slovakia","Slovenia",
    "Somalia","South Africa","South Korea","South Sudan","Spain","Sri Lanka","Sudan",
    "Suriname","Sweden","Switzerland","Syria","Taiwan","Tajikistan","Tanzania",
    "Thailand","Togo","Trinidad and Tobago","Tunisia","Turkey","Turkmenistan","Uganda",
    "Ukraine","United Arab Emirates","United States","Uruguay","Uzbekistan",
    "Venezuela","Vietnam","Wales","Yemen","Zambia","Zimbabwe",
    # Nomes alternativos comuns na API
    "Korea Republic","Korea DPR","USA","IR Iran","Côte d'Ivoire",
    "Cape Verde","Trinidad & Tobago","Congo DR","Bosnia","Türkiye","Cape Verde Islands",
}

TRADUCOES = {
    "Afghanistan": "Afeganistão", "Albania": "Albânia", "Algeria": "Argélia",
    "Angola": "Angola", "Argentina": "Argentina", "Australia": "Austrália",
    "Austria": "Áustria", "Belgium": "Bélgica", "Bolivia": "Bolívia",
    "Bosnia and Herzegovina": "Bósnia e Herzegovina", "Bosnia": "Bósnia",
    "Brazil": "Brasil", "Bulgaria": "Bulgária", "Cameroon": "Camarões",
    "Canada": "Canadá", "Cape Verde Islands": "Cabo Verde", "Cabo Verde": "Cabo Verde",
    "Chile": "Chile", "China": "China", "Colombia": "Colômbia",
    "Congo": "Congo", "DR Congo": "RD Congo", "Congo DR": "RD Congo",
    "Costa Rica": "Costa Rica", "Croatia": "Croácia", "Cuba": "Cuba",
    "Czech Republic": "República Tcheca", "Denmark": "Dinamarca",
    "Ecuador": "Equador", "Egypt": "Egito", "El Salvador": "El Salvador",
    "England": "Inglaterra", "Ethiopia": "Etiópia", "Finland": "Finlândia",
    "France": "França", "Germany": "Alemanha", "Ghana": "Gana",
    "Greece": "Grécia", "Guatemala": "Guatemala", "Guinea": "Guiné",
    "Haiti": "Haiti", "Honduras": "Honduras", "Hungary": "Hungria",
    "Iceland": "Islândia", "India": "Índia", "Indonesia": "Indonésia",
    "Iran": "Irã", "IR Iran": "Irã", "Iraq": "Iraque", "Ireland": "Irlanda",
    "Republic of Ireland": "Irlanda", "Israel": "Israel", "Italy": "Itália",
    "Ivory Coast": "Costa do Marfim", "Côte d'Ivoire": "Costa do Marfim",
    "Jamaica": "Jamaica", "Japan": "Japão", "Jordan": "Jordânia",
    "Kenya": "Quênia", "Korea Republic": "Coreia do Sul",
    "South Korea": "Coreia do Sul", "Korea DPR": "Coreia do Norte",
    "North Korea": "Coreia do Norte", "Kuwait": "Kuwait",
    "Lebanon": "Líbano", "Libya": "Líbia", "Lithuania": "Lituânia",
    "Luxembourg": "Luxemburgo", "Malaysia": "Malásia", "Mali": "Mali",
    "Mexico": "México", "Morocco": "Marrocos", "Mozambique": "Moçambique",
    "Netherlands": "Holanda", "New Zealand": "Nova Zelândia",
    "Nicaragua": "Nicarágua", "Nigeria": "Nigéria",
    "North Macedonia": "Macedônia do Norte", "Northern Ireland": "Irlanda do Norte",
    "Norway": "Noruega", "Pakistan": "Paquistão", "Palestine": "Palestina",
    "Panama": "Panamá", "Paraguay": "Paraguai", "Peru": "Peru",
    "Philippines": "Filipinas", "Poland": "Polônia", "Portugal": "Portugal",
    "Qatar": "Catar", "Romania": "Romênia", "Russia": "Rússia",
    "Rwanda": "Ruanda", "Saudi Arabia": "Arábia Saudita",
    "Scotland": "Escócia", "Senegal": "Senegal", "Serbia": "Sérvia",
    "Slovakia": "Eslováquia", "Slovenia": "Eslovênia",
    "South Africa": "África do Sul", "Spain": "Espanha",
    "Sudan": "Sudão", "Sweden": "Suécia", "Switzerland": "Suíça",
    "Syria": "Síria", "Thailand": "Tailândia", "Togo": "Togo",
    "Trinidad and Tobago": "Trinidad e Tobago",
    "Trinidad & Tobago": "Trinidad e Tobago",
    "Tunisia": "Tunísia", "Turkey": "Turquia", "Türkiye": "Turquia", "Uganda": "Uganda",
    "Ukraine": "Ucrânia", "United Arab Emirates": "Emirados Árabes",
    "United States": "Estados Unidos", "USA": "Estados Unidos",
    "Uruguay": "Uruguai", "Uzbekistan":"Usbequistão","Venezuela": "Venezuela", "Vietnam": "Vietnã",
    "Wales": "País de Gales", "Yemen": "Iêmen", "Zambia": "Zâmbia",
    "Zimbabwe": "Zimbábue",
}



FLAG_EMOJIS = {
    "Brazil":"🇧🇷","Argentina":"🇦🇷","France":"🇫🇷","Germany":"🇩🇪",
    "Spain":"🇪🇸","England":"🏴","Portugal":"🇵🇹","Italy":"🇮🇹",
    "Netherlands":"🇳🇱","Belgium":"🇧🇪","Croatia":"🇭🇷","Uruguay":"🇺🇾",
    "Colombia":"🇨🇴","Mexico":"🇲🇽","Japan":"🇯🇵","South Korea":"🇰🇷",
    "Korea Republic":"🇰🇷","Australia":"🇦🇺","USA":"🇺🇸","United States":"🇺🇸",
    "Canada":"🇨🇦","Morocco":"🇲🇦","Senegal":"🇸🇳","Nigeria":"🇳🇬",
    "Ghana":"🇬🇭","Cameroon":"🇨🇲","South Africa":"🇿🇦","Egypt":"🇪🇬",
    "Tunisia":"🇹🇳","Algeria":"🇩🇿","Saudi Arabia":"🇸🇦","Iran":"🇮🇷",
    "IR Iran":"🇮🇷","Qatar":"🇶🇦","Switzerland":"🇨🇭","Denmark":"🇩🇰",
    "Sweden":"🇸🇪","Poland":"🇵🇱","Serbia":"🇷🇸","Turkey":"🇹🇷",
    "Ukraine":"🇺🇦","Czech Republic":"🇨🇿","Scotland":"🏴","Wales":"🏴",
    "Chile":"🇨🇱","Peru":"🇵🇪","Ecuador":"🇪🇨","Paraguay":"🇵🇾",
    "Bolivia":"🇧🇴","Venezuela":"🇻🇪","Panama":"🇵🇦","Costa Rica":"🇨🇷",
    "Honduras":"🇭🇳","Greece":"🇬🇷","Austria":"🇦🇹","Romania":"🇷🇴",
    "Hungary":"🇭🇺","Slovakia":"🇸🇰","Slovenia":"🇸🇮","Israel":"🇮🇱",
    "Ivory Coast":"🇨🇮","Mali":"🇲🇱","Togo":"🇹🇬","Rwanda":"🇷🇼",
    "Kenya":"🇰🇪","Angola":"🇦🇴","Cape Verde":"🇨🇻","Cabo Verde":"🇨🇻","Cape Verde Islands":"🇨🇻","Türkiye":"🇹🇷",
    "New Zealand":"🇳🇿","Bosnia and Herzegovina":"🇧🇦","Bosnia":"🇧🇦",
    "North Macedonia":"🇲🇰","Albania":"🇦🇱","Kosovo":"🇽🇰",
    "Montenegro":"🇲🇪","Uzbekistan":"🇺🇿","Jordan":"🇯🇴",
    "Iraq":"🇮🇶","Palestine":"🇵🇸","Kuwait":"🇰🇼",
    "Trinidad and Tobago":"🇹🇹","Trinidad & Tobago":"🇹🇹",
    "Jamaica":"🇯🇲","Haiti":"🇭🇹","El Salvador":"🇸🇻",
    "Guatemala":"🇬🇹","Nicaragua":"🇳🇮",
}

def flag_emoji(nome_pais):
    """Retorna emoji de bandeira para seleções nacionais."""
    return FLAG_EMOJIS.get(nome_pais, "")

def eh_selecao(nome):
    """Retorna True se o nome do time é uma seleção nacional."""
    return nome in SELECOES


def traduzir_pais(nome):
    """Traduz nome de país do inglês para português. Retorna original se não encontrar."""
    return TRADUCOES.get(nome, nome)


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)

    login_manager.init_app(app)
    login_manager.login_view = 'main.login'
    login_manager.login_message = 'Faça login para acessar esta página.'

    from app import routes
    app.register_blueprint(routes.bp)

    from app import routes_export
    app.register_blueprint(routes_export.bp_export)

    # ── Filtros de timezone ──────────────────────────────
    from app.utils import converter_utc_brasilia

    @app.template_filter('brasilia')
    def brasilia_filter(data):
        if not data:
            return ''
        data_br = converter_utc_brasilia(data)
        if not data_br:
            return str(data).replace('T', ' ')[:16]
        return data_br.strftime('%d/%m/%Y às %H:%M')

    @app.template_filter('brasilia_curto')
    def brasilia_curto_filter(data):
        if not data:
            return ''
        data_br = converter_utc_brasilia(data)
        if not data_br:
            return str(data).replace('T', ' ')[:16]
        return data_br.strftime('%d/%m às %H:%M')

    # ── Filtro sort_rodadas (ordena rodadas: numéricas por número, textuais alfabético) ──
    def sort_rodadas(rodadas):
        def key(r):
            try: return (0, int(str(r)))
            except: return (1, str(r))
        return sorted(rodadas, key=key)
    app.jinja_env.filters['sort_rodadas'] = sort_rodadas

    # ── Filtro timestamp_to_date (ms → dd/mm às HH:MM) ──
    def timestamp_to_date(ts):
        if not ts: return '—'
        try:
            from datetime import datetime
            import pytz
            dt = datetime.fromtimestamp(int(ts), tz=pytz.timezone('America/Sao_Paulo'))
            return dt.strftime('%d/%m às %H:%M')
        except:
            return '—'
    app.jinja_env.filters['timestamp_to_date'] = timestamp_to_date

    # ── Globals do Jinja2 (disponíveis em todos os templates) ──
    app.jinja_env.globals['eh_selecao'] = eh_selecao
    app.jinja_env.globals['traduzir_pais'] = traduzir_pais
    app.jinja_env.globals['flag_emoji'] = flag_emoji

    # ── APScheduler (backup do Cron Job do Render) ──────────
    # Cron Job roda no :00 de cada hora; scheduler interno roda no :30
    # para não concorrerem. Só inicia fora de modo teste/migrate.
    import os as _os
    if not app.config.get('TESTING') and _os.environ.get('FLASK_ENV') != 'testing':
        try:
            from app.scheduler import iniciar_scheduler
            iniciar_scheduler(app)
        except Exception as e:
            print(f"[SCHEDULER] Aviso: não foi possível iniciar: {e}")

    return app


@login_manager.user_loader
def load_user(user_id):
    from app.models import Usuario
    return Usuario.query.get(int(user_id))
