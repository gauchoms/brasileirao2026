from flask import Blueprint, render_template, request, jsonify
from app import db
from app.models import Time, Jogo, Projecao, Meta

bp = Blueprint('main', __name__)

METAS = {
    'titulo': 80,
    'libertadores': 70,
    'rebaixamento': 45
}

@bp.route('/')
def index():
    return render_template('index.html')

@bp.route('/projecoes')
def projecoes():
    times = Time.query.order_by(Time.nome).all()
    time_id = request.args.get('time_id', type=int)
    projecao_selecionada = request.args.get('projecao', 'titulo')

    time_selecionado = None
    jogos = []
    pontos_projetados = 0
    meta = METAS.get(projecao_selecionada, 80)

    if time_id:
        time_selecionado = Time.query.get(time_id)

        todos_jogos = Jogo.query.filter(
            (Jogo.time_casa_id == time_id) | (Jogo.time_fora_id == time_id)
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
        times=times,
        time_selecionado=time_selecionado,
        projecao_selecionada=projecao_selecionada,
        jogos=jogos,
        pontos_projetados=pontos_projetados,
        meta=meta
    )

@bp.route('/salvar_projecao', methods=['POST'])
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
def atualizar_resultados():
    from app.api import get_resultados_brasileirao

    data = get_resultados_brasileirao()
    jogos = data.get('response', [])
    atualizados = 0

    for fixture in jogos:
        api_id = fixture['fixture']['id']
        gols_casa = fixture['goals']['home']
        gols_fora = fixture['goals']['away']

        jogo = Jogo.query.filter_by(api_id=api_id).first()
        if jogo and gols_casa is not None and gols_fora is not None:
            jogo.gols_casa = gols_casa
            jogo.gols_fora = gols_fora
            atualizados += 1

    db.session.commit()
    return jsonify({'sucesso': True, 'atualizados': atualizados})

@bp.route('/dashboard')
def dashboard():
    times = Time.query.order_by(Time.nome).all()
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
        # Pontos reais acumulados
        pontos_reais = 0
        jogos_time = Jogo.query.filter(
            (Jogo.time_casa_id == time.id) | (Jogo.time_fora_id == time.id)
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
            pontos_proj = db.session.query(db.func.sum(Projecao.pontos)).filter(
                Projecao.time_id == time.id,
                Projecao.tipo == tipo
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
            (Jogo.time_casa_id == time_id) | (Jogo.time_fora_id == time_id)
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
        from app.models import Time, Jogo, Projecao, Meta
        db.create_all()
        
        # Verifica se já tem times
        count_times = Time.query.count()
        count_jogos = Jogo.query.count()
        
        return jsonify({
            'status': 'ok',
            'times_cadastrados': count_times,
            'jogos_cadastrados': count_jogos,
            'mensagem': 'Tabelas criadas. Use /importar_times e /importar_jogos'
        })
    except Exception as e:
        return jsonify({'erro': str(e)}), 500


@bp.route('/importar_times')
def importar_times():
    from app.api import get_jogos_brasileirao, processar_jogos
    
    if Time.query.count() > 0:
        return jsonify({'mensagem': 'Times já importados', 'total': Time.query.count()})
    
    data = get_jogos_brasileirao()
    jogos = processar_jogos(data)
    
    times_unicos = {}
    for jogo in jogos:
        times_unicos[jogo['time_casa_id']] = jogo['time_casa']
        times_unicos[jogo['time_fora_id']] = jogo['time_fora']
    
    for api_id, nome in times_unicos.items():
        time = Time(api_id=api_id, nome=nome)
        db.session.add(time)
    
    db.session.commit()
    return jsonify({'sucesso': True, 'times_importados': len(times_unicos)})

@bp.route('/importar_jogos')
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

