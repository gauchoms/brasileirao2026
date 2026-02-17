from app import db

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
    pontos_projetados = db.Column(db.Integer, nullable=True)  # 0, 1 ou 3

class Meta(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    time_id = db.Column(db.Integer, db.ForeignKey('time.id'), nullable=False)
    descricao = db.Column(db.String(50), nullable=False)  # 'titulo', 'libertadores', 'rebaixamento'
    pontos_alvo = db.Column(db.Integer, nullable=False)   # 68, 70 ou 45