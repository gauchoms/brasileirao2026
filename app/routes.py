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
    return render_template('index.html')