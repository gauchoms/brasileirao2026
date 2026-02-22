from flask import Blueprint, render_template, request, jsonify, redirect
from app import db
from app.models import Time, Jogo, Projecao, Meta, Competicao, Bolao, ParticipanteBolao, RegraPontuacao,Palpite

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
        competicoes=competicoes_disponiveis,
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
    ligas = listar_ligas_disponiveis(ano)
    
    # Filtra só ligas de campeonatos relevantes
    ligas_filtradas = [
        l for l in ligas 
        if l['tipo'] in ['League', 'Cup'] and l['pais'] in [
            'World', 'Brazil', 'England', 'Spain', 'Italy', 'Germany', 'France', 
            'Argentina', 'Uruguay', 'Colombia', 'Chile', 'Ecuador', 'Peru'
        ]
    ]
    
    return render_template('admin/listar_ligas.html', ligas=ligas_filtradas, ano=ano)

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
        
        db.session.add(novo_usuario)
        db.session.commit()
        
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
        competicao_id = request.form.get('competicao_id', type=int)
        regra_pontuacao_id = request.form.get('regra_pontuacao_id', type=int)
        tipo_acesso = request.form.get('tipo_acesso', 'publico')
        
        # Gera código de convite único
        codigo_convite = secrets.token_urlsafe(6).upper()[:8]
        
        # Cria o bolão
        novo_bolao = Bolao(
            nome=nome,
            competicao_id=competicao_id,
            dono_id=current_user.id,
            codigo_convite=codigo_convite,
            regra_pontuacao_id=regra_pontuacao_id,
            tipo_acesso=tipo_acesso,
            status_pagamento='pendente',
            valor_pago=15.00
        )
        
        db.session.add(novo_bolao)
        db.session.commit()
        
        # TODO: Redirecionar para pagamento Mercado Pago
        # Por enquanto, vamos direto para o bolão
        return redirect(f'/bolao/{novo_bolao.id}')
    
    # GET - mostra formulário
    competicoes = Competicao.query.all()
    
    # Cria regra padrão se não existir
    regra_padrao = RegraPontuacao.query.first()
    if not regra_padrao:
        regra_padrao = RegraPontuacao(
            nome='Padrão',
            criador_id=1,  # Admin
            pontos_placar_exato=5,
            pontos_resultado_certo=3,
            pontos_gols_time_casa=1,
            pontos_gols_time_fora=1
        )
        db.session.add(regra_padrao)
        db.session.commit()
    
    regras = RegraPontuacao.query.filter_by(publica=True).all()
    
    return render_template('criar_bolao.html', competicoes=competicoes, regras=regras)


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
    
    # Busca jogos da competição
    jogos = Jogo.query.filter_by(competicao_id=bolao.competicao_id).order_by(Jogo.data).all()
    
    # Busca palpites do usuário neste bolão
    palpites_usuario = {}
    palpites = Palpite.query.filter_by(bolao_id=bolao_id, usuario_id=current_user.id).all()
    for p in palpites:
        palpites_usuario[p.jogo_id] = p
    
    return render_template('bolao_detalhes.html', 
                         bolao=bolao, 
                         eh_dono=eh_dono,
                         jogos=jogos,
                         palpites_usuario=palpites_usuario)


@bp.route('/salvar_palpite', methods=['POST'])
@login_required
def salvar_palpite():
    from app.models import Palpite
    
    data = request.get_json()
    bolao_id = data.get('bolao_id')
    jogo_id = data.get('jogo_id')
    gols_casa = data.get('gols_casa')
    gols_fora = data.get('gols_fora')
    
    # Verifica se o jogo já aconteceu
    jogo = Jogo.query.get(jogo_id)
    if jogo.gols_casa is not None:
        return jsonify({'erro': 'Jogo já aconteceu, não pode mais palpitar'}), 400
    
    # Busca ou cria palpite
    palpite = Palpite.query.filter_by(
        bolao_id=bolao_id,
        usuario_id=current_user.id,
        jogo_id=jogo_id
    ).first()
    
    if palpite:
        palpite.gols_casa_palpite = gols_casa
        palpite.gols_fora_palpite = gols_fora
    else:
        palpite = Palpite(
            bolao_id=bolao_id,
            usuario_id=current_user.id,
            jogo_id=jogo_id,
            gols_casa_palpite=gols_casa,
            gols_fora_palpite=gols_fora
        )
        db.session.add(palpite)
    
    db.session.commit()
    
    return jsonify({'sucesso': True})


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
        brasileirao = Competicao.query.filter(Competicao.nome.like('%Brasileirão%')).first()
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
