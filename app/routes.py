from flask import Blueprint, render_template, request, jsonify, redirect
from app import db
from datetime import datetime
from app.models import Time, Jogo, Projecao, Meta, Competicao, Bolao, ParticipanteBolao, RegraPontuacao,Palpite,SolicitacaoEntrada
import os
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from functools import wraps
from app.models import Time, Jogo, Projecao, Meta, Competicao

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
    """
    pontos = 0
    
    # Placar exato
    placar_exato = (palpite.gols_casa_palpite == jogo.gols_casa and 
                    palpite.gols_fora_palpite == jogo.gols_fora)
    
    if placar_exato:
        pontos += regra.pontos_placar_exato
        
        # Se modo A (só placar exato), retorna aqui
        if regra.modo == 'placar_exato':
            return pontos
    
    # Se modo A e não acertou placar exato, retorna 0
    if regra.modo == 'placar_exato' and not placar_exato:
        return 0
    
    # Se acertou placar exato no modo B ou C, não soma acertos parciais
    if placar_exato:
        # Mas se for modo C, ainda pode ganhar bônus de gols
        if regra.modo == 'com_bonus':
            total_gols = jogo.gols_casa + jogo.gols_fora
            if total_gols > regra.limite_gols_bonus:
                gols_extras = total_gols - regra.limite_gols_bonus
                pontos += gols_extras * regra.pontos_por_gol_extra
        return pontos
    
    # Acertos parciais (modo B e C)
    
    # Determina vencedor/perdedor/empate
    resultado_real = 'empate' if jogo.gols_casa == jogo.gols_fora else ('casa' if jogo.gols_casa > jogo.gols_fora else 'fora')
    resultado_palpite = 'empate' if palpite.gols_casa_palpite == palpite.gols_fora_palpite else ('casa' if palpite.gols_casa_palpite > palpite.gols_fora_palpite else 'fora')
    
    # Acertou gols do vencedor
    if resultado_real != 'empate' and resultado_palpite == resultado_real:
        gols_vencedor_real = jogo.gols_casa if resultado_real == 'casa' else jogo.gols_fora
        gols_vencedor_palpite = palpite.gols_casa_palpite if resultado_palpite == 'casa' else palpite.gols_fora_palpite
        
        if gols_vencedor_real == gols_vencedor_palpite:
            pontos += regra.pontos_gols_vencedor
    
    # Acertou gols do perdedor
    if resultado_real != 'empate' and resultado_palpite == resultado_real:
        gols_perdedor_real = jogo.gols_fora if resultado_real == 'casa' else jogo.gols_casa
        gols_perdedor_palpite = palpite.gols_fora_palpite if resultado_palpite == 'casa' else palpite.gols_casa_palpite
        
        if gols_perdedor_real == gols_perdedor_palpite:
            pontos += regra.pontos_gols_perdedor
    
    # Acertou diferença de gols
    diferenca_real = abs(jogo.gols_casa - jogo.gols_fora)
    diferenca_palpite = abs(palpite.gols_casa_palpite - palpite.gols_fora_palpite)
    
    if diferenca_real == diferenca_palpite:
        pontos += regra.pontos_diferenca_gols
    
    # Bônus por jogos elásticos (só modo C)
    if regra.modo == 'com_bonus':
        total_gols = jogo.gols_casa + jogo.gols_fora
        if total_gols > regra.limite_gols_bonus:
            gols_extras = total_gols - regra.limite_gols_bonus
            pontos += gols_extras * regra.pontos_por_gol_extra
    
    return pontos

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
    from app.models import Palpite, Bolao, ParticipanteBolao

    data = get_resultados_brasileirao()
    jogos = data.get('response', [])
    
    novos_atualizados = 0
    ja_tinham_placar = 0
    palpites_calculados = 0

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
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = Usuario.query.filter_by(username=username).first()
        
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
                time = Time.query.filter_by(api_id=api_id).first()
                if not time:
                    time = Time(api_id=api_id, nome=nome)
                    db.session.add(time)
                    db.session.flush()
                times_cadastrados[api_id] = time.id
        
        # Cadastra jogo
        jogo_existente = Jogo.query.filter_by(api_id=jogo['api_id']).first()
        if not jogo_existente:
            novo_jogo = Jogo(
                api_id=jogo['api_id'],
                competicao_id=competicao.id,
                rodada=jogo['rodada'],
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
        
        return redirect('/perfil')
    
    return render_template('registro.html')

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
                from werkzeug.utils import secure_filename
                from PIL import Image
                import os
                
                filename = secure_filename(f"user_{current_user.id}_{file.filename}")
                filepath = os.path.join('app', 'static', 'uploads', 'avatars', filename)
                
                # Cria pasta se não existir
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                
                # Redimensiona e salva
                img = Image.open(file)
                img = img.resize((200, 200), Image.Resampling.LANCZOS)
                img.save(filepath)
                
                current_user.avatar_custom_url = f'/static/uploads/avatars/{filename}'
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
        
        # Cria a regra de pontuação conforme o modo
        if modo_pontuacao == 'placar_exato':
            regra = RegraPontuacao(
                nome=f"Regra de {nome}",
                criador_id=current_user.id,
                modo='placar_exato',
                pontos_placar_exato=request.form.get('pts_placar_exato_a', 10, type=int),
                pontos_gols_vencedor=0,
                pontos_gols_perdedor=0,
                pontos_diferenca_gols=0
            )
        elif modo_pontuacao == 'acertos_parciais':
            regra = RegraPontuacao(
                nome=f"Regra de {nome}",
                criador_id=current_user.id,
                modo='acertos_parciais',
                pontos_placar_exato=request.form.get('pts_placar_exato_b', 10, type=int),
                pontos_gols_vencedor=request.form.get('pts_gols_vencedor_b', 3, type=int),
                pontos_gols_perdedor=request.form.get('pts_gols_perdedor_b', 1, type=int),
                pontos_diferenca_gols=request.form.get('pts_diferenca_gols_b', 2, type=int)
            )
        else:  # com_bonus
            regra = RegraPontuacao(
                nome=f"Regra de {nome}",
                criador_id=current_user.id,
                modo='com_bonus',
                pontos_placar_exato=request.form.get('pts_placar_exato_c', 10, type=int),
                pontos_gols_vencedor=request.form.get('pts_gols_vencedor_c', 3, type=int),
                pontos_gols_perdedor=request.form.get('pts_gols_perdedor_c', 1, type=int),
                pontos_diferenca_gols=request.form.get('pts_diferenca_gols_c', 2, type=int),
                limite_gols_bonus=request.form.get('limite_gols_bonus', 4, type=int),
                pontos_por_gol_extra=request.form.get('pts_por_gol_extra', 1, type=int)
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
    
    # Se não é dono e não participa, redireciona
    if not eh_dono and not participa:
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
    
    return render_template('bolao_detalhes.html', 
                         bolao=bolao, 
                         eh_dono=eh_dono,
                         jogos=jogos,
                         palpites_usuario=palpites_usuario,
                         solicitacoes_pendentes=solicitacoes_pendentes,
                         todos_palpites=todos_palpites,
                         agora=datetime.now().strftime('%Y-%m-%dT%H:%M:%S'))


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
    
    # Verifica se jogo ainda não começou
    jogo = Jogo.query.get_or_404(jogo_id)
    if jogo.data:
        from datetime import datetime
        data_jogo = datetime.strptime(jogo.data, '%Y-%m-%dT%H:%M:%S')
        if datetime.now() >= data_jogo:
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
            return render_template('entrar_bolao.html', erro=f'Você já participa do bolão "{bolao.nome}"!')
        
        # Verifica se é o dono
        if bolao.dono_id == current_user.id:
            return render_template('entrar_bolao.html', erro=f'Você é o criador do bolão "{bolao.nome}"!')
        
        # PÚBLICO: Entra automaticamente
        if bolao.tipo_acesso == 'publico':
            participante = ParticipanteBolao(
                bolao_id=bolao.id,
                usuario_id=current_user.id,
                pontos_totais=0
            )
            db.session.add(participante)
            db.session.commit()
    
            # Envia email para o usuário
            if solicitacao.usuario.email:
                from app.email import email_solicitacao_respondida
                email_solicitacao_respondida(solicitacao, acao == 'aprovar')
            
            return jsonify({'sucesso': True})
            
            
        
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
            
            return render_template('entrar_bolao.html', 
                sucesso=f'Solicitação enviada para o bolão "{bolao.nome}"! Aguarde aprovação.')
    
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
    from app.comprovante import gerar_qr_code
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import cm
    from io import BytesIO
    from datetime import datetime
    
    palpite = Palpite.query.get_or_404(palpite_id)
    
    # Verifica se é o dono do palpite
    if palpite.usuario_id != current_user.id:
        return "Acesso negado", 403
    
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
    c.drawString(3*cm, y, f"Data/Hora: {timestamp_dt.strftime('%d/%m/%Y às %H:%M:%S.%f')[:-3]}")
    
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
    c.drawCentredString(width/2, 2*cm, "Este comprovante é imutável e criptograficamente seguro")
    c.drawCentredString(width/2, 1.5*cm, "Brasileirão 2026 - www.brasileirao2026.com")
    
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