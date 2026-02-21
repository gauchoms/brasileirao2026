from app import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

class Time(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    api_id = db.Column(db.Integer, unique=True, nullable=False)
    nome = db.Column(db.String(100), nullable=False)
    logo_url = db.Column(db.String(200), nullable=True)
    pais = db.Column(db.String(50), nullable=True)
    liga_principal = db.Column(db.String(100), nullable=True)
    ativo = db.Column(db.Boolean, default=True)
    ultima_atualizacao = db.Column(db.DateTime, default=db.func.now())
    jogos_casa = db.relationship('Jogo', foreign_keys='Jogo.time_casa_id', backref='time_casa', lazy=True)
    jogos_fora = db.relationship('Jogo', foreign_keys='Jogo.time_fora_id', backref='time_fora', lazy=True)

class Jogo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    api_id = db.Column(db.Integer, unique=True, nullable=False)
    competicao_id = db.Column(db.Integer, db.ForeignKey('competicao.id'), nullable=False)
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
    email = db.Column(db.String(120), unique=True, nullable=True)
    nome_completo = db.Column(db.String(200), nullable=True)
    password_hash = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    
    # Avatar
    avatar_tipo = db.Column(db.String(20), default='sugerido')  # sugerido, upload
    avatar_sugerido_id = db.Column(db.Integer, db.ForeignKey('avatar_sugerido.id'), nullable=True)
    avatar_custom_url = db.Column(db.String(200), nullable=True)
    
    # Time do coração
    time_coracao_id = db.Column(db.Integer, db.ForeignKey('time.id'), nullable=True)
    
    # Status
    tipo = db.Column(db.String(20), default='participante')  # admin, dono, participante
    status = db.Column(db.String(20), default='ativo')  # ativo, suspenso
    data_cadastro = db.Column(db.DateTime, default=db.func.now())
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class AvatarSugerido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(200), nullable=False)
    categoria = db.Column(db.String(50), nullable=False)

class Competicao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    ano = db.Column(db.Integer, nullable=False)
    tipo = db.Column(db.String(50), nullable=False)  # brasileirao, copa_mundo, libertadores
    api_league_id = db.Column(db.Integer, nullable=True)

class RegraPontuacao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    criador_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    pontos_placar_exato = db.Column(db.Integer, default=5)
    pontos_resultado_certo = db.Column(db.Integer, default=3)
    pontos_gols_time_casa = db.Column(db.Integer, default=1)
    pontos_gols_time_fora = db.Column(db.Integer, default=1)
    bonus_placar_perfeito = db.Column(db.Integer, default=0)
    publica = db.Column(db.Boolean, default=True)

class Bolao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    competicao_id = db.Column(db.Integer, db.ForeignKey('competicao.id'), nullable=False)
    dono_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    codigo_convite = db.Column(db.String(10), unique=True, nullable=False)
    regra_pontuacao_id = db.Column(db.Integer, db.ForeignKey('regra_pontuacao.id'), nullable=False)
    tipo_acesso = db.Column(db.String(20), default='publico')  # publico, privado
    status_pagamento = db.Column(db.String(20), default='pendente')  # pendente, aprovado, recusado
    valor_pago = db.Column(db.Float, default=0.0)
    data_pagamento = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default='ativo')  # ativo, encerrado
    data_criacao = db.Column(db.DateTime, default=db.func.now())

class SolicitacaoPagamento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    bolao_id = db.Column(db.Integer, db.ForeignKey('bolao.id'), nullable=True)
    valor = db.Column(db.Float, nullable=False)
    comprovante_url = db.Column(db.String(200), nullable=True)
    metodo_pagamento = db.Column(db.String(50), default='mercadopago')
    status = db.Column(db.String(20), default='pendente')
    data_solicitacao = db.Column(db.DateTime, default=db.func.now())
    data_aprovacao = db.Column(db.DateTime, nullable=True)
    aprovado_por = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=True)
    observacoes = db.Column(db.Text, nullable=True)
    mercadopago_payment_id = db.Column(db.String(100), nullable=True)

class ParticipanteBolao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bolao_id = db.Column(db.Integer, db.ForeignKey('bolao.id'), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    data_entrada = db.Column(db.DateTime, default=db.func.now())
    pontos_totais = db.Column(db.Integer, default=0)

class SolicitacaoEntrada(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bolao_id = db.Column(db.Integer, db.ForeignKey('bolao.id'), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    status = db.Column(db.String(20), default='pendente')
    data_solicitacao = db.Column(db.DateTime, default=db.func.now())
    data_resposta = db.Column(db.DateTime, nullable=True)
    respondido_por = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=True)

class Palpite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bolao_id = db.Column(db.Integer, db.ForeignKey('bolao.id'), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    jogo_id = db.Column(db.Integer, db.ForeignKey('jogo.id'), nullable=False)
    gols_casa_palpite = db.Column(db.Integer, nullable=False)
    gols_fora_palpite = db.Column(db.Integer, nullable=False)
    pontos_obtidos = db.Column(db.Integer, default=0)
    data_palpite = db.Column(db.DateTime, default=db.func.now())

class Chat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bolao_id = db.Column(db.Integer, db.ForeignKey('bolao.id'), nullable=False)
    tipo = db.Column(db.String(20), default='geral')  # geral, partida
    jogo_id = db.Column(db.Integer, db.ForeignKey('jogo.id'), nullable=True)

class Mensagem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.Integer, db.ForeignKey('chat.id'), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    texto = db.Column(db.Text, nullable=False)
    data_envio = db.Column(db.DateTime, default=db.func.now())
    editada = db.Column(db.Boolean, default=False)
    deletada = db.Column(db.Boolean, default=False)

class Reacao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mensagem_id = db.Column(db.Integer, db.ForeignKey('mensagem.id'), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    tipo = db.Column(db.String(10), nullable=False)  # emoji unicode

class Provocacao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    de_usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    para_usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    bolao_id = db.Column(db.Integer, db.ForeignKey('bolao.id'), nullable=False)
    texto = db.Column(db.String(200), nullable=False)
    jogo_relacionado_id = db.Column(db.Integer, db.ForeignKey('jogo.id'), nullable=True)
    data = db.Column(db.DateTime, default=db.func.now())

class Notificacao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    tipo = db.Column(db.String(50), nullable=False)
    mensagem = db.Column(db.String(200), nullable=False)
    lida = db.Column(db.Boolean, default=False)
    data = db.Column(db.DateTime, default=db.func.now())