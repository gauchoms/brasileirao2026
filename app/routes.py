
from flask import Blueprint, render_template, request, redirect, url_for, jsonify, flash
from app import db
from datetime import datetime
from app.models import Time, Jogo, Projecao, Meta, Competicao, Bolao, ParticipanteBolao, RegraPontuacao,Palpite,SolicitacaoEntrada
import os
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from functools import wraps
from app.utils import converter_utc_brasilia


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect('/login?next=' + request.path)
        if not current_user.is_admin:
            return jsonify({'erro': 'Acesso negado. Apenas administradores.'}), 403
        return f(*args, **kwargs)
    return decorated_function

bp = Blueprint('main', __name__)

METAS = {
    'titulo': 80,
    'libertadores': 70,
    'rebaixamento': 45
}


def calcular_pontos_palpite(palpite, jogo, regra):
    """
    Calcula os pontos obtidos em um palpite baseado na regra de pontuação.
    Sistema acumulativo: soma todos os acertos.
    """
    pontos = 0
    
    # Determina resultado real
    if jogo.gols_casa > jogo.gols_fora:
        resultado_real = 'casa'
        gols_vencedor_real = jogo.gols_casa
        gols_perdedor_real = jogo.gols_fora
    elif jogo.gols_fora > jogo.gols_casa:
        resultado_real = 'fora'
        gols_vencedor_real = jogo.gols_fora
        gols_perdedor_real = jogo.gols_casa
    else:
        resultado_real = 'empate'
        gols_vencedor_real = None
        gols_perdedor_real = None
    
    # Determina resultado do palpite
    if palpite.gols_casa_palpite > palpite.gols_fora_palpite:
        resultado_palpite = 'casa'
        gols_vencedor_palpite = palpite.gols_casa_palpite
        gols_perdedor_palpite = palpite.gols_fora_palpite
    elif palpite.gols_fora_palpite > palpite.gols_casa_palpite:
        resultado_palpite = 'fora'
        gols_vencedor_palpite = palpite.gols_fora_palpite
        gols_perdedor_palpite = palpite.gols_casa_palpite
    else:
        resultado_palpite = 'empate'
        gols_vencedor_palpite = None
        gols_perdedor_palpite = None
    
    # Acertou o resultado?
    acertou_resultado = (resultado_real == resultado_palpite)
    
    if acertou_resultado:
        # Ganha pontos por acertar o resultado
        pontos += regra.pontos_resultado
        
        # Acertos adicionais
        if resultado_real != 'empate':
            # VITÓRIAS: pontua vencedor e perdedor separadamente
            if gols_vencedor_real == gols_vencedor_palpite:
                pontos += regra.pontos_gols_vencedor
            
            if gols_perdedor_real == gols_perdedor_palpite:
                pontos += regra.pontos_gols_perdedor
        else:
            # EMPATES: pontua se acertou os gols de ambos os times
            if palpite.gols_casa_palpite == jogo.gols_casa:
                pontos += regra.pontos_gols_vencedor
            
            if palpite.gols_fora_palpite == jogo.gols_fora:
                pontos += regra.pontos_gols_perdedor
        
        # Acertou diferença de gols?
        diferenca_real = abs(jogo.gols_casa - jogo.gols_fora)
        diferenca_palpite = abs(palpite.gols_casa_palpite - palpite.gols_fora_palpite)
        if diferenca_real == diferenca_palpite:
            pontos += regra.pontos_diferenca_gols
            # Bônus por jogos elásticos
        if regra.ativar_bonus_gols:
            total_gols = jogo.gols_casa + jogo.gols_fora
            if total_gols > regra.limite_gols_bonus:
                gols_extras = total_gols - regra.limite_gols_bonus
                pontos += gols_extras * regra.pontos_por_gol_extra

    
    else:
        # Errou o resultado
        if not regra.requer_resultado_correto:
            # Checkbox desmarcado: pontua mesmo errando resultado
            if resultado_real != 'empate' and resultado_palpite != 'empate':
                # Ambos preveram vitória (mas de times diferentes)
                # Verifica se acertou os números mesmo invertidos
                if gols_vencedor_real == gols_vencedor_palpite:
                    pontos += regra.pontos_gols_vencedor
                
                if gols_perdedor_real == gols_perdedor_palpite:
                    pontos += regra.pontos_gols_perdedor
            
            # Diferença de gols
            diferenca_real = abs(jogo.gols_casa - jogo.gols_fora)
            diferenca_palpite = abs(palpite.gols_casa_palpite - palpite.gols_fora_palpite)
            if diferenca_real == diferenca_palpite:
                pontos += regra.pontos_diferenca_gols
            
        
        # Se checkbox marcado: pontos = 0 (já está zerado)
    
    
    return pontos

@bp.route('/admin/boloes')
@admin_required
def admin_boloes():
    """
    Lista TODOS os bolões do sistema (ADMIN ONLY)
    """
    from app.models import Bolao
    
    boloes = Bolao.query.order_by(Bolao.data_criacao.desc()).all()
    
    return render_template('admin_boloes.html', boloes=boloes)

@bp.route('/')
def index():
    return render_template('index.html')

@bp.route('/projecoes')
def projecoes():
    # Busca competições disponíveis para projeção
    competicoes_disponiveis = Competicao.query.filter(
        (Competicao.uso == 'projecao') | (Competicao.uso == 'ambos')
    ).all()
    
    # Competição selecionada (default: primeira disponível)
    competicao_id = request.args.get('competicao_id', type=int)
    if not competicao_id and competicoes_disponiveis:
        competicao_id = competicoes_disponiveis[0].id
    
    # Busca apenas times que jogam na competição selecionada
    if competicao_id:
        times_ids = db.session.query(Jogo.time_casa_id).filter_by(competicao_id=competicao_id).union(
            db.session.query(Jogo.time_fora_id).filter_by(competicao_id=competicao_id)
        ).distinct()
        times = Time.query.filter(Time.id.in_(times_ids)).order_by(Time.nome).all()
    else:
        times = []
    



    time_id = request.args.get('time_id', type=int)
    projecao_selecionada = request.args.get('projecao', 'titulo')

    time_selecionado = None
    jogos = []
    pontos_projetados = 0
    meta = METAS.get(projecao_selecionada, 80)

    if time_id and competicao_id:
        time_selecionado = Time.query.get(time_id)

        # Filtra jogos pela competição selecionada
        todos_jogos = Jogo.query.filter(
            ((Jogo.time_casa_id == time_id) | (Jogo.time_fora_id == time_id)),
            Jogo.competicao_id == competicao_id
        ).all()

        for jogo in todos_jogos:
            eh_casa = jogo.time_casa_id == time_id
            adversario_obj = Time.query.get(jogo.time_fora_id if eh_casa else jogo.time_casa_id)

            # Extrai número da rodada
            rodada_num = ''.join(filter(str.isdigit, jogo.rodada))

            # Busca projeção existente
            proj = Projecao.query.filter_by(
                jogo_id=jogo.id,
                time_id=time_id,
                tipo=projecao_selecionada
            ).first()

            projecao_atual = proj.pontos if proj else None
            if projecao_atual is not None:
                pontos_projetados += projecao_atual

            jogos.append({
                'jogo_id': jogo.id,
                'rodada_num': rodada_num,
                'adversario': adversario_obj.nome if adversario_obj else '?',
                'casa': eh_casa,
                'projecao_atual': projecao_atual
            })

        jogos.sort(key=lambda x: int(x['rodada_num']) if x['rodada_num'].isdigit() else 0)

    return render_template('projecoes.html',
        competicoes=competicoes_disponiveis,
        competicao_selecionada=competicao_id,
        times=times,
        time_selecionado=time_selecionado,
        projecao_selecionada=projecao_selecionada,
        jogos=jogos,
        pontos_projetados=pontos_projetados,
        meta=meta
    )


@bp.route('/salvar_projecao', methods=['POST'])
@admin_required
def salvar_projecao():
    data = request.get_json()
    jogo_id = data.get('jogo_id')
    time_id = data.get('time_id')
    tipo = data.get('projecao')
    pontos = data.get('pontos')

    proj = Projecao.query.filter_by(
        jogo_id=jogo_id,
        time_id=time_id,
        tipo=tipo
    ).first()

    if proj:
        proj.pontos = pontos
    else:
        proj = Projecao(
            jogo_id=jogo_id,
            time_id=time_id,
            tipo=tipo,
            pontos=pontos
        )
        db.session.add(proj)

    db.session.commit()

    # Calcula total de pontos projetados para esse time/projeção
    total = db.session.query(db.func.sum(Projecao.pontos)).filter_by(
        time_id=time_id,
        tipo=tipo
    ).scalar() or 0

    return jsonify({'sucesso': True, 'total_pontos': total})

@bp.route('/atualizar_resultados', methods=['POST'])
@admin_required
def atualizar_resultados():
    from app.api import get_resultados_brasileirao
    from app.models import Palpite, Bolao, ParticipanteBolao, Competicao

    # Busca TODAS as competições cadastradas
    competicoes = Competicao.query.all()
    
    novos_atualizados = 0
    ja_tinham_placar = 0
    palpites_calculados = 0

    for comp in competicoes:
        try:
            # Busca resultados de cada competição
            data = get_resultados_brasileirao(league_id=comp.api_league_id, season=comp.ano)
            jogos = data.get('response', [])
            
            for fixture in jogos:
                api_id = fixture['fixture']['id']
                gols_casa = fixture['goals']['home']
                gols_fora = fixture['goals']['away']

                jogo = Jogo.query.filter_by(api_id=api_id).first()
                
                if jogo and gols_casa is not None and gols_fora is not None:
                    tinha_placar = jogo.gols_casa is not None and jogo.gols_fora is not None
                    
                    if not tinha_placar:
                        # Jogo NOVO com resultado
                        jogo.gols_casa = gols_casa
                        jogo.gols_fora = gols_fora
                        novos_atualizados += 1
                        
                        # CALCULA PONTOS de todos os palpites deste jogo
                        palpites = Palpite.query.filter_by(jogo_id=jogo.id).all()
                        for palpite in palpites:
                            bolao = Bolao.query.get(palpite.bolao_id)
                            regra = RegraPontuacao.query.get(bolao.regra_pontuacao_id)
                            
                            # Calcula pontos
                            pontos = calcular_pontos_palpite(palpite, jogo, regra)
                            palpite.pontos_obtidos = pontos
                            palpites_calculados += 1
                            
                            # Atualiza pontos totais do participante
                            participante = ParticipanteBolao.query.filter_by(
                                bolao_id=palpite.bolao_id,
                                usuario_id=palpite.usuario_id
                            ).first()
                            if participante:
                                # Recalcula total somando todos os palpites
                                total = db.session.query(db.func.sum(Palpite.pontos_obtidos)).filter_by(
                                    bolao_id=palpite.bolao_id,
                                    usuario_id=palpite.usuario_id
                                ).scalar() or 0
                                participante.pontos_totais = total
                        
                    elif jogo.gols_casa != gols_casa or jogo.gols_fora != gols_fora:
                        # Placar mudou (raro)
                        jogo.gols_casa = gols_casa
                        jogo.gols_fora = gols_fora
                        ja_tinham_placar += 1
        
        except Exception as e:
            print(f"Erro ao buscar resultados da liga {comp.nome}: {e}")
            continue

    db.session.commit()
    
    return jsonify({
        'sucesso': True,
        'novos_resultados': novos_atualizados,
        'atualizados': ja_tinham_placar,
        'palpites_calculados': palpites_calculados
    })



@bp.route('/dashboard')
def dashboard():
    # Busca competições disponíveis para projeção
 # Busca apenas competições disponíveis para dashboard
    competicoes = Competicao.query.filter_by(disponivel_dashboard=True).all()
    
    # Se não tiver nenhuma, usa Série A como fallback
    if not competicoes:
        competicoes = Competicao.query.filter(
            (Competicao.nome.like('%Serie A%')) | (Competicao.nome.like('%Série A%'))
        ).all()
    
    # Competição selecionada (default: primeira disponível)
    competicao_id = request.args.get('competicao_id', type=int)
    if not competicao_id and competicoes:
        competicao_id = competicoes[0].id
    
    # Busca apenas times que jogam na competição selecionada
    if competicao_id:
        times_ids = db.session.query(Jogo.time_casa_id).filter_by(competicao_id=competicao_id).union(
            db.session.query(Jogo.time_fora_id).filter_by(competicao_id=competicao_id)
        ).distinct()
        times = Time.query.filter(Time.id.in_(times_ids)).order_by(Time.nome).all()
    else:
        times = []
    
    time_id = request.args.get('time_id', type=int)
    ordenar_por = request.args.get('ordenar', 'pontos_reais')
    time_selecionado = None
    detalhe = None

    METAS_DICT = {
        'titulo': 80,
        'libertadores': 70,
        'rebaixamento': 45
    }

    tabela = []
    for time in times:
        # Pontos reais acumulados (só jogos da competição selecionada)
        pontos_reais = 0
        jogos_time = Jogo.query.filter(
            ((Jogo.time_casa_id == time.id) | (Jogo.time_fora_id == time.id)),
            Jogo.competicao_id == competicao_id
        ).all()

        for jogo in jogos_time:
            if jogo.gols_casa is not None and jogo.gols_fora is not None:
                eh_casa = jogo.time_casa_id == time.id
                if eh_casa:
                    if jogo.gols_casa > jogo.gols_fora:
                        pontos_reais += 3
                    elif jogo.gols_casa == jogo.gols_fora:
                        pontos_reais += 1
                else:
                    if jogo.gols_fora > jogo.gols_casa:
                        pontos_reais += 3
                    elif jogo.gols_casa == jogo.gols_fora:
                        pontos_reais += 1

        cenarios = {}
        for tipo, meta in METAS_DICT.items():
            pontos_proj = db.session.query(db.func.sum(Projecao.pontos)).join(
                Jogo, Projecao.jogo_id == Jogo.id
            ).filter(
                Projecao.time_id == time.id,
                Projecao.tipo == tipo,
                Jogo.competicao_id == competicao_id
            ).scalar() or 0

            # Pontos projetados até os jogos já disputados
            jogos_disputados_ids = [
                j.id for j in jogos_time
                if j.gols_casa is not None and j.gols_fora is not None
            ]
            pontos_proj_ate_agora = db.session.query(db.func.sum(Projecao.pontos)).filter(
                Projecao.time_id == time.id,
                Projecao.tipo == tipo,
                Projecao.jogo_id.in_(jogos_disputados_ids)
            ).scalar() or 0

            pct = round((pontos_reais / pontos_proj_ate_agora * 100), 1) if pontos_proj_ate_agora > 0 else 0
            diff = pontos_reais - pontos_proj_ate_agora

            cenarios[tipo] = {
                'projetado_total': pontos_proj,
                'projetado_ate_agora': pontos_proj_ate_agora,
                'real': pontos_reais,
                'diff': diff,
                'pct': pct,
                'meta': meta
            }

        tabela.append({
            'time': time,
            'pontos_reais': pontos_reais,
            'cenarios': cenarios
        })

    # Ordenação
    if ordenar_por == 'pontos_reais':
        tabela.sort(key=lambda x: x['pontos_reais'], reverse=True)
    elif ordenar_por == 'titulo':
        tabela.sort(key=lambda x: x['cenarios']['titulo']['pct'], reverse=True)
    elif ordenar_por == 'libertadores':
        tabela.sort(key=lambda x: x['cenarios']['libertadores']['pct'], reverse=True)
    elif ordenar_por == 'rebaixamento':
        tabela.sort(key=lambda x: x['cenarios']['rebaixamento']['pct'], reverse=True)

    # Detalhe por time
    if time_id:
        time_selecionado = Time.query.get(time_id)
        jogos_time = Jogo.query.filter(
            ((Jogo.time_casa_id == time_id) | (Jogo.time_fora_id == time_id)),
            Jogo.competicao_id == competicao_id
        ).all()

        evolucao = []
        pontos_reais_acum = 0
        proj_titulo_acum = 0
        proj_lib_acum = 0
        proj_rebaixa_acum = 0

        jogos_ordenados = sorted(jogos_time, key=lambda j: int(''.join(filter(str.isdigit, j.rodada))) if any(c.isdigit() for c in j.rodada) else 0)

        for jogo in jogos_ordenados:
            if jogo.gols_casa is None:
                continue

            eh_casa = jogo.time_casa_id == time_id
            if eh_casa:
                if jogo.gols_casa > jogo.gols_fora:
                    pontos_reais_acum += 3
                elif jogo.gols_casa == jogo.gols_fora:
                    pontos_reais_acum += 1
            else:
                if jogo.gols_fora > jogo.gols_casa:
                    pontos_reais_acum += 3
                elif jogo.gols_casa == jogo.gols_fora:
                    pontos_reais_acum += 1

            for tipo in ['titulo', 'libertadores', 'rebaixamento']:
                proj = Projecao.query.filter_by(jogo_id=jogo.id, time_id=time_id, tipo=tipo).first()
                pts = proj.pontos if proj else 0
                if tipo == 'titulo':
                    proj_titulo_acum += pts
                elif tipo == 'libertadores':
                    proj_lib_acum += pts
                else:
                    proj_rebaixa_acum += pts

            rodada_num = ''.join(filter(str.isdigit, jogo.rodada))
            evolucao.append({
                'rodada': rodada_num,
                'real': pontos_reais_acum,
                'titulo': proj_titulo_acum,
                'libertadores': proj_lib_acum,
                'rebaixamento': proj_rebaixa_acum
            })

        detalhe = {
            'evolucao': evolucao,
            'cenarios': next((t['cenarios'] for t in tabela if t['time'].id == time_id), {})
        }

    return render_template('dashboard.html',
        competicoes=competicoes,
        competicao_selecionada=competicao_id,
        times=times,
        tabela=tabela,
        time_selecionado=time_selecionado,
        detalhe=detalhe,
        ordenar_por=ordenar_por
    )






@bp.route('/setup_inicial_render')
def setup_inicial_render():
    try:
        # Força criação das tabelas
        from app import db
        from app.models import Time, Jogo, Projecao, Meta, Usuario
        db.create_all()
        
        # Verifica se já tem times
        count_times = Time.query.count()
        count_jogos = Jogo.query.count()
        count_usuarios = Usuario.query.count()
        
        return jsonify({
            'status': 'ok',
            'times_cadastrados': count_times,
            'jogos_cadastrados': count_jogos,
            'usuarios_cadastrados': count_usuarios,
            'mensagem': 'Tabelas criadas. Use /criar_admin, /importar_times e /importar_jogos'
        })
    except Exception as e:
        return jsonify({'erro': str(e)}), 500


@bp.route('/importar_times')
@admin_required
def importar_times():
    from app.api import get_jogos_brasileirao, processar_jogos
    
    try:
        if Time.query.count() > 0:
            return jsonify({'mensagem': 'Times já importados', 'total': Time.query.count()})
        
        data = get_jogos_brasileirao()
        
        if not data or 'response' not in data:
            return jsonify({'erro': 'API não retornou dados', 'data': str(data)[:200]})
        
        jogos = processar_jogos(data)
        
        if not jogos:
            return jsonify({'erro': 'Nenhum jogo processado', 'response_count': len(data.get('response', []))})
        
        times_unicos = {}
        for jogo in jogos:
            times_unicos[jogo['time_casa_id']] = jogo['time_casa']
            times_unicos[jogo['time_fora_id']] = jogo['time_fora']
        
        for api_id, nome in times_unicos.items():
            time = Time(api_id=api_id, nome=nome)
            db.session.add(time)
        
        db.session.commit()
        return jsonify({'sucesso': True, 'times_importados': len(times_unicos)})
    except Exception as e:
        return jsonify({'erro': str(e)}), 500


@bp.route('/importar_jogos')
@admin_required
def importar_jogos():
    from app.api import get_jogos_brasileirao, processar_jogos
    
    if Jogo.query.count() > 0:
        return jsonify({'mensagem': 'Jogos já importados', 'total': Jogo.query.count()})
    
    data = get_jogos_brasileirao()
    jogos_data = processar_jogos(data)
    
    times_map = {t.api_id: t.id for t in Time.query.all()}
    
    for jogo in jogos_data:
        novo_jogo = Jogo(
            api_id=jogo['api_id'],
            rodada=jogo['rodada'],
            time_casa_id=times_map[jogo['time_casa_id']],
            time_fora_id=times_map[jogo['time_fora_id']],
            data=jogo['data'],
            gols_casa=jogo['gols_casa'],
            gols_fora=jogo['gols_fora']
        )
        db.session.add(novo_jogo)
    
    db.session.commit()
    return jsonify({'sucesso': True, 'jogos_importados': len(jogos_data)})

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        from app.models import Usuario
        login_input = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        print(f"[DEBUG LOGIN] Input: '{login_input}'")
        
        # Busca por username OU email
        user = Usuario.query.filter(
            (Usuario.username == login_input) | (Usuario.email == login_input)
        ).first()
        
        print(f"[DEBUG LOGIN] Usuário encontrado: {user}")
        if user:
            print(f"[DEBUG LOGIN] check_password result: {user.check_password(password)}")
            print(f"[DEBUG LOGIN] Hash atual: {user.password_hash[:30]}")
        
        if user and user.check_password(password):
            login_user(user)
            return redirect(request.args.get('next') or '/')
        
        return render_template('login.html', erro='Usuário ou senha incorretos')
    
    return render_template('login.html')

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/')

@bp.route('/esqueci_senha', methods=['GET', 'POST'])
def esqueci_senha():
    from app.models import Usuario
    import secrets
    from datetime import datetime, timedelta

    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        usuario = Usuario.query.filter_by(email=email).first()

        # Sempre mostra a mesma mensagem (segurança)
        mensagem = 'Se este email estiver cadastrado, você receberá as instruções em breve.'

        if usuario:
            token = secrets.token_urlsafe(32)
            usuario.reset_token = token
            usuario.reset_token_expira = datetime.utcnow() + timedelta(hours=1)
            db.session.commit()

            from app.email import email_recuperar_senha
            email_recuperar_senha(usuario, token)

        return render_template('esqueci_senha.html', mensagem=mensagem)

    return render_template('esqueci_senha.html')
@bp.route('/redefinir_senha/<token>', methods=['GET', 'POST'])
def redefinir_senha(token):
    from app.models import Usuario
    from datetime import datetime

    usuario = Usuario.query.filter_by(reset_token=token).first()

    # Valida token
    if not usuario or not usuario.reset_token_expira or usuario.reset_token_expira < datetime.utcnow():
        return render_template('redefinir_senha.html', token_invalido=True)

    if request.method == 'POST':
        nova_senha = request.form.get('nova_senha', '')
        confirmar = request.form.get('confirmar_senha', '')

        if len(nova_senha) < 6:
            return render_template('redefinir_senha.html', token=token, erro='A senha deve ter pelo menos 6 caracteres.')

        if nova_senha != confirmar:
            return render_template('redefinir_senha.html', token=token, erro='As senhas não coincidem.')

        print(f"[DEBUG] Hash ANTES: {usuario.password_hash[:30]}")
        usuario.set_password(nova_senha)
        usuario.reset_token = None
        usuario.reset_token_expira = None
        db.session.add(usuario)
        db.session.commit()
        db.session.refresh(usuario)
        print(f"[DEBUG] Hash DEPOIS: {usuario.password_hash[:30]}")
        print(f"[DEBUG] Usuario ID: {usuario.id}, username: {usuario.username}")

        return render_template('redefinir_senha.html', sucesso=True)

    return render_template('redefinir_senha.html', token=token)



@bp.route('/criar_admin')
def criar_admin():
    from app.models import Usuario
    
    # Verifica se já existe admin
    if Usuario.query.filter_by(is_admin=True).first():
        return jsonify({'mensagem': 'Já existe um administrador cadastrado'})
    
    admin = Usuario(username='admin', is_admin=True)
    admin.set_password('admin123')  # TROQUE ESSA SENHA DEPOIS!
    db.session.add(admin)
    db.session.commit()
    
    return jsonify({'sucesso': True, 'mensagem': 'Admin criado! Username: admin, Senha: admin123'})

@bp.route('/admin/competicoes')
@admin_required
def admin_competicoes():
    competicoes = Competicao.query.all()
    return render_template('admin/competicoes.html', competicoes=competicoes)

@bp.route('/admin/listar_ligas_api')
@admin_required
def admin_listar_ligas_api():
    from app.api import listar_ligas_disponiveis
    
    ano = request.args.get('ano', 2026, type=int)
    pais_filtro = request.args.get('pais', 'todos')
    
    ligas = listar_ligas_disponiveis(ano)
    
    # Filtra por país se selecionado
    if pais_filtro != 'todos':
        ligas_filtradas = [l for l in ligas if l['pais'] == pais_filtro]
    else:
        # Mostra todas, mas filtra só League e Cup
        ligas_filtradas = [l for l in ligas if l['tipo'] in ['League', 'Cup']]
    
    # Extrai lista única de países para o filtro
    paises_disponiveis = sorted(list(set([l['pais'] for l in ligas if l['tipo'] in ['League', 'Cup']])))
    
    return render_template('admin/listar_ligas.html', 
                         ligas=ligas_filtradas, 
                         ano=ano, 
                         pais_filtro=pais_filtro,
                         paises=paises_disponiveis)


@bp.route('/admin/importar_competicao/<int:league_id>/<int:ano>')
@admin_required
def admin_importar_competicao(league_id, ano):
    from app.api import get_jogos_competicao, processar_jogos, listar_ligas_disponiveis
    
    # Busca informações da liga
    ligas = listar_ligas_disponiveis(ano)
    liga_info = next((l for l in ligas if l['api_id'] == league_id), None)
    
    if not liga_info:
        return jsonify({'erro': 'Liga não encontrada'}), 404
    
    # Cria a competição
    competicao = Competicao.query.filter_by(api_league_id=league_id, ano=ano).first()
    if not competicao:
        competicao = Competicao(
            nome=f"{liga_info['nome']} {ano}",
            ano=ano,
            tipo=liga_info['tipo'].lower(),
            api_league_id=league_id
        )
        db.session.add(competicao)
        db.session.commit()
    
    # Importa jogos
    data = get_jogos_competicao(league_id, ano)
    jogos = processar_jogos(data)
    
    times_cadastrados = {}
    jogos_novos = 0
    
    for jogo in jogos:
        # Cadastra times
        for key in ['time_casa_id', 'time_fora_id']:
            api_id = jogo[key]
            nome = jogo['time_casa'] if key == 'time_casa_id' else jogo['time_fora']
            
            if api_id not in times_cadastrados:
                logo = jogo['logo_casa'] if key == 'time_casa_id' else jogo['logo_fora']
                time = Time.query.filter_by(api_id=api_id).first()
                if not time:
                    from app.api import upload_logo_cloudinary
                    logo_cl = upload_logo_cloudinary(api_id, logo) if logo else None
                    time = Time(api_id=api_id, nome=nome, logo_url=logo_cl or logo)
                    db.session.add(time)
                    db.session.flush()
                elif logo and not time.logo_url:
                    from app.api import upload_logo_cloudinary
                    logo_cl = upload_logo_cloudinary(api_id, logo)
                    time.logo_url = logo_cl or logo
                times_cadastrados[api_id] = time.id
        
        # Cadastra jogo
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
            jogos_novos += 1
    
    db.session.commit()
    
    return jsonify({
        'sucesso': True,
        'competicao': competicao.nome,
        'jogos_importados': jogos_novos,
        'times_total': len(times_cadastrados)
    })

@bp.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        from app.models import Usuario
        
        nome_completo = request.form.get('nome_completo')
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Verifica se usuário já existe
        if Usuario.query.filter_by(username=username).first():
            return render_template('registro.html', erro='Usuário já existe')
        
        if Usuario.query.filter_by(email=email).first():
            return render_template('registro.html', erro='E-mail já cadastrado')
        
        # Cria novo usuário
        novo_usuario = Usuario(
            username=username,
            email=email,
            nome_completo=nome_completo,
            tipo='participante'
        )
        novo_usuario.set_password(password)
        # Registra aceite dos termos
        novo_usuario.termos_aceitos_em = db.func.now()
        db.session.add(novo_usuario)
        db.session.commit()
        
        # Envia email de boas-vindas
        if novo_usuario.email:
            from app.email import email_boas_vindas
            email_boas_vindas(novo_usuario)
        
               
        # Faz login automaticamente
        login_user(novo_usuario)
        
        # ✅ CORREÇÃO: Redireciona para o bolão se veio de um link de convite
        next_url = request.args.get('next')
        if next_url:
            return redirect(next_url)
        
        return redirect('/perfil')
    
    # ✅ CORREÇÃO: Passa o parâmetro next para o template
    next_url = request.args.get('next', '')
    return render_template('registro.html', next_url=next_url)

@bp.route('/perfil', methods=['GET', 'POST'])
@login_required
def perfil():
    times = Time.query.filter_by(ativo=True).order_by(Time.nome).all()
    
    print(f"DEBUG: avatar_tipo={current_user.avatar_tipo}, avatar_sugerido_id={current_user.avatar_sugerido_id}")
    
    if request.method == 'POST':
        # Atualiza informações básicas
        current_user.nome_completo = request.form.get('nome_completo')
        current_user.email = request.form.get('email')
        
        # Atualiza avatar
        avatar_tipo = request.form.get('avatar_tipo')
        current_user.avatar_tipo = avatar_tipo
        
        if avatar_tipo == 'sugerido':
            current_user.avatar_sugerido_id = request.form.get('avatar_sugerido_id', type=int)
            current_user.avatar_custom_url = None
        elif avatar_tipo == 'upload':
            file = request.files.get('avatar_file')
            if file and file.filename:
                import cloudinary
                import cloudinary.uploader
                import os

                cloudinary.config(
                    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
                    api_key=os.getenv('CLOUDINARY_API_KEY'),
                    api_secret=os.getenv('CLOUDINARY_API_SECRET')
                )

                resultado = cloudinary.uploader.upload(
                    file,
                    public_id=f"avatars/user_{current_user.id}",
                    overwrite=True,
                    transformation=[
                        {'width': 200, 'height': 200, 'crop': 'fill', 'gravity': 'face'}
                    ]
                )

                current_user.avatar_custom_url = resultado['secure_url']
                current_user.avatar_sugerido_id = None
        
        # Atualiza time do coração
        time_id = request.form.get('time_coracao_id')
        current_user.time_coracao_id = int(time_id) if time_id else None
        
        db.session.commit()
        
        return redirect('/')
        
    
    return render_template('perfil.html', times=times)


@bp.route('/migrar_banco_render')
def migrar_banco_render():
    try:
        from sqlalchemy import text
        
        # Cria todas as tabelas novas
        db.create_all()
        
        # Adiciona colunas que podem estar faltando na tabela usuario
        comandos = [
            "ALTER TABLE usuario ADD COLUMN IF NOT EXISTS nome_completo VARCHAR(200)",
            "ALTER TABLE usuario ADD COLUMN IF NOT EXISTS email VARCHAR(120)",
            "ALTER TABLE usuario ADD COLUMN IF NOT EXISTS avatar_tipo VARCHAR(20) DEFAULT 'sugerido'",
            "ALTER TABLE usuario ADD COLUMN IF NOT EXISTS avatar_sugerido_id INTEGER",
            "ALTER TABLE usuario ADD COLUMN IF NOT EXISTS avatar_custom_url VARCHAR(200)",
            "ALTER TABLE usuario ADD COLUMN IF NOT EXISTS time_coracao_id INTEGER",
            "ALTER TABLE usuario ADD COLUMN IF NOT EXISTS tipo VARCHAR(20) DEFAULT 'participante'",
            "ALTER TABLE usuario ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'ativo'",
            "ALTER TABLE usuario ADD COLUMN IF NOT EXISTS data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
            "ALTER TABLE jogo ADD COLUMN IF NOT EXISTS competicao_id INTEGER",
            "ALTER TABLE jogo ADD COLUMN IF NOT EXISTS competicao_id INTEGER",
            "ALTER TABLE time ADD COLUMN IF NOT EXISTS logo_url VARCHAR(200)",
            "ALTER TABLE time ADD COLUMN IF NOT EXISTS pais VARCHAR(50)",
            "ALTER TABLE time ADD COLUMN IF NOT EXISTS liga_principal VARCHAR(100)",
            "ALTER TABLE time ADD COLUMN IF NOT EXISTS ativo BOOLEAN DEFAULT TRUE",
            "ALTER TABLE time ADD COLUMN IF NOT EXISTS ultima_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
]


        for cmd in comandos:
            db.session.execute(text(cmd))
        
        db.session.commit()
        
        # Conta quantas tabelas existem
        resultado = db.session.execute(text("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'"))
        total_tabelas = resultado.scalar()
        
        return jsonify({
            'sucesso': True, 
            'mensagem': 'Banco atualizado!',
            'total_tabelas': total_tabelas
        })
    except Exception as e:
        return jsonify({'erro': str(e)}), 500


@bp.route('/meus_boloes')
@login_required
def meus_boloes():
    from app.models import Bolao, ParticipanteBolao
    
    # Bolões que o usuário criou
    boloes_dono = Bolao.query.filter_by(dono_id=current_user.id).all()
    
    # Bolões que o usuário participa
    boloes_participante = ParticipanteBolao.query.filter_by(usuario_id=current_user.id).all()
    
    return render_template('meus_boloes.html', 
                         boloes_dono=boloes_dono,
                         boloes_participante=boloes_participante)

@bp.route('/criar_bolao', methods=['GET', 'POST'])
@login_required
def criar_bolao():
    from app.models import Bolao, RegraPontuacao
    import secrets
    
    if request.method == 'POST':
        nome = request.form.get('nome')
        tipo_bolao = request.form.get('tipo_bolao', 'campeonato_completo')
        tipo_acesso = request.form.get('tipo_acesso', 'publico')
        modo_pontuacao = request.form.get('modo_pontuacao', 'acertos_parciais')
        
        competicao_id = None
        time_especifico_id = None
        ano = None
        
        # Processa conforme o tipo
        if tipo_bolao == 'campeonato_completo':
            competicao_id = request.form.get('competicao_id', type=int)
        elif tipo_bolao == 'time_campeonato':
            competicao_id = request.form.get('competicao_id_time', type=int)
            time_especifico_id = request.form.get('time_id_campeonato', type=int)
        elif tipo_bolao == 'time_ano_completo':
            time_especifico_id = request.form.get('time_id_ano', type=int)
            ano = request.form.get('ano', type=int)
        
           
       
       
        # Captura modo escolhido
        modo = request.form.get('modo_pontuacao', 'acumulativo')
        criterios_desempate = request.form.get('criterios_desempate', 'placares_exatos,acertos_resultado,palpite_antigo')

        # Cria a regra de pontuação com nova estrutura
        bonus_ativo = request.form.get('ativar_bonus_gols') == 'on'

        if modo == 'simples':
            # MODO SIMPLES: só placar exato
            pontos_exato = request.form.get('pontos_placar_exato_simples', 1, type=int)
            regra = RegraPontuacao(
                nome=f"Regra de {nome}",
                criador_id=current_user.id,
                pontos_resultado=pontos_exato,
                pontos_gols_vencedor=0,
                pontos_gols_perdedor=0,
                pontos_diferenca_gols=0,
                requer_resultado_correto=False,
                ativar_bonus_gols=False,
                limite_gols_bonus=5,
                pontos_por_gol_extra=1,
                criterios_desempate=criterios_desempate,
                data_criacao=db.func.now()
            )
        else:
            # MODO ACUMULATIVO: todos os campos
            regra = RegraPontuacao(
                nome=f"Regra de {nome}",
                criador_id=current_user.id,
                pontos_resultado=request.form.get('pontos_resultado', 5, type=int),
                pontos_gols_vencedor=request.form.get('pontos_gols_vencedor', 3, type=int),
                pontos_gols_perdedor=request.form.get('pontos_gols_perdedor', 2, type=int),
                pontos_diferenca_gols=request.form.get('pontos_diferenca_gols', 1, type=int),
                requer_resultado_correto=request.form.get('requer_resultado') == 'on',
                ativar_bonus_gols=bonus_ativo,
                limite_gols_bonus=request.form.get('limite_gols_bonus', 4, type=int) if bonus_ativo else 0,
                pontos_por_gol_extra=request.form.get('pontos_por_gol_extra', 1, type=int) if bonus_ativo else 0,
                criterios_desempate=criterios_desempate,
                data_criacao=db.func.now()
            )

        
        db.session.add(regra)
        db.session.flush()  # Garante que a regra tem um ID
        
        # Gera código de convite único
        codigo_convite = secrets.token_urlsafe(6).upper()[:8]
        
        # Cria o bolão
        novo_bolao = Bolao(
            nome=nome,
            competicao_id=competicao_id,
            dono_id=current_user.id,
            codigo_convite=codigo_convite,
            regra_pontuacao_id=regra.id,
            tipo_acesso=tipo_acesso,
            tipo_bolao=tipo_bolao,
            time_especifico_id=time_especifico_id,
            ano=ano,
            status_pagamento='pendente',
            valor_pago=15.00
        )
        
        
        db.session.add(novo_bolao)
        db.session.commit()
         
        #Se for bolão de time no ano completo, importa jogos automaticamente
        if tipo_bolao == 'time_ano_completo' and time_especifico_id:
            from app.api import importar_jogos_time_ano
            # Busca o time para pegar o api_id
            time = Time.query.get(time_especifico_id)
            if time and time.api_id:
                try:
                    resultado = importar_jogos_time_ano(time.api_id, ano)
                    # Aqui você poderia mostrar uma mensagem de sucesso
                    # flash(f"Importados {resultado['total_jogos']} jogos de {len(resultado['competicoes_criadas'])} competições")
                except Exception as e:
                    print(f"Erro ao importar jogos: {str(e)}")
        
        # Criador entra automaticamente como participante
        participante = ParticipanteBolao(
            bolao_id=novo_bolao.id,
            usuario_id=current_user.id,
            pontos_totais=0
        )
        db.session.add(participante)
        db.session.commit()
        
        # TODO: Redirecionar para pagamento Mercado Pago
        return redirect(f'/bolao/{novo_bolao.id}')
    
    # GET - mostra formulário
    competicoes = Competicao.query.filter(
        (Competicao.uso == 'bolao') | (Competicao.uso == 'ambos')
    ).all()
    
    # Busca todos os times ativos
    times = Time.query.filter_by(ativo=True).order_by(Time.nome).all()
    
    # Cria regra padrão se não existir
    regra_padrao = RegraPontuacao.query.first()
    if not regra_padrao:
        regra_padrao = RegraPontuacao(
            nome='Padrão',
            criador_id=1,
            pontos_placar_exato=5,
            pontos_resultado_certo=3,
            pontos_gols_time_casa=1,
            pontos_gols_time_fora=1
        )
        db.session.add(regra_padrao)
        db.session.commit()
    
    regras = RegraPontuacao.query.filter_by(publica=True).all()
    
    return render_template('criar_bolao.html', competicoes=competicoes, regras=regras, times=times)

@bp.route('/api/times_por_competicao/<int:competicao_id>')
@login_required
def api_times_por_competicao(competicao_id):
    # Busca times que jogam na competição
    times_ids = db.session.query(Jogo.time_casa_id).filter_by(competicao_id=competicao_id).union(
        db.session.query(Jogo.time_fora_id).filter_by(competicao_id=competicao_id)
    ).distinct()
    
    times = Time.query.filter(Time.id.in_(times_ids)).order_by(Time.nome).all()
    
    return jsonify({
        'times': [{'id': t.id, 'nome': t.nome} for t in times]
    })



@bp.route('/bolao/<int:bolao_id>')
@login_required
def bolao_detalhes(bolao_id):
    from app.models import Bolao, ParticipanteBolao, Palpite
    
    bolao = Bolao.query.get_or_404(bolao_id)
    
    # Verifica se o usuário é o dono
    eh_dono = bolao.dono_id == current_user.id
    
    # Verifica se o usuário participa
    participa = ParticipanteBolao.query.filter_by(
        bolao_id=bolao_id,
        usuario_id=current_user.id
    ).first() is not None
    
    # Se não é dono, não participa E não é admin, redireciona
    if not eh_dono and not participa and not current_user.is_admin:
        return redirect('/meus_boloes')

    

# Busca jogos conforme o tipo de bolão
    if bolao.tipo_bolao == 'campeonato_completo':
        # Todos os jogos da competição
        jogos = Jogo.query.filter_by(competicao_id=bolao.competicao_id).order_by(Jogo.data).all()
    
    elif bolao.tipo_bolao == 'time_campeonato':
        # Apenas jogos do time específico naquela competição
        jogos = Jogo.query.filter(
            ((Jogo.time_casa_id == bolao.time_especifico_id) | (Jogo.time_fora_id == bolao.time_especifico_id)),
            Jogo.competicao_id == bolao.competicao_id
        ).order_by(Jogo.data).all()
    
    elif bolao.tipo_bolao == 'time_ano_completo':
        # Todos os jogos do time em todas as competições do ano
        jogos = Jogo.query.join(Competicao).filter(
            ((Jogo.time_casa_id == bolao.time_especifico_id) | (Jogo.time_fora_id == bolao.time_especifico_id)),
            Competicao.ano == bolao.ano
        ).order_by(Jogo.data).all()
    
    else:
        jogos = []


    # Busca palpites do usuário neste bolão
    palpites_usuario = {}
    palpites = Palpite.query.filter_by(bolao_id=bolao_id, usuario_id=current_user.id).all()
    for p in palpites:
        palpites_usuario[p.jogo_id] = p
    
    # Busca solicitações pendentes (se for dono)
    solicitacoes_pendentes = []
    if eh_dono:
        solicitacoes_pendentes = SolicitacaoEntrada.query.filter_by(
            bolao_id=bolao_id,
            status='pendente'
        ).all()
    # Busca todos os palpites do bolão
    from app.models import Palpite
    todos_palpites = Palpite.query.filter_by(bolao_id=bolao_id).all()    
    
    # ✅ CORREÇÃO: Buscar regra de pontuação para mostrar no template
    regra = RegraPontuacao.query.get(bolao.regra_pontuacao_id)
    if not regra:
        # Criar regra default temporária se não encontrar
        regra = RegraPontuacao(
            pontos_resultado=5,
            pontos_gols_vencedor=3,
            pontos_gols_perdedor=2,
            pontos_diferenca_gols=1,
            requer_resultado_correto=True
        )

    # Computa ranking com critérios de desempate
    import json
    ranking = []
    for part in bolao.participantes.all():
        palpites_part = Palpite.query.filter_by(bolao_id=bolao_id, usuario_id=part.usuario_id).all()

        placares_exatos = 0
        acertos_resultado = 0
        gols_vencedor_acertos = 0
        gols_perdedor_acertos = 0
        timestamp_min = None
        detalhes = []

        for p in palpites_part:
            j = p.jogo
            if j.gols_casa is None or j.gols_fora is None:
                continue

            res_real = 'casa' if j.gols_casa > j.gols_fora else ('fora' if j.gols_fora > j.gols_casa else 'empate')
            res_palpite = 'casa' if p.gols_casa_palpite > p.gols_fora_palpite else ('fora' if p.gols_fora_palpite > p.gols_casa_palpite else 'empate')

            eh_placar_exato = (p.gols_casa_palpite == j.gols_casa and p.gols_fora_palpite == j.gols_fora)
            eh_acerto_resultado = (res_real == res_palpite)

            # Gols vencedor/perdedor
            if res_real != 'empate':
                gols_v_real = max(j.gols_casa, j.gols_fora)
                gols_p_real = min(j.gols_casa, j.gols_fora)
                gols_v_palp = max(p.gols_casa_palpite, p.gols_fora_palpite)
                gols_p_palp = min(p.gols_casa_palpite, p.gols_fora_palpite)
                if gols_v_real == gols_v_palp:
                    gols_vencedor_acertos += 1
                if gols_p_real == gols_p_palp:
                    gols_perdedor_acertos += 1

            if eh_placar_exato:
                placares_exatos += 1
            if eh_acerto_resultado:
                acertos_resultado += 1

            if p.timestamp_preciso and (timestamp_min is None or p.timestamp_preciso < timestamp_min):
                timestamp_min = p.timestamp_preciso

            detalhes.append({
                'time_casa': j.time_casa.nome,
                'time_fora': j.time_fora.nome,
                'data': converter_utc_brasilia(j.data).strftime('%d/%m/%Y às %H:%M') if j.data else '',
                'gols_casa_real': j.gols_casa,
                'gols_fora_real': j.gols_fora,
                'gols_casa_palpite': p.gols_casa_palpite,
                'gols_fora_palpite': p.gols_fora_palpite,
                'pontos': p.pontos_obtidos,
                'placar_exato': eh_placar_exato,
                'acerto_resultado': eh_acerto_resultado,
                'gols_vencedor_acerto': res_real != 'empate' and max(j.gols_casa, j.gols_fora) == max(p.gols_casa_palpite, p.gols_fora_palpite),
                'gols_perdedor_acerto': res_real != 'empate' and min(j.gols_casa, j.gols_fora) == min(p.gols_casa_palpite, p.gols_fora_palpite),
            })

        ranking.append({
            'participante': part,
            'pontos': part.pontos_totais,
            'placares_exatos': placares_exatos,
            'acertos_resultado': acertos_resultado,
            'gols_vencedor': gols_vencedor_acertos,
            'gols_perdedor': gols_perdedor_acertos,
            'timestamp_min': timestamp_min,
            'detalhes_json': json.dumps(detalhes, ensure_ascii=False),
        })

    criterios = (regra.criterios_desempate if regra and getattr(regra, 'criterios_desempate', None) else 'placares_exatos,acertos_resultado,palpite_antigo').split(',')

    def sort_key(item):
        keys = [-item['pontos']]
        for c in criterios:
            if c == 'placares_exatos':
                keys.append(-item['placares_exatos'])
            elif c == 'acertos_resultado':
                keys.append(-item['acertos_resultado'])
            elif c == 'gols_vencedor':
                keys.append(-item['gols_vencedor'])
            elif c == 'gols_perdedor':
                keys.append(-item['gols_perdedor'])
            elif c == 'palpite_antigo':
                keys.append(item['timestamp_min'] or 9999999999999)
        # palpite_antigo sempre ao final
        if 'palpite_antigo' not in criterios:
            keys.append(item['timestamp_min'] or 9999999999999)
        return tuple(keys)

    ranking.sort(key=sort_key)
    
    return render_template('bolao_detalhes.html', 
                         bolao=bolao, 
                         regra=regra,  # ✅ ADICIONA REGRA
                         eh_dono=eh_dono,
                         jogos=jogos,
                         palpites_usuario=palpites_usuario,
                         solicitacoes_pendentes=solicitacoes_pendentes,
                         todos_palpites=todos_palpites,
                         ranking=ranking,
                         criterios=criterios,
                         agora=datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S'))


@bp.route('/salvar_palpite', methods=['POST'])
@login_required
def salvar_palpite():
    from app.models import Palpite, Jogo
    from app.comprovante import gerar_hash_palpite
    import time
    
    data = request.get_json()
    bolao_id = data.get('bolao_id')
    jogo_id = data.get('jogo_id')
    gols_casa = data.get('gols_casa')
    gols_fora = data.get('gols_fora')
    
    # Verifica se jogo ainda não começou (comparação em UTC para evitar erro de fuso)
    jogo = Jogo.query.get_or_404(jogo_id)
    if jogo.data:
        from datetime import datetime
        data_str = jogo.data.replace('+00:00', '').replace('Z', '').split('+')[0][:19]
        try:
            data_jogo_utc = datetime.strptime(data_str, '%Y-%m-%dT%H:%M:%S')
        except ValueError:
            data_jogo_utc = datetime.strptime(data_str[:16], '%Y-%m-%dT%H:%M')
        if datetime.utcnow() >= data_jogo_utc:
            return jsonify({'erro': 'Jogo já começou! Palpites encerrados.'}), 400
    
    # Gera timestamp preciso (milissegundos)
    timestamp_ms = int(time.time() * 1000)
    
    # Gera hash do palpite
    hash_comprovante = gerar_hash_palpite(
        current_user.id,
        jogo_id,
        gols_casa,
        gols_fora,
        timestamp_ms
    )
    
    # Busca ou cria palpite
    palpite = Palpite.query.filter_by(
        bolao_id=bolao_id,
        usuario_id=current_user.id,
        jogo_id=jogo_id
    ).first()
    
    if palpite:
        # Atualiza palpite existente
        palpite.gols_casa_palpite = gols_casa
        palpite.gols_fora_palpite = gols_fora
        palpite.hash_comprovante = hash_comprovante
        palpite.timestamp_preciso = timestamp_ms
    else:
        # Cria novo palpite
        palpite = Palpite(
            bolao_id=bolao_id,
            usuario_id=current_user.id,
            jogo_id=jogo_id,
            gols_casa_palpite=gols_casa,
            gols_fora_palpite=gols_fora,
            hash_comprovante=hash_comprovante,
            timestamp_preciso=timestamp_ms
        )
        db.session.add(palpite)
    
    db.session.commit()
    
    return jsonify({
        'sucesso': True,
        'hash': hash_comprovante,
        'timestamp': timestamp_ms
    })

@bp.route('/testar_api')
def testar_api():
    from app.api import get_jogos_brasileirao
    from config import Config
    
    try:
        api_key_presente = bool(Config.API_FOOTBALL_KEY)
        api_key_primeiros = Config.API_FOOTBALL_KEY[:10] if Config.API_FOOTBALL_KEY else 'NENHUMA'
        
        data = get_jogos_brasileirao()
        
        return jsonify({
            'api_key_configurada': api_key_presente,
            'api_key_inicio': api_key_primeiros,
            'api_results': data.get('results', 0),
            'api_response_count': len(data.get('response', [])),
            'api_errors': data.get('errors', {}),
            'api_message': data.get('message', 'ok')
        })
    except Exception as e:
        return jsonify({'erro': str(e)}), 500
    
    
@bp.route('/migrar_uso')
def migrar_uso():
    from sqlalchemy import text, inspect
    
    try:
        # Verifica se a coluna já existe
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('competicao')]
        
        if 'uso' not in columns:
            db.session.execute(text("ALTER TABLE competicao ADD COLUMN uso VARCHAR(20) DEFAULT 'ambos'"))
            db.session.commit()
        
        # Marca o Brasileirão como "projecao"
        brasileirao = Competicao.query.filter(Competicao.nome.like('%Serie A%')).first()

        #brasileirao = Competicao.query.filter(Competicao.nome.like('%Brasileirão%')).first()
        if brasileirao:
            brasileirao.uso = 'projecao'
            db.session.commit()
        
        # Marca outras competições como "bolao"
        outras = Competicao.query.filter(~Competicao.nome.like('%Brasileirão%')).all()
        for comp in outras:
            if comp.uso == 'ambos':  # Só atualiza se ainda não foi definido
                comp.uso = 'bolao'
        db.session.commit()
        
        return jsonify({'sucesso': True, 'brasileirao': brasileirao.nome if brasileirao else None})
    except Exception as e:
        return jsonify({'erro': str(e)}), 500
    
@bp.route('/debug_jogos')
def debug_jogos():
    serie_a = Competicao.query.filter_by(nome='Serie A 2026').first()
    if not serie_a:
        return jsonify({'erro': 'Serie A não encontrada'})
    
    jogos_serie_a = Jogo.query.filter_by(competicao_id=serie_a.id).count()
    jogos_sem_competicao = Jogo.query.filter_by(competicao_id=None).count()
    total_jogos = Jogo.query.count()
    
    return jsonify({
        'serie_a_id': serie_a.id,
        'jogos_serie_a': jogos_serie_a,
        'jogos_sem_competicao': jogos_sem_competicao,
        'total_jogos': total_jogos
    })
@bp.route('/corrigir_jogos_brasileirao')
def corrigir_jogos_brasileirao():
    from sqlalchemy import text
    
    serie_a = Competicao.query.filter_by(nome='Serie A 2026').first()
    if not serie_a:
        return jsonify({'erro': 'Serie A não encontrada'})
    
    # Atualiza jogos sem competicao_id para Serie A 2026
    result = db.session.execute(
        text("UPDATE jogo SET competicao_id = :comp_id WHERE competicao_id IS NULL"),
        {'comp_id': serie_a.id}
    )
    db.session.commit()
    
    # Verifica quantos foram atualizados
    jogos_serie_a = Jogo.query.filter_by(competicao_id=serie_a.id).count()
    
    return jsonify({
        'sucesso': True,
        'jogos_atualizados': result.rowcount,
        'total_jogos_serie_a': jogos_serie_a
    })

@bp.route('/convite/<codigo>')
def link_convite(codigo):
    """
    ✅ NOVO: Link direto de convite para bolão
    Se não estiver logado, redireciona para login/registro com next parameter
    Se estiver logado, processa entrada automaticamente
    """
    from app.models import Bolao, ParticipanteBolao, SolicitacaoEntrada
    
    codigo = codigo.strip().upper()
    
    # Busca bolão pelo código
    bolao = Bolao.query.filter_by(codigo_convite=codigo).first()
    
    if not bolao:
        flash('Código de convite inválido!', 'error')
        return redirect('/')
    
    # Se não estiver logado, redireciona para login com next
    if not current_user.is_authenticated:
        flash(f'Faça login ou cadastre-se para entrar no bolão "{bolao.nome}"', 'info')
        return redirect(f'/login?next=/convite/{codigo}')
    
    # Verifica se já participa
    ja_participa = ParticipanteBolao.query.filter_by(
        bolao_id=bolao.id,
        usuario_id=current_user.id
    ).first()
    
    if ja_participa:
        flash(f'Você já participa do bolão "{bolao.nome}"!', 'info')
        return redirect(f'/bolao/{bolao.id}')
    
    # Verifica se é o dono
    if bolao.dono_id == current_user.id:
        flash(f'Você é o criador deste bolão!', 'info')
        return redirect(f'/bolao/{bolao.id}')
    
    # PÚBLICO: Entra automaticamente
    if bolao.tipo_acesso == 'publico':
        participante = ParticipanteBolao(
            bolao_id=bolao.id,
            usuario_id=current_user.id,
            pontos_totais=0
        )
        db.session.add(participante)
        db.session.commit()
        
        flash(f'✅ Você entrou no bolão "{bolao.nome}" com sucesso!', 'success')
        return redirect(f'/bolao/{bolao.id}')
    
    # PRIVADO: Cria solicitação
    else:
        # Verifica se já tem solicitação pendente
        solicitacao_existente = SolicitacaoEntrada.query.filter_by(
            bolao_id=bolao.id,
            usuario_id=current_user.id,
            status='pendente'
        ).first()
        
        if solicitacao_existente:
            flash(f'Você já solicitou entrada neste bolão. Aguarde aprovação.', 'info')
            return redirect(f'/bolao/{bolao.id}')
        
        # Cria solicitação
        solicitacao = SolicitacaoEntrada(
            bolao_id=bolao.id,
            usuario_id=current_user.id,
            status='pendente'
        )
        db.session.add(solicitacao)
        db.session.commit()
        
        flash(f'Solicitação enviada! Aguarde aprovação do criador.', 'info')
        return redirect(f'/bolao/{bolao.id}')


@bp.route('/entrar_bolao', methods=['GET', 'POST'])
@login_required
def entrar_bolao():
    from app.models import Bolao, ParticipanteBolao, SolicitacaoEntrada
    
    if request.method == 'POST':
        codigo = request.form.get('codigo', '').strip().upper()
        
        # Busca bolão pelo código
        bolao = Bolao.query.filter_by(codigo_convite=codigo).first()
        
        if not bolao:
            return render_template('entrar_bolao.html', erro='Código inválido. Verifique e tente novamente.')
        
        # Verifica se já participa
        ja_participa = ParticipanteBolao.query.filter_by(
            bolao_id=bolao.id,
            usuario_id=current_user.id
        ).first()
        
        if ja_participa:
            # ✅ CORREÇÃO: Redireciona para o bolão ao invés de mostrar erro
            flash(f'Você já participa do bolão "{bolao.nome}"!', 'info')
            return redirect(f'/bolao/{bolao.id}')
        
        # Verifica se é o dono
        if bolao.dono_id == current_user.id:
            flash(f'Você é o criador do bolão "{bolao.nome}"!', 'info')
            return redirect(f'/bolao/{bolao.id}')
        
        # PÚBLICO: Entra automaticamente
        if bolao.tipo_acesso == 'publico':
            participante = ParticipanteBolao(
                bolao_id=bolao.id,
                usuario_id=current_user.id,
                pontos_totais=0
            )
            db.session.add(participante)
            db.session.commit()
            
            # ✅ CORREÇÃO: Redireciona para o bolão
            flash(f'✅ Você entrou no bolão "{bolao.nome}" com sucesso!', 'success')
            return redirect(f'/bolao/{bolao.id}')
        
        # PRIVADO: Cria solicitação
        else:
            # Verifica se já tem solicitação pendente
            solicitacao_existente = SolicitacaoEntrada.query.filter_by(
                bolao_id=bolao.id,
                usuario_id=current_user.id,
                status='pendente'
            ).first()
            
            if solicitacao_existente:
                return render_template('entrar_bolao.html', 
                    erro=f'Você já solicitou entrada no bolão "{bolao.nome}". Aguarde aprovação do criador.')
            
            # Cria solicitação
            solicitacao = SolicitacaoEntrada(
                bolao_id=bolao.id,
                usuario_id=current_user.id,
                status='pendente'
            )
            db.session.add(solicitacao)
            db.session.commit()
            
            # ✅ CORREÇÃO: Redireciona para o bolão
            flash(f'Solicitação enviada! Aguarde aprovação.', 'info')
            return redirect(f'/bolao/{bolao.id}')
    
    return render_template('entrar_bolao.html')



@bp.route('/admin/gerenciar')
@admin_required
def admin_gerenciar():
    from app.models import Usuario, Bolao
    
    usuarios = Usuario.query.all()
    boloes = Bolao.query.all()
    
    return render_template('admin/gerenciar.html', usuarios=usuarios, boloes=boloes)

@bp.route('/admin/excluir_usuario/<int:user_id>', methods=['POST'])
@admin_required
def admin_excluir_usuario(user_id):
    from app.models import Usuario, Palpite, ParticipanteBolao, SolicitacaoEntrada
    
    usuario = Usuario.query.get_or_404(user_id)
    
    if usuario.is_admin:
        return jsonify({'erro': 'Não pode excluir admin'}), 400
    
    # Deleta palpites
    Palpite.query.filter_by(usuario_id=user_id).delete()
    
    # Deleta participações
    ParticipanteBolao.query.filter_by(usuario_id=user_id).delete()
    
    # Deleta solicitações
    SolicitacaoEntrada.query.filter_by(usuario_id=user_id).delete()
    
    # Deleta bolões criados por ele (e tudo relacionado)
    boloes = Bolao.query.filter_by(dono_id=user_id).all()
    for bolao in boloes:
        Palpite.query.filter_by(bolao_id=bolao.id).delete()
        ParticipanteBolao.query.filter_by(bolao_id=bolao.id).delete()
        SolicitacaoEntrada.query.filter_by(bolao_id=bolao.id).delete()
        db.session.delete(bolao)
    
    # Deleta usuário
    db.session.delete(usuario)
    db.session.commit()
    
    return jsonify({'sucesso': True})

@bp.route('/admin/excluir_bolao/<int:bolao_id>', methods=['POST'])
@admin_required
def admin_excluir_bolao(bolao_id):
    from app.models import Bolao, Palpite, ParticipanteBolao, SolicitacaoEntrada
    
    bolao = Bolao.query.get_or_404(bolao_id)
    
    # Deleta tudo relacionado
    Palpite.query.filter_by(bolao_id=bolao_id).delete()
    ParticipanteBolao.query.filter_by(bolao_id=bolao_id).delete()
    SolicitacaoEntrada.query.filter_by(bolao_id=bolao_id).delete()
    
    # Deleta bolão
    db.session.delete(bolao)
    db.session.commit()
    
    return jsonify({'sucesso': True})


@bp.route('/responder_solicitacao', methods=['POST'])
@login_required
def responder_solicitacao():
    from app.models import SolicitacaoEntrada, ParticipanteBolao, Bolao
    
    data = request.get_json()
    solicitacao_id = data.get('solicitacao_id')
    acao = data.get('acao')  # 'aprovar' ou 'rejeitar'
    
    solicitacao = SolicitacaoEntrada.query.get_or_404(solicitacao_id)
    bolao = Bolao.query.get(solicitacao.bolao_id)
    
    # Verifica se é o dono do bolão
    if bolao.dono_id != current_user.id:
        return jsonify({'erro': 'Apenas o criador pode aprovar solicitações'}), 403
    
    if acao == 'aprovar':
        # Adiciona como participante
        participante = ParticipanteBolao(
            bolao_id=solicitacao.bolao_id,
            usuario_id=solicitacao.usuario_id,
            pontos_totais=0
        )
        db.session.add(participante)
        solicitacao.status = 'aprovada'
        solicitacao.respondido_por = current_user.id
        solicitacao.data_resposta = db.func.now()
        
    elif acao == 'rejeitar':
        solicitacao.status = 'rejeitada'
        solicitacao.respondido_por = current_user.id
        solicitacao.data_resposta = db.func.now()
    
    db.session.commit()
    
    return jsonify({'sucesso': True})


@bp.route('/atualizar_jogos_bolao/<int:bolao_id>', methods=['POST'])
@login_required
def atualizar_jogos_bolao(bolao_id):
    from app.models import Bolao, Time
    from app.api import importar_jogos_time_ano, get_jogos_competicao
    
    bolao = Bolao.query.get_or_404(bolao_id)
    
    # Verifica se é o dono
    if bolao.dono_id != current_user.id:
        return jsonify({'erro': 'Apenas o criador pode atualizar jogos'}), 403
    
    try:
        novos_jogos = 0
        
        if bolao.tipo_bolao == 'time_ano_completo':
            # Reimporta todos os jogos do time no ano
            time = Time.query.get(bolao.time_especifico_id)
            if time and time.api_id:
                resultado = importar_jogos_time_ano(time.api_id, bolao.ano)
                novos_jogos = resultado['total_jogos']
        
        elif bolao.tipo_bolao in ['campeonato_completo', 'time_campeonato']:
            # Reimporta jogos da competição
            if bolao.competicao and bolao.competicao.api_league_id:
                jogos_data = get_jogos_competicao(bolao.competicao.api_league_id, bolao.competicao.ano)
                
                from app.api import processar_jogos
                jogos = processar_jogos(jogos_data)
                
                times_cadastrados = {}
                
                for jogo in jogos:
                    # Verifica se jogo já existe
                    jogo_existente = Jogo.query.filter_by(api_id=jogo['api_id']).first()
                    if jogo_existente:
                        continue
                    
                    # Cadastra times se necessário
                    for key in ['time_casa_id', 'time_fora_id']:
                        api_id = jogo[key]
                        nome = jogo['time_casa'] if key == 'time_casa_id' else jogo['time_fora']
                        
                        if api_id not in times_cadastrados:
                            time_db = Time.query.filter_by(api_id=api_id).first()
                            if not time_db:
                                time_db = Time(api_id=api_id, nome=nome, ativo=True)
                                db.session.add(time_db)
                                db.session.flush()
                            times_cadastrados[api_id] = time_db.id
                    
                    # Cria novo jogo
                    novo_jogo = Jogo(
                        api_id=jogo['api_id'],
                        competicao_id=bolao.competicao_id,
                        rodada=jogo['rodada'],
                        time_casa_id=times_cadastrados[jogo['time_casa_id']],
                        time_fora_id=times_cadastrados[jogo['time_fora_id']],
                        data=jogo['data'],
                        gols_casa=jogo['gols_casa'],
                        gols_fora=jogo['gols_fora']
                    )
                    db.session.add(novo_jogo)
                    novos_jogos += 1
                
                db.session.commit()
        
        return jsonify({'sucesso': True, 'novos_jogos': novos_jogos})
    
    except Exception as e:
        print(f"Erro ao atualizar jogos: {str(e)}")
        return jsonify({'erro': str(e)}), 500


@bp.route('/migrar_pontuacao_render')
def migrar_pontuacao_render():
    from sqlalchemy import text, inspect
    
    try:
        inspector = inspect(db.engine)
        
        # Migra tabela regra_pontuacao
        columns_regra = [col['name'] for col in inspector.get_columns('regra_pontuacao')]
        
        novas_colunas_regra = {
            'modo': "VARCHAR(20) DEFAULT 'acertos_parciais'",
            'pontos_gols_vencedor': 'INTEGER DEFAULT 0',
            'pontos_gols_perdedor': 'INTEGER DEFAULT 0',
            'pontos_diferenca_gols': 'INTEGER DEFAULT 0',
            'ativar_bonus_gols': 'INTEGER DEFAULT 0',
            'limite_gols_bonus': 'INTEGER DEFAULT 4',
            'pontos_por_gol_extra': 'INTEGER DEFAULT 1',
            'data_criacao': 'TIMESTAMP',
            'tipo_bolao': "VARCHAR(30) DEFAULT 'campeonato_completo'",
            'time_especifico_id': 'INTEGER',
            'ano': 'INTEGER',
            'data_criacao': 'TIMESTAMP'
        }
        
        for coluna, tipo in novas_colunas_regra.items():
            if coluna not in columns_regra:
                if 'TIMESTAMP' in tipo:
                    db.session.execute(text(f"ALTER TABLE regra_pontuacao ADD COLUMN {coluna} TIMESTAMP"))
                else:
                    db.session.execute(text(f"ALTER TABLE regra_pontuacao ADD COLUMN {coluna} {tipo}"))
        
        # Migra tabela bolao
        columns_bolao = [col['name'] for col in inspector.get_columns('bolao')]
        
        if 'data_criacao' not in columns_bolao:
            db.session.execute(text("ALTER TABLE bolao ADD COLUMN data_criacao TIMESTAMP"))
        
        
        db.session.commit()
        
        return jsonify({
            'sucesso': True,
            'mensagem': 'Migração concluída!'
        })
    
    except Exception as e:
        return jsonify({'erro': str(e)}), 500
@bp.route('/migrar_regra_pontuacao_render')
def migrar_regra_pontuacao_render():
    from sqlalchemy import text, inspect
    
    try:
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('regra_pontuacao')]
        
        if 'modo' not in columns:
            db.session.execute(text("ALTER TABLE regra_pontuacao ADD COLUMN modo VARCHAR(20) DEFAULT 'acertos_parciais'"))
        if 'pontos_gols_vencedor' not in columns:
            db.session.execute(text("ALTER TABLE regra_pontuacao ADD COLUMN pontos_gols_vencedor INTEGER DEFAULT 0"))
        if 'pontos_gols_perdedor' not in columns:
            db.session.execute(text("ALTER TABLE regra_pontuacao ADD COLUMN pontos_gols_perdedor INTEGER DEFAULT 0"))
        if 'pontos_diferenca_gols' not in columns:
            db.session.execute(text("ALTER TABLE regra_pontuacao ADD COLUMN pontos_diferenca_gols INTEGER DEFAULT 0"))
        if 'limite_gols_bonus' not in columns:
            db.session.execute(text("ALTER TABLE regra_pontuacao ADD COLUMN limite_gols_bonus INTEGER DEFAULT 4"))
        if 'pontos_por_gol_extra' not in columns:
            db.session.execute(text("ALTER TABLE regra_pontuacao ADD COLUMN pontos_por_gol_extra INTEGER DEFAULT 1"))
        if 'data_criacao' not in columns:
            db.session.execute(text("ALTER TABLE regra_pontuacao ADD COLUMN data_criacao TIMESTAMP"))
        
        db.session.commit()
        return jsonify({'sucesso': True, 'tabela': 'regra_pontuacao'})
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

@bp.route('/migrar_bolao_render')
def migrar_bolao_render():
    from sqlalchemy import text, inspect
    
    try:
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('bolao')]
        
        if 'tipo_bolao' not in columns:
            db.session.execute(text("ALTER TABLE bolao ADD COLUMN tipo_bolao VARCHAR(30) DEFAULT 'campeonato_completo'"))
        if 'time_especifico_id' not in columns:
            db.session.execute(text("ALTER TABLE bolao ADD COLUMN time_especifico_id INTEGER"))
        if 'ano' not in columns:
            db.session.execute(text("ALTER TABLE bolao ADD COLUMN ano INTEGER"))
        if 'data_criacao' not in columns:
            db.session.execute(text("ALTER TABLE bolao ADD COLUMN data_criacao TIMESTAMP"))
        
        db.session.commit()
        return jsonify({'sucesso': True, 'tabela': 'bolao'})
    except Exception as e:
        return jsonify({'erro': str(e)}), 500
@bp.route('/migrar_competicao_nullable')
def migrar_competicao_nullable():
    from sqlalchemy import text
    
    try:
        # PostgreSQL permite alterar restrição NOT NULL diretamente
        db.session.execute(text("ALTER TABLE bolao ALTER COLUMN competicao_id DROP NOT NULL"))
        db.session.commit()
        return jsonify({'sucesso': True, 'mensagem': 'competicao_id agora aceita NULL'})
    except Exception as e:
        return jsonify({'erro': str(e)}), 500
@bp.route('/corrigir_serie_a_uso')
def corrigir_serie_a_uso():
    from sqlalchemy import text
    
    try:
        # Marca Série A como uso='ambos'
        db.session.execute(text("UPDATE competicao SET uso = 'ambos' WHERE nome LIKE '%Serie A%' OR nome LIKE '%Série A%'"))
        db.session.commit()
        return jsonify({'sucesso': True, 'mensagem': 'Série A agora disponível para bolões'})
    except Exception as e:
        return jsonify({'erro': str(e)}), 500
@bp.route('/admin/toggle_dashboard_competicao', methods=['POST'])
@admin_required
def toggle_dashboard_competicao():
    data = request.get_json()
    competicao_id = data.get('competicao_id')
    ativo = data.get('ativo')
    
    competicao = Competicao.query.get_or_404(competicao_id)
    competicao.disponivel_dashboard = ativo
    db.session.commit()
    
    return jsonify({'sucesso': True})

@bp.route('/migrar_dashboard_flag_render')
def migrar_dashboard_flag_render():
    from sqlalchemy import text, inspect
    
    try:
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('competicao')]
        
        if 'disponivel_dashboard' not in columns:
            db.session.execute(text("ALTER TABLE competicao ADD COLUMN disponivel_dashboard BOOLEAN DEFAULT FALSE"))
            # Marca Série A como disponível
            db.session.execute(text("UPDATE competicao SET disponivel_dashboard = TRUE WHERE nome LIKE '%Serie A%' OR nome LIKE '%Série A%'"))
        
        db.session.commit()
        return jsonify({'sucesso': True, 'mensagem': 'Dashboard flag adicionado'})
    except Exception as e:
        return jsonify({'erro': str(e)}), 500
    

@bp.route('/termos')
def termos():
    from datetime import datetime
    return render_template('termos.html', now=datetime.now)

@bp.route('/privacidade')
def privacidade():
    from datetime import datetime
    return render_template('privacidade.html', now=datetime.now)

@bp.route('/comprovante/<int:palpite_id>')
@login_required
def gerar_comprovante_pdf(palpite_id):
    from app.models import Palpite
    from app.comprovante import gerar_qr_code, gerar_hash_palpite
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import cm
    from io import BytesIO
    from datetime import datetime
    import time
    
    palpite = Palpite.query.get_or_404(palpite_id)
    
    # Verifica se é o dono do palpite
    if palpite.usuario_id != current_user.id:
        return "Acesso negado", 403
    
    # Se palpite antigo não tem hash, gera agora
    if not palpite.hash_comprovante or not palpite.timestamp_preciso:
        timestamp_ms = int(palpite.data_palpite.timestamp() * 1000)
        hash_comprovante = gerar_hash_palpite(
            palpite.usuario_id,
            palpite.jogo_id,
            palpite.gols_casa_palpite,
            palpite.gols_fora_palpite,
            timestamp_ms
        )
        palpite.hash_comprovante = hash_comprovante
        palpite.timestamp_preciso = timestamp_ms
        db.session.commit()
    
    # Cria PDF
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # Título
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(width/2, height - 3*cm, "COMPROVANTE DE PALPITE")
    
    # Hash (selo de autenticidade)
    c.setFont("Helvetica", 10)
    c.drawCentredString(width/2, height - 4*cm, f"Hash: {palpite.hash_comprovante}")
    
    # Dados do palpite
    y = height - 6*cm
    c.setFont("Helvetica-Bold", 14)
    c.drawString(3*cm, y, "Dados do Palpite:")
    
    c.setFont("Helvetica", 12)
    y -= 1*cm
    c.drawString(3*cm, y, f"Participante: {palpite.usuario.nome_completo or palpite.usuario.username}")
    
    y -= 0.8*cm
    c.drawString(3*cm, y, f"Jogo: {palpite.jogo.time_casa.nome} vs {palpite.jogo.time_fora.nome}")
    
    y -= 0.8*cm
    c.drawString(3*cm, y, f"Palpite: {palpite.gols_casa_palpite} x {palpite.gols_fora_palpite}")
    
    y -= 0.8*cm
    timestamp_dt = datetime.fromtimestamp(palpite.timestamp_preciso / 1000)
    c.drawString(3*cm, y, f"Data/Hora: {timestamp_dt.strftime('%d/%m/%Y as %H:%M:%S')}")
    
    # QR Code
    qr_img = gerar_qr_code(palpite.hash_comprovante)
    from reportlab.lib.utils import ImageReader
    import base64
    
    qr_data = base64.b64decode(qr_img)
    qr_buffer = BytesIO(qr_data)
    c.drawImage(ImageReader(qr_buffer), width/2 - 3*cm, height - 18*cm, width=6*cm, height=6*cm)
    
    # Instruções
    c.setFont("Helvetica", 10)
    c.drawCentredString(width/2, height - 19*cm, "Escaneie o QR Code para verificar autenticidade")
    
    # Rodapé
    c.setFont("Helvetica", 8)
    c.drawCentredString(width/2, 2*cm, "Este comprovante e imutavel e criptograficamente seguro")
    c.drawCentredString(width/2, 1.5*cm, "Brasileirao 2026 - www.brasileirao2026.com")
    
    c.save()
    
    buffer.seek(0)
    
    from flask import send_file
    return send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'comprovante_palpite_{palpite_id}.pdf'
    )



@bp.route('/verificar/<hash_comprovante>')
def verificar_comprovante(hash_comprovante):
    from app.models import Palpite
    
    palpite = Palpite.query.filter_by(hash_comprovante=hash_comprovante).first()
    
    return render_template('verificar.html', palpite=palpite)

@bp.route('/migrar_termos_render')
def migrar_termos_render():
    from sqlalchemy import text, inspect
    
    try:
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('usuario')]
        
        if 'termos_aceitos_em' not in columns:
            db.session.execute(text("ALTER TABLE usuario ADD COLUMN termos_aceitos_em TIMESTAMP"))
        
        db.session.commit()
        return jsonify({'sucesso': True})
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

@bp.route('/migrar_pontuacao_acumulativa_render')
def migrar_pontuacao_acumulativa_render():
    from sqlalchemy import text, inspect
    
    try:
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('regra_pontuacao')]
        
        # Adiciona nova coluna pontos_resultado
        if 'pontos_resultado' not in columns:
            db.session.execute(text("ALTER TABLE regra_pontuacao ADD COLUMN pontos_resultado INTEGER DEFAULT 5"))
        
        # Adiciona checkbox de regra
        if 'requer_resultado_correto' not in columns:
            db.session.execute(text("ALTER TABLE regra_pontuacao ADD COLUMN requer_resultado_correto BOOLEAN DEFAULT TRUE"))
        
        # Atualiza valores padrão para regras antigas
        db.session.execute(text("""
            UPDATE regra_pontuacao 
            SET pontos_resultado = 5,
                pontos_gols_vencedor = COALESCE(pontos_gols_vencedor, 3),
                pontos_gols_perdedor = COALESCE(pontos_gols_perdedor, 2),
                pontos_diferenca_gols = COALESCE(pontos_diferenca_gols, 1),
                requer_resultado_correto = COALESCE(requer_resultado_correto, TRUE)
            WHERE pontos_resultado IS NULL
        """))
        
        db.session.commit()
        return jsonify({'sucesso': True, 'mensagem': 'Migração concluída!'})
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

@bp.route('/migrar_comprovante_render')
def migrar_comprovante_render():
    from sqlalchemy import text, inspect
    
    try:
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('palpite')]
        
        if 'hash_comprovante' not in columns:
            db.session.execute(text("ALTER TABLE palpite ADD COLUMN hash_comprovante VARCHAR(64)"))
        
        if 'timestamp_preciso' not in columns:
            db.session.execute(text("ALTER TABLE palpite ADD COLUMN timestamp_preciso BIGINT"))
        
        db.session.commit()
        return jsonify({'sucesso': True})
    except Exception as e:
        return jsonify({'erro': str(e)}), 500
    
@bp.route('/migrar_boolean_para_integer_render')
def migrar_boolean_para_integer_render():
    from sqlalchemy import text
    
    try:
        # Remove default
        db.session.execute(text("ALTER TABLE regra_pontuacao ALTER COLUMN ativar_bonus_gols DROP DEFAULT"))
        db.session.execute(text("ALTER TABLE regra_pontuacao ALTER COLUMN requer_resultado_correto DROP DEFAULT"))
        
        # Converte para boolean
        db.session.execute(text("ALTER TABLE regra_pontuacao ALTER COLUMN ativar_bonus_gols TYPE BOOLEAN USING ativar_bonus_gols::boolean"))
        db.session.execute(text("ALTER TABLE regra_pontuacao ALTER COLUMN requer_resultado_correto TYPE BOOLEAN USING requer_resultado_correto::boolean"))
        
        # Recoloca default
        db.session.execute(text("ALTER TABLE regra_pontuacao ALTER COLUMN ativar_bonus_gols SET DEFAULT FALSE"))
        db.session.execute(text("ALTER TABLE regra_pontuacao ALTER COLUMN requer_resultado_correto SET DEFAULT TRUE"))
        
        db.session.commit()
        return jsonify({'sucesso': True, 'mensagem': 'Conversão completa!'})
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

@bp.route('/editar_bolao/<int:bolao_id>', methods=['GET', 'POST'])
@admin_required
def editar_bolao(bolao_id):
    """
    Edita regras do bolão e recalcula pontos (ADMIN ONLY)
    """
    from app.models import Bolao, RegraPontuacao, Palpite, ParticipanteBolao
    
    bolao = Bolao.query.get_or_404(bolao_id)
    regra = bolao.regra
    
    if request.method == 'POST':
        # Captura modo escolhido
        modo = request.form.get('modo_pontuacao', 'acumulativo')
        
        if modo == 'simples':
            # MODO SIMPLES: só placar exato
            pontos_exato = int(request.form.get('pontos_placar_exato_simples', 1))
            regra.pontos_resultado = pontos_exato
            regra.pontos_gols_vencedor = 0
            regra.pontos_gols_perdedor = 0
            regra.pontos_diferenca_gols = 0
        else:
            # MODO ACUMULATIVO: todos os campos
            regra.pontos_resultado = int(request.form.get('pontos_resultado', 5))
            regra.pontos_gols_vencedor = int(request.form.get('pontos_gols_vencedor', 3))
            regra.pontos_gols_perdedor = int(request.form.get('pontos_gols_perdedor', 2))
            regra.pontos_diferenca_gols = int(request.form.get('pontos_diferenca_gols', 1))
        
        # Bônus Elástico
        regra.ativar_bonus_gols = 'ativar_bonus_gols' in request.form
        if regra.ativar_bonus_gols:
            regra.limite_gols_bonus = int(request.form.get('limite_gols_bonus', 5))
            regra.pontos_por_gol_extra = int(request.form.get('pontos_por_gol_extra', 2))
        
        db.session.commit()
        
        # RECALCULA TODOS OS PALPITES DO BOLÃO
        palpites = Palpite.query.filter_by(bolao_id=bolao_id).all()
        for palpite in palpites:
            jogo = palpite.jogo
            if jogo.gols_casa is not None and jogo.gols_fora is not None:
                pontos = calcular_pontos_palpite(palpite, jogo, regra)
                palpite.pontos_obtidos = pontos
        
        # ATUALIZA RANKING
        participantes = ParticipanteBolao.query.filter_by(bolao_id=bolao_id).all()
        for participante in participantes:
            total = db.session.query(db.func.sum(Palpite.pontos_obtidos)).filter_by(
                bolao_id=bolao_id,
                usuario_id=participante.usuario_id
            ).scalar() or 0
            participante.pontos_totais = total
        
        db.session.commit()
        
        flash(f'✅ Regras atualizadas e {len(palpites)} palpites recalculados!', 'success')
        return redirect(url_for('main.bolao_detalhes', bolao_id=bolao_id))
    
    # GET: Mostra formulário
    return render_template('editar_bolao.html', bolao=bolao, regra=regra)

@bp.route('/recalcular_bolao/<int:bolao_id>', methods=['POST'])
@admin_required
def recalcular_bolao(bolao_id):
    """
    Recalcula TODOS os pontos de um bolão
    Cria backup automático antes (snapshot)
    """
    from app.models import Bolao, Palpite, ParticipanteBolao, RegraPontuacao, SnapshotPontuacao
    import json
    
    bolao = Bolao.query.get_or_404(bolao_id)
    regra = bolao.regra
    
    # 1. CRIAR SNAPSHOT (BACKUP) ANTES DE RECALCULAR
    palpites_atuais = Palpite.query.filter_by(bolao_id=bolao_id).all()
    participantes_atuais = ParticipanteBolao.query.filter_by(bolao_id=bolao_id).all()
    
    dados_backup = {
        'palpites': [
            {'id': p.id, 'pontos_obtidos': p.pontos_obtidos}
            for p in palpites_atuais
        ],
        'participantes': [
            {'id': p.id, 'usuario_id': p.usuario_id, 'pontos_totais': p.pontos_totais}
            for p in participantes_atuais
        ]
    }
    
    snapshot = SnapshotPontuacao(
        bolao_id=bolao_id,
        motivo='Recálculo manual via admin',
        usuario_id=current_user.id,
        dados_json=json.dumps(dados_backup)
    )
    db.session.add(snapshot)
    db.session.flush()
    
    # 2. RECALCULAR PONTOS
    palpites_recalculados = 0
    
    for palpite in palpites_atuais:
        jogo = palpite.jogo
        
        if jogo.gols_casa is not None and jogo.gols_fora is not None:
            pontos = calcular_pontos_palpite(palpite, jogo, regra)
            palpite.pontos_obtidos = pontos
            palpites_recalculados += 1
    
    # 3. ATUALIZAR RANKING
    for participante in participantes_atuais:
        total = db.session.query(db.func.sum(Palpite.pontos_obtidos)).filter_by(
            bolao_id=bolao_id,
            usuario_id=participante.usuario_id
        ).scalar() or 0
        participante.pontos_totais = total
    
    db.session.commit()
    
    flash(f'✅ Recálculo concluído! {palpites_recalculados} palpites recalculados. Backup #{snapshot.id} criado.', 'success')
    return redirect(url_for('main.bolao_detalhes', bolao_id=bolao_id))


@bp.route('/restaurar_snapshot/<int:snapshot_id>', methods=['POST'])
@admin_required
def restaurar_snapshot(snapshot_id):
    """
    ROLLBACK - Restaura pontos de um snapshot (backup)
    """
    from app.models import SnapshotPontuacao, Palpite, ParticipanteBolao
    import json
    
    snapshot = SnapshotPontuacao.query.get_or_404(snapshot_id)
    dados = json.loads(snapshot.dados_json)
    
    # Restaurar pontos dos palpites
    for p_data in dados['palpites']:
        palpite = Palpite.query.get(p_data['id'])
        if palpite:
            palpite.pontos_obtidos = p_data['pontos_obtidos']
    
    # Restaurar pontos totais dos participantes
    for part_data in dados['participantes']:
        participante = ParticipanteBolao.query.get(part_data['id'])
        if participante:
            participante.pontos_totais = part_data['pontos_totais']
    
    db.session.commit()
    
    flash(f'✅ Pontos restaurados do backup #{snapshot_id} de {snapshot.data_snapshot.strftime("%d/%m/%Y %H:%M")}', 'success')
    return redirect(url_for('main.bolao_detalhes', bolao_id=snapshot.bolao_id))


@bp.route('/snapshots/<int:bolao_id>')
@admin_required
def listar_snapshots(bolao_id):
    """
    Lista todos os snapshots (backups) de um bolão
    """
    from app.models import Bolao, SnapshotPontuacao
    
    bolao = Bolao.query.get_or_404(bolao_id)
    snapshots = SnapshotPontuacao.query.filter_by(bolao_id=bolao_id).order_by(
        SnapshotPontuacao.data_snapshot.desc()
    ).all()
    
    return render_template('snapshots_bolao.html', bolao=bolao, snapshots=snapshots)


@bp.route('/visualizar_projecoes/<int:competicao_id>')
@login_required
def visualizar_projecoes(competicao_id):
    """Interface de projeções"""
    competicao = Competicao.query.get_or_404(competicao_id)
    
    jogos = Jogo.query.filter_by(competicao_id=competicao_id).all()
    times_ids = set()
    for jogo in jogos:
        times_ids.add(jogo.time_casa_id)
        times_ids.add(jogo.time_fora_id)
    
    times = Time.query.filter(Time.id.in_(times_ids)).order_by(Time.nome).all()
    
    return render_template('visualizar_projecoes.html', competicao=competicao, times=times)
@bp.route('/replicar_palpite', methods=['POST'])
@login_required
def replicar_palpite():
    """
    Replica um palpite para todos os outros bolões do usuário
    que contenham o mesmo jogo e ainda estejam abertos.
    """
    from app.models import Palpite, ParticipanteBolao, Bolao
    from app.comprovante import gerar_hash_palpite
    import time as time_module

    data = request.get_json()
    jogo_id = data.get('jogo_id')
    gols_casa = data.get('gols_casa')
    gols_fora = data.get('gols_fora')
    bolao_origem_id = data.get('bolao_id')
    confirmar = data.get('confirmar', False)  # True = usuário já confirmou sobrescrita

    if gols_casa is None or gols_fora is None or not jogo_id:
        return jsonify({'erro': 'Dados incompletos'}), 400

    # Verifica se o jogo ainda está aberto (comparação em UTC para evitar erro de fuso)
    jogo = Jogo.query.get_or_404(jogo_id)
    if jogo.data:
        from datetime import datetime
        data_str = jogo.data.replace('+00:00', '').replace('Z', '').split('+')[0][:19]
        try:
            data_jogo_utc = datetime.strptime(data_str, '%Y-%m-%dT%H:%M:%S')
        except ValueError:
            data_jogo_utc = datetime.strptime(data_str[:16], '%Y-%m-%dT%H:%M')
        if datetime.utcnow() >= data_jogo_utc:
            return jsonify({'erro': 'Jogo já começou!'}), 400

    # Busca outros bolões do usuário que contenham este jogo
    participacoes = ParticipanteBolao.query.filter_by(usuario_id=current_user.id).all()
    boloes_ids = [p.bolao_id for p in participacoes if p.bolao_id != bolao_origem_id]

    # Filtra bolões que têm este jogo (mesma competicao_id ou time)
    boloes_alvo = []
    for bolao_id in boloes_ids:
        bolao = Bolao.query.get(bolao_id)
        if not bolao or bolao.status != 'ativo':
            continue

        # Verifica se o jogo pertence a este bolão
        jogo_pertence = False
        if bolao.tipo_bolao == 'campeonato_completo' and jogo.competicao_id == bolao.competicao_id:
            jogo_pertence = True
        elif bolao.tipo_bolao == 'time_campeonato' and jogo.competicao_id == bolao.competicao_id and \
             (jogo.time_casa_id == bolao.time_especifico_id or jogo.time_fora_id == bolao.time_especifico_id):
            jogo_pertence = True
        elif bolao.tipo_bolao == 'time_ano_completo' and \
             (jogo.time_casa_id == bolao.time_especifico_id or jogo.time_fora_id == bolao.time_especifico_id):
            jogo_pertence = True

        if jogo_pertence:
            palpite_existente = Palpite.query.filter_by(
                bolao_id=bolao_id,
                usuario_id=current_user.id,
                jogo_id=jogo_id
            ).first()
            boloes_alvo.append({
                'bolao_id': bolao_id,
                'nome': bolao.nome,
                'tem_palpite': palpite_existente is not None,
                'palpite_atual': f"{palpite_existente.gols_casa_palpite}x{palpite_existente.gols_fora_palpite}" if palpite_existente else None
            })

    if not boloes_alvo:
        return jsonify({'sucesso': True, 'replicados': 0, 'mensagem': 'Nenhum outro bolão encontrado com este jogo.'})

    # Se há palpites existentes e usuário ainda não confirmou → pede confirmação
    com_palpite = [b for b in boloes_alvo if b['tem_palpite']]
    if com_palpite and not confirmar:
        return jsonify({
            'requer_confirmacao': True,
            'boloes_com_palpite': com_palpite,
            'boloes_sem_palpite': [b for b in boloes_alvo if not b['tem_palpite']],
            'total': len(boloes_alvo)
        })

    # Replica para todos
    replicados = 0
    timestamp_ms = int(time_module.time() * 1000)

    for b in boloes_alvo:
        hash_comprovante = gerar_hash_palpite(
            current_user.id, jogo_id, gols_casa, gols_fora, timestamp_ms
        )
        palpite = Palpite.query.filter_by(
            bolao_id=b['bolao_id'],
            usuario_id=current_user.id,
            jogo_id=jogo_id
        ).first()

        if palpite:
            palpite.gols_casa_palpite = gols_casa
            palpite.gols_fora_palpite = gols_fora
            palpite.hash_comprovante = hash_comprovante
            palpite.timestamp_preciso = timestamp_ms
        else:
            palpite = Palpite(
                bolao_id=b['bolao_id'],
                usuario_id=current_user.id,
                jogo_id=jogo_id,
                gols_casa_palpite=gols_casa,
                gols_fora_palpite=gols_fora,
                hash_comprovante=hash_comprovante,
                timestamp_preciso=timestamp_ms
            )
            db.session.add(palpite)
        replicados += 1

    db.session.commit()
    return jsonify({'sucesso': True, 'replicados': replicados, 'mensagem': f'Palpite replicado para {replicados} bolão(ões)!'})


@bp.route('/migrar_criterios_desempate')
def migrar_criterios_desempate():
    from sqlalchemy import text
    try:
        db.session.execute(text("ALTER TABLE regra_pontuacao ADD COLUMN IF NOT EXISTS criterios_desempate VARCHAR(200) DEFAULT 'placares_exatos,acertos_resultado,palpite_antigo'"))
        db.session.commit()
        return jsonify({'sucesso': True, 'mensagem': 'Coluna criterios_desempate adicionada!'})
    except Exception as e:
        return jsonify({'erro': str(e)}), 500







@bp.route('/admin/checar_copa')
@bp.route('/admin/checar_copa/<int:competicao_id>')
@admin_required
def checar_copa(competicao_id=None):
    """Compara jogos da Copa do Mundo no banco vs API Football."""
    import requests, os
    from app.models import Jogo, Time, Competicao
    from app.utils import converter_utc_brasilia

    if competicao_id:
        copa = Competicao.query.get_or_404(competicao_id)
    else:
        # Busca o torneio, excluindo qualificações
        copa = Competicao.query.filter(
            (Competicao.nome.ilike('%world cup%') | Competicao.nome.ilike('%copa do mundo%')) ,
            ~Competicao.nome.ilike('%qualif%'),
            ~Competicao.nome.ilike('%qualification%'),
            ~Competicao.nome.ilike('%eliminat%')
        ).order_by(Competicao.id.desc()).first()

    if not copa:
        return "<h2 style='font-family:monospace;color:#e74c3c;padding:2rem'>Copa do Mundo não encontrada no banco.<br>Importe primeiro em /admin/competicoes</h2>"

    # Detecta season
    jogos_banco = Jogo.query.filter_by(competicao_id=copa.id).order_by(Jogo.data).all()
    seasons = set()
    for j in jogos_banco:
        if j.data:
            try: seasons.add(int(j.data[:4]))
            except: pass
    if not seasons:
        seasons = {2026}

    # Busca na API Football
    headers = {"x-apisports-key": os.getenv("API_FOOTBALL_KEY")}
    jogos_api = {}
    for season in seasons:
        r = requests.get("https://v3.football.api-sports.io/fixtures",
            headers=headers,
            params={"league": copa.api_league_id, "season": season},
            timeout=15)
        for f in r.json().get("response", []):
            jogos_api[f["fixture"]["id"]] = f

    # Monta tabela
    linhas = []
    for j in jogos_banco:
        api  = jogos_api.get(j.api_id)
        data_banco = j.data or "nulo"
        data_api   = api["fixture"]["date"] if api else "não encontrado"
        br_banco   = converter_utc_brasilia(data_banco)
        br_api     = converter_utc_brasilia(data_api) if api else None
        b_fmt = br_banco.strftime("%d/%m %H:%M") if br_banco else data_banco
        a_fmt = br_api.strftime("%d/%m %H:%M")   if br_api   else data_api
        dif   = b_fmt != a_fmt
        cor   = "#e74c3c" if dif else "#2ecc71"
        rodada = j.rodada or (api["league"]["round"] if api else "?")
        grupo  = j.grupo or (api["league"].get("group") or "—" if api else "—")
        tc = j.time_casa.nome if j.time_casa else "?"
        tf = j.time_fora.nome if j.time_fora else "?"
        ph = "🔜" if (j.time_casa and j.time_casa.api_id >= 9000000) or (j.time_fora and j.time_fora.api_id >= 9000000) else ""
        linhas.append(f"""<tr style="border-bottom:1px solid #333">
            <td style="padding:0.4rem 0.6rem;font-size:0.75rem;color:#aaa">{rodada}</td>
            <td style="padding:0.4rem 0.6rem;font-size:0.75rem;color:var(--verde)">{grupo}</td>
            <td style="padding:0.4rem 0.6rem">{ph} {tc} × {tf}</td>
            <td style="padding:0.4rem 0.6rem;color:{cor}">{b_fmt}</td>
            <td style="padding:0.4rem 0.6rem;color:{cor}">{a_fmt}</td>
            <td style="padding:0.4rem 0.6rem;font-size:0.8rem">{"⚠️" if dif else "✅"}</td>
        </tr>""")

    # Jogos na API mas não no banco
    ids_banco = {j.api_id for j in jogos_banco}
    extras = []
    for api_id, f in jogos_api.items():
        if api_id not in ids_banco:
            rodada = f["league"]["round"]
            grupo  = f["league"].get("group") or "—"
            tc     = f["teams"]["home"]["name"]
            tf     = f["teams"]["away"]["name"]
            data   = converter_utc_brasilia(f["fixture"]["date"])
            d_fmt  = data.strftime("%d/%m/%Y %H:%M") if data else "?"
            extras.append(f"""<tr style="border-bottom:1px solid #333;background:rgba(255,150,0,0.08)">
                <td style="padding:0.4rem 0.6rem;font-size:0.75rem;color:#aaa">{rodada}</td>
                <td style="padding:0.4rem 0.6rem;font-size:0.75rem;color:var(--verde)">{grupo}</td>
                <td style="padding:0.4rem 0.6rem">🆕 {tc} × {tf}</td>
                <td style="padding:0.4rem 0.6rem;color:#ff9500">{d_fmt}</td>
                <td style="padding:0.4rem 0.6rem;color:#ff9500">—</td>
                <td style="padding:0.4rem 0.6rem;font-size:0.8rem">🆕 só na API</td>
            </tr>""")

    html = f"""<html><body style="background:#111;color:#eee;font-family:monospace;padding:1.5rem">
    <h2>🌍 Copa do Mundo 2026 — {copa.nome} (league_id={copa.api_league_id})</h2>
    <p style="color:#aaa">{len(jogos_banco)} jogos no banco · {len(jogos_api)} na API · {len(extras)} só na API (faltam importar)</p>
    <div style="margin-bottom:1rem;display:flex;gap:1rem;flex-wrap:wrap">
        <a href="/admin/corrigir_horarios_copa" style="background:#e74c3c;color:#fff;padding:0.5rem 1rem;border-radius:4px;text-decoration:none">⚠️ Corrigir horários diferentes</a>
        <a href="/admin/importar_competicao/{copa.api_league_id}/2026" style="background:#ff9500;color:#000;padding:0.5rem 1rem;border-radius:4px;text-decoration:none">🆕 Importar jogos faltando</a>
    </div>
    <table style="width:100%;border-collapse:collapse">
    <thead><tr style="border-bottom:2px solid #00a651">
        <th style="padding:0.4rem 0.6rem;text-align:left;font-size:0.8rem">Rodada</th>
        <th style="padding:0.4rem 0.6rem;text-align:left;font-size:0.8rem">Grupo</th>
        <th style="padding:0.4rem 0.6rem;text-align:left">Jogo</th>
        <th style="padding:0.4rem 0.6rem;text-align:left">🗄️ Banco</th>
        <th style="padding:0.4rem 0.6rem;text-align:left">🌐 API</th>
        <th style="padding:0.4rem 0.6rem;text-align:left">Status</th>
    </tr></thead>
    <tbody>{"".join(linhas)}{"".join(extras)}</tbody>
    </table></body></html>"""
    return html


@bp.route('/admin/corrigir_horarios_copa')
@admin_required
def corrigir_horarios_copa():
    """Corrige horários da Copa do Mundo em background."""
    import threading
    from flask import current_app
    from app.models import Competicao

    copa = Competicao.query.filter(
        Competicao.nome.ilike('%world cup%') | Competicao.nome.ilike('%copa do mundo%') | Competicao.nome.ilike('%mundial%')
    ).first()
    if not copa:
        return jsonify({"erro": "Copa não encontrada"}), 404

    app = current_app._get_current_object()

    def job():
        from app.scheduler import corrigir_horarios_job
        corrigir_horarios_job(app)

    threading.Thread(target=job, daemon=True).start()
    return jsonify({"sucesso": True, "mensagem": "⏳ Correção iniciada em background"})

@bp.route('/admin/checar_horarios/<int:time_api_id>')
@admin_required
def checar_horarios(time_api_id):
    """
    Compara horários no banco vs API Football para um time.
    Uso: /admin/checar_horarios/118  (118 = Grêmio na API Football)
    """
    import requests, os
    from app.models import Jogo, Time
    from app.utils import converter_utc_brasilia

    time_db = Time.query.filter_by(api_id=time_api_id).first()
    nome_time = time_db.nome if time_db else f"API ID {time_api_id}"

    # Detecta seasons a partir dos jogos no banco (ex: 2025 e 2026)
    if time_db:
        jogos_banco = Jogo.query.filter(
            (Jogo.time_casa_id == time_db.id) | (Jogo.time_fora_id == time_db.id)
        ).order_by(Jogo.data).all()
    else:
        jogos_banco = []

    seasons = set()
    for j in jogos_banco:
        if j.data:
            try:
                seasons.add(int(j.data[:4]))
            except:
                pass
    if not seasons:
        seasons = {2026}

    headers = {"x-apisports-key": os.getenv("API_FOOTBALL_KEY")}
    jogos_api = {}
    for season in seasons:
        r = requests.get(
            "https://v3.football.api-sports.io/fixtures",
            headers=headers,
            params={"team": time_api_id, "season": season},
            timeout=10
        )
        for f in r.json().get("response", []):
            jogos_api[f["fixture"]["id"]] = f

    linhas = []
    for j in jogos_banco:
        api = jogos_api.get(j.api_id)
        data_api_raw = api["fixture"]["date"] if api else "não encontrado na API"
        data_banco   = j.data or "nulo"

        br_banco = converter_utc_brasilia(data_banco)
        br_api   = converter_utc_brasilia(data_api_raw) if api else None

        banco_fmt = br_banco.strftime("%d/%m/%Y %H:%M") if br_banco else data_banco
        api_fmt   = br_api.strftime("%d/%m/%Y %H:%M")   if br_api   else data_api_raw

        diferente = banco_fmt != api_fmt
        cor   = "#e74c3c" if diferente else "#2ecc71"
        icone = "⚠️" if diferente else "✅"

        adv_id = j.time_fora_id if j.time_casa_id == (time_db.id if time_db else -1) else j.time_casa_id
        adv = Time.query.get(adv_id)
        adversario = adv.nome if adv else "?"

        linhas.append(f"""
        <tr style="border-bottom:1px solid #333;">
            <td style="padding:0.5rem">{icone}</td>
            <td style="padding:0.5rem">{j.api_id}</td>
            <td style="padding:0.5rem">{adversario}</td>
            <td style="padding:0.5rem;color:{cor}">{banco_fmt}</td>
            <td style="padding:0.5rem;color:{cor}">{api_fmt}</td>
            <td style="padding:0.5rem;font-weight:bold;color:{cor}">{"DIFERENTE" if diferente else "ok"}</td>
        </tr>""")

    html = f"""<html><body style="background:#1a1a2e;color:#eee;font-family:monospace;padding:2rem">
    <h2>🔍 Horários: {nome_time} (api_id={time_api_id})</h2>
    <p style="color:#aaa">{len(jogos_banco)} jogos no banco · {len(jogos_api)} na API Football · Fuso: Brasília (UTC-3)</p>
    <a href="/admin/corrigir_horarios/{time_api_id}"
       style="background:#e74c3c;color:#fff;padding:0.6rem 1.2rem;border-radius:4px;text-decoration:none;display:inline-block;margin-bottom:1rem">
       ⚠️ Corrigir TODOS os horários diferentes agora
    </a>
    <table style="width:100%;border-collapse:collapse;margin-top:1rem">
        <thead><tr style="border-bottom:2px solid #00a651">
            <th style="padding:0.5rem;text-align:left"></th>
            <th style="padding:0.5rem;text-align:left">API ID</th>
            <th style="padding:0.5rem;text-align:left">Adversário</th>
            <th style="padding:0.5rem;text-align:left">🗄️ Banco (Brasília)</th>
            <th style="padding:0.5rem;text-align:left">🌐 API Football (Brasília)</th>
            <th style="padding:0.5rem;text-align:left">Status</th>
        </tr></thead>
        <tbody>{"".join(linhas) if linhas else "<tr><td colspan=6 style='padding:1rem'>Nenhum jogo encontrado no banco para este time.</td></tr>"}</tbody>
    </table>
    </body></html>"""
    return html


@bp.route('/admin/corrigir_horarios/<int:time_api_id>')
@admin_required
def corrigir_horarios(time_api_id):
    """Corrige horários no banco usando dados atuais da API Football."""
    import requests, os
    from app.models import Jogo, Time

    time_db = Time.query.filter_by(api_id=time_api_id).first()
    if not time_db:
        return jsonify({"erro": "Time não encontrado no banco"}), 404

    jogos_banco_all = Jogo.query.filter(
        (Jogo.time_casa_id == time_db.id) | (Jogo.time_fora_id == time_db.id)
    ).all()
    seasons = set()
    for j in jogos_banco_all:
        if j.data:
            try: seasons.add(int(j.data[:4]))
            except: pass
    if not seasons:
        seasons = {2026}

    headers = {"x-apisports-key": os.getenv("API_FOOTBALL_KEY")}
    jogos_api = {}
    for season in seasons:
        r = requests.get(
            "https://v3.football.api-sports.io/fixtures",
            headers=headers,
            params={"team": time_api_id, "season": season},
            timeout=10
        )
        for f in r.json().get("response", []):
            jogos_api[f["fixture"]["id"]] = f["fixture"]["date"]

    corrigidos = 0
    for jogo in Jogo.query.filter(
        (Jogo.time_casa_id == time_db.id) | (Jogo.time_fora_id == time_db.id)
    ).all():
        if jogo.api_id in jogos_api:
            nova_data = jogos_api[jogo.api_id]
            if nova_data != jogo.data:
                jogo.data = nova_data
                corrigidos += 1

    db.session.commit()
    return jsonify({
        "sucesso": True,
        "time": time_db.nome,
        "corrigidos": corrigidos,
        "total_verificados": len(jogos_api),
        "mensagem": f"✅ {corrigidos} horários corrigidos para {time_db.nome}"
    })


@bp.route('/admin/corrigir_horarios_todos')
@admin_required
def corrigir_horarios_todos():
    """
    Dispara a correção de horários em background e retorna imediatamente.
    O job roda em thread separada para não travar o Gunicorn.
    """
    import threading
    from flask import current_app

    app = current_app._get_current_object()

    def job_background():
        from app.scheduler import corrigir_horarios_job
        corrigir_horarios_job(app)

    t = threading.Thread(target=job_background, daemon=True)
    t.start()

    return jsonify({
        "sucesso": True,
        "mensagem": "⏳ Correção iniciada em background. Acompanhe os logs do Render. Leva ~2-5 minutos."
    })

@bp.route('/migrar_logos_cloudinary')
@admin_required
def migrar_logos_cloudinary():
    """
    Processa todos os times que têm logo_url da API Football
    e faz re-upload para o Cloudinary.
    Processa em lotes de 20 para evitar timeout.
    """
    from app.api import upload_logo_cloudinary
    from app.models import Time

    offset = request.args.get('offset', 0, type=int)
    lote = 20

    # Times com logo_url que não seja do Cloudinary
    times = Time.query.filter(
        Time.logo_url.isnot(None),
        Time.logo_url != '',
        ~Time.logo_url.like('%cloudinary%')
    ).offset(offset).limit(lote).all()

    total_pendente = Time.query.filter(
        Time.logo_url.isnot(None),
        Time.logo_url != '',
        ~Time.logo_url.like('%cloudinary%')
    ).count()

    atualizados = 0
    erros = []

    for time in times:
        nova_url = upload_logo_cloudinary(time.api_id, time.logo_url)
        if nova_url:
            time.logo_url = nova_url
            atualizados += 1
        else:
            erros.append(f"{time.nome} (api_id={time.api_id})")

    db.session.commit()

    proximo_offset = offset + lote
    tem_mais = proximo_offset < total_pendente

    return jsonify({
        'sucesso': True,
        'lote': lote,
        'offset': offset,
        'atualizados_agora': atualizados,
        'total_pendente_restante': max(0, total_pendente - lote),
        'erros': erros,
        'proximo': f'/migrar_logos_cloudinary?offset={proximo_offset}' if tem_mais else None,
        'mensagem': f'✅ Pronto! Todos processados.' if not tem_mais else f'⏳ Rode o próximo: offset={proximo_offset}'
    })

@bp.route('/migrar_grupo_e_logos')
@admin_required
def migrar_grupo_e_logos():
    """
    1. Adiciona coluna 'grupo' em jogo se não existir (DDL, rápido)
    2. Dispara re-sincronização de logos e grupos em background
    """
    from sqlalchemy import text, inspect
    import threading
    from flask import current_app

    resultados = {'colunas': [], 'erros': []}

    # Passo 1: DDL é rápido, pode rodar inline
    try:
        inspector = inspect(db.engine)
        cols = [c['name'] for c in inspector.get_columns('jogo')]
        if 'grupo' not in cols:
            db.session.execute(text("ALTER TABLE jogo ADD COLUMN grupo VARCHAR(50) DEFAULT ''"))
            db.session.commit()
            resultados['colunas'].append('grupo adicionada em jogo')
        else:
            resultados['colunas'].append('grupo já existia')
    except Exception as e:
        resultados['erros'].append(f"coluna grupo: {str(e)}")

    # Passo 2: API calls pesadas → background
    app = current_app._get_current_object()

    def job_background():
        with app.app_context():
            try:
                from app.api import get_jogos_competicao, processar_jogos, upload_logo_cloudinary
                from app.models import Competicao, Jogo, Time
                logos = 0
                grupos = 0
                for comp in Competicao.query.all():
                    if not comp.api_league_id:
                        continue
                    try:
                        jogos_comp = Jogo.query.filter_by(competicao_id=comp.id).all()
                        seasons = set()
                        for j in jogos_comp:
                            if j.data:
                                try: seasons.add(int(j.data[:4]))
                                except: pass
                        if not seasons:
                            seasons = {comp.ano}
                        for season in seasons:
                            data = get_jogos_competicao(comp.api_league_id, season)
                            for jogo_raw in processar_jogos(data):
                                # Logos
                                for key, logo_key in [('time_casa_id','logo_casa'),('time_fora_id','logo_fora')]:
                                    t = Time.query.filter_by(api_id=jogo_raw[key]).first()
                                    if t and jogo_raw.get(logo_key) and not (t.logo_url or '').startswith('http'):
                                        nova = upload_logo_cloudinary(t.api_id, jogo_raw[logo_key])
                                        if nova:
                                            t.logo_url = nova
                                            logos += 1
                                # Grupos
                                jogo_db = Jogo.query.filter_by(api_id=jogo_raw['api_id']).first()
                                if jogo_db and jogo_raw.get('grupo') and not jogo_db.grupo:
                                    jogo_db.grupo = jogo_raw['grupo']
                                    grupos += 1
                            db.session.commit()
                    except Exception as e:
                        print(f"[BG] Erro {comp.nome}: {e}")
                print(f"[BG] migrar_grupo_e_logos: {logos} logos, {grupos} grupos atualizados ✅")
            except Exception as e:
                print(f"[BG] Erro geral migrar_grupo_e_logos: {e}")

    t = threading.Thread(target=job_background, daemon=True)
    t.start()

    return jsonify({
        'sucesso': True,
        **resultados,
        'mensagem': '⏳ Logos e grupos sendo atualizados em background (~2-5 min). Veja logs do Render.'
    })


@bp.route('/migrar_reset_senha_render')
def migrar_reset_senha_render():
    from sqlalchemy import text, inspect
    try:
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('usuario')]
        
        if 'reset_token' not in columns:
            db.session.execute(text("ALTER TABLE usuario ADD COLUMN reset_token VARCHAR(100)"))
        if 'reset_token_expira' not in columns:
            db.session.execute(text("ALTER TABLE usuario ADD COLUMN reset_token_expira TIMESTAMP"))
        
        db.session.commit()
        return jsonify({'sucesso': True, 'mensagem': 'Colunas adicionadas!'})
    except Exception as e:
        return jsonify({'erro': str(e)}), 500


@bp.route('/admin/popular_grupos_standings')
@admin_required  
def popular_grupos_standings():
    """Busca /standings da Copa 2026 e popula jogo.grupo no banco."""
    import requests, os, threading
    from flask import current_app
    app = current_app._get_current_object()

    def job():
        with app.app_context():
            from app.models import Competicao, Jogo, Time
            from app import db
            import requests, os

            headers = {"x-apisports-key": os.getenv("API_FOOTBALL_KEY")}
            r = requests.get(
                "https://v3.football.api-sports.io/standings",
                headers=headers,
                params={"league": 1, "season": 2026},
                timeout=15
            )
            data = r.json()

            # Montar mapeamento team_api_id → grupo
            time_grupo = {}
            for liga in data.get("response", []):
                for grupo_list in liga.get("league", {}).get("standings", []):
                    for entry in grupo_list:
                        team_id = entry["team"]["id"]
                        grupo   = entry.get("group", "")
                        if grupo:
                            time_grupo[team_id] = grupo

            print(f"[STANDINGS] {len(time_grupo)} times com grupo mapeado")

            copa = Competicao.query.filter_by(api_league_id=1, ano=2026).first()
            if not copa:
                print("[STANDINGS] Copa 2026 não encontrada")
                return

            atualizados = 0
            for jogo in Jogo.query.filter_by(competicao_id=copa.id).all():
                tc = jogo.time_casa
                tf = jogo.time_fora
                grupo = None
                if tc and tc.api_id in time_grupo:
                    grupo = time_grupo[tc.api_id]
                elif tf and tf.api_id in time_grupo:
                    grupo = time_grupo[tf.api_id]
                if grupo and jogo.grupo != grupo:
                    jogo.grupo = grupo
                    atualizados += 1

            db.session.commit()
            print(f"[STANDINGS] {atualizados} jogos atualizados com grupo ✅")

    threading.Thread(target=job, daemon=True).start()
    return jsonify({"sucesso": True, "mensagem": "⏳ Populando grupos via standings em background"})


@bp.route('/copa2026')
def copa2026():
    """Página pública com dados ao vivo da Copa do Mundo 2026."""
    import requests, os
    from app.utils import converter_utc_brasilia

    headers = {"x-apisports-key": os.getenv("API_FOOTBALL_KEY")}

    # Standings (classificação por grupo)
    standings = []
    try:
        r = requests.get("https://v3.football.api-sports.io/standings",
            headers=headers, params={"league": 1, "season": 2026}, timeout=10)
        for liga in r.json().get("response", []):
            for grupo_list in liga.get("league", {}).get("standings", []):
                if grupo_list:
                    grupo_nome = grupo_list[0].get("group", "")
                    standings.append({
                        "grupo": grupo_nome,
                        "times": grupo_list
                    })
        standings.sort(key=lambda x: x["grupo"])
    except Exception as e:
        print(f"[copa2026] standings erro: {e}")

    # Artilheiros
    artilheiros = []
    try:
        r = requests.get("https://v3.football.api-sports.io/players/topscorers",
            headers=headers, params={"league": 1, "season": 2026}, timeout=10)
        artilheiros = r.json().get("response", [])[:10]
    except Exception as e:
        print(f"[copa2026] artilheiros erro: {e}")

    # Próximos jogos
    proximos = []
    try:
        r = requests.get("https://v3.football.api-sports.io/fixtures",
            headers=headers, params={"league": 1, "season": 2026, "next": 12}, timeout=10)
        for f in r.json().get("response", []):
            data_br = converter_utc_brasilia(f["fixture"]["date"])
            proximos.append({
                "data":       data_br.strftime("%d/%m às %H:%M") if data_br else "?",
                "rodada":     f["league"]["round"],
                "grupo":      f["league"].get("group") or "",
                "casa":       f["teams"]["home"]["name"],
                "fora":       f["teams"]["away"]["name"],
                "logo_casa":  f["teams"]["home"].get("logo",""),
                "logo_fora":  f["teams"]["away"].get("logo",""),
                "status":     f["fixture"]["status"]["short"],
                "gols_casa":  f["goals"]["home"],
                "gols_fora":  f["goals"]["away"],
            })
    except Exception as e:
        print(f"[copa2026] próximos erro: {e}")

    # Últimos resultados
    resultados = []
    try:
        r = requests.get("https://v3.football.api-sports.io/fixtures",
            headers=headers, params={"league": 1, "season": 2026, "last": 12}, timeout=10)
        for f in r.json().get("response", []):
            data_br = converter_utc_brasilia(f["fixture"]["date"])
            resultados.append({
                "data":       data_br.strftime("%d/%m %H:%M") if data_br else "?",
                "grupo":      f["league"].get("group") or "",
                "casa":       f["teams"]["home"]["name"],
                "fora":       f["teams"]["away"]["name"],
                "logo_casa":  f["teams"]["home"].get("logo",""),
                "logo_fora":  f["teams"]["away"].get("logo",""),
                "gols_casa":  f["goals"]["home"],
                "gols_fora":  f["goals"]["away"],
                "vencedor":   f["teams"]["home"]["winner"],
            })
    except Exception as e:
        print(f"[copa2026] resultados erro: {e}")

    return render_template("copa2026.html",
        standings=standings,
        artilheiros=artilheiros,
        proximos=proximos,
        resultados=resultados
    )

@bp.route('/admin/popular_grupos_copa')
@admin_required
def popular_grupos_copa():
    """
    Popula o campo grupo para todos os jogos da Copa do Mundo 2026.
    Derivado do sorteio oficial (API Football não retorna esse campo).
    """
    from app.models import Competicao, Jogo, Time

    # Mapeamento oficial: time → grupo (derivado do sorteio dez/2024)
    TIME_GRUPO = {
        "Mexico": "Group A", "South Africa": "Group A",
        "South Korea": "Group A", "Czech Republic": "Group A",
        "Canada": "Group B", "Switzerland": "Group B",
        "Qatar": "Group B", "Bosnia & Herzegovina": "Group B",
        "USA": "Group C", "Paraguay": "Group C",
        "Australia": "Group C", "Türkiye": "Group C",
        "Brazil": "Group D", "Morocco": "Group D",
        "Haiti": "Group D", "Scotland": "Group D",
        "Germany": "Group E", "Ecuador": "Group E",
        "Ivory Coast": "Group E", "Curaçao": "Group E",
        "Netherlands": "Group F", "Japan": "Group F",
        "Sweden": "Group F", "Tunisia": "Group F",
        "Spain": "Group G", "Uruguay": "Group G",
        "Saudi Arabia": "Group G", "Cape Verde Islands": "Group G",
        "Belgium": "Group H", "Egypt": "Group H",
        "Iran": "Group H", "New Zealand": "Group H",
        "France": "Group I", "Senegal": "Group I",
        "Norway": "Group I", "Iraq": "Group I",
        "England": "Group J", "Croatia": "Group J",
        "Panama": "Group J", "Ghana": "Group J",
        "Portugal": "Group K", "Uzbekistan": "Group K",
        "Colombia": "Group K", "Congo DR": "Group K",
        "Argentina": "Group L", "Algeria": "Group L",
        "Austria": "Group L", "Jordan": "Group L",
    }

    copa = Competicao.query.filter(
        Competicao.api_league_id == 1,
        Competicao.ano == 2026
    ).first()
    if not copa:
        return jsonify({"erro": "World Cup 2026 não encontrado"}), 404

    atualizados = 0
    nao_encontrados = []

    for jogo in Jogo.query.filter_by(competicao_id=copa.id).all():
        tc = jogo.time_casa.nome if jogo.time_casa else ""
        grupo = TIME_GRUPO.get(tc)
        if not grupo:
            tf = jogo.time_fora.nome if jogo.time_fora else ""
            grupo = TIME_GRUPO.get(tf)
        if grupo and jogo.grupo != grupo:
            jogo.grupo = grupo
            atualizados += 1
        elif not grupo:
            nao_encontrados.append(f"{tc} × {jogo.time_fora.nome if jogo.time_fora else '?'}")

    db.session.commit()
    return jsonify({
        "sucesso": True,
        "atualizados": atualizados,
        "nao_encontrados": nao_encontrados,
        "mensagem": f"✅ {atualizados} jogos com grupo definido"
    })

@bp.route('/admin/popular_grupos/<int:competicao_id>')
@admin_required
def popular_grupos(competicao_id):
    """Busca o campo grupo de cada jogo direto na API Football e salva no banco."""
    import requests, os, threading
    from flask import current_app
    from app.models import Competicao, Jogo

    comp = Competicao.query.get_or_404(competicao_id)
    app = current_app._get_current_object()

    def job():
        with app.app_context():
            from app.models import Competicao, Jogo
            from app import db
            import requests, os

            comp = Competicao.query.get(competicao_id)
            headers = {"x-apisports-key": os.getenv("API_FOOTBALL_KEY")}

            seasons = set()
            for j in Jogo.query.filter_by(competicao_id=comp.id).all():
                if j.data:
                    try: seasons.add(int(j.data[:4]))
                    except: pass
            if not seasons:
                seasons = {comp.ano}

            atualizados = 0
            for season in seasons:
                r = requests.get(
                    "https://v3.football.api-sports.io/fixtures",
                    headers=headers,
                    params={"league": comp.api_league_id, "season": season},
                    timeout=15
                )
                for f in r.json().get("response", []):
                    grupo = f["league"].get("group") or ""
                    if not grupo:
                        continue
                    jogo = Jogo.query.filter_by(api_id=f["fixture"]["id"]).first()
                    if jogo and jogo.grupo != grupo:
                        jogo.grupo = grupo
                        atualizados += 1

            db.session.commit()
            print(f"[popular_grupos] {comp.nome}: {atualizados} grupos atualizados ✅")

    threading.Thread(target=job, daemon=True).start()
    return jsonify({"sucesso": True, "competicao": comp.nome, "mensagem": f"⏳ Populando grupos em background. Veja logs."})


@bp.route('/admin/trocar_competicao/<int:bolao_id>/<int:nova_competicao_id>')
@admin_required
def trocar_competicao_bolao(bolao_id, nova_competicao_id):
    """Troca a competição de um bolão."""
    from app.models import Bolao, Competicao
    bolao = Bolao.query.get_or_404(bolao_id)
    nova  = Competicao.query.get_or_404(nova_competicao_id)
    antiga = bolao.competicao.nome
    bolao.competicao_id = nova_competicao_id
    db.session.commit()
    return jsonify({'sucesso': True, 'bolao': bolao.nome, 'de': antiga, 'para': nova.nome})

