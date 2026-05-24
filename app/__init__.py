from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from config import Config

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()

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

    # Importa a função de conversão de timezone
    from app.utils import converter_utc_brasilia

    # Filtro completo: "11/06/2026 às 16:00"
    @app.template_filter('brasilia')
    def brasilia_filter(data):
        if not data:
            return ''
        data_br = converter_utc_brasilia(data)
        if not data_br:
            # fallback: retorna a string original sem o "T"
            return str(data).replace('T', ' ')[:16]
        return data_br.strftime('%d/%m/%Y às %H:%M')

    # Filtro curto para cards compactos: "11/06 às 16:00"
    @app.template_filter('brasilia_curto')
    def brasilia_curto_filter(data):
        if not data:
            return ''
        data_br = converter_utc_brasilia(data)
        if not data_br:
            return str(data).replace('T', ' ')[:16]
        return data_br.strftime('%d/%m às %H:%M')

    return app


@login_manager.user_loader
def load_user(user_id):
    from app.models import Usuario
    return Usuario.query.get(int(user_id))
