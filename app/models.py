from app import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin


class Time(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    api_id = db.Column(db.Integer, unique=True, nullable=False)
    nome = db.Column(db.String(100), nullable=False)
    jogos_casa = db.relationship('Jogo', foreign_keys='Jogo.time_casa_id', backref='time_casa', lazy=True)
    jogos_fora = db.relationship('Jogo', foreign_keys='Jogo.time_fora_id', backref='time_fora', lazy=True)

class Jogo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    api_id = db.Column(db.Integer, unique=True, nullable=False)
    rodada = db.Column(db.String(50), nullable=False)
    time_casa_id = db.Column(db.Integer, db.ForeignKey('time.id'), nullable=False)
    time_fora_id = db.Column(db.Integer, db.ForeignKey('time.id'), nullable=False)
    data = db.Column(db.String(50), nullable=True)
    gols_casa = db.Column(db.Integer, nullable=True)
    gols_fora = db.Column(db.Integer, nullable=True)

class Projecao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    jogo_id = db.Column(db.Integer, db.ForeignKey('jogo.id'), nullable=False)
    time_id = db.Column(db.Integer, db.ForeignKey('time.id'), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)  # 'titulo', 'libertadores', 'rebaixamento'
    pontos = db.Column(db.Integer, nullable=True)    # 0, 1 ou 3

class Meta(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    time_id = db.Column(db.Integer, db.ForeignKey('time.id'), nullable=False)
    descricao = db.Column(db.String(50), nullable=False)  # 'titulo', 'libertadores', 'rebaixamento'
    pontos_alvo = db.Column(db.Integer, nullable=False)   # 68, 70 ou 45


class Usuario(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)