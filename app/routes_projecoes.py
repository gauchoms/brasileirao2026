"""
Rotas de visualização de projeções
Gráficos: Linhas, Barras, Vídeos Animados
"""

from flask import Blueprint, Response, render_template_string
from app.models import Competicao, Time, Jogo, Projecao
from app import db
import json

bp_projecoes = Blueprint('graficos', __name__, url_prefix='/graficos')

# ========================================
# CONFIGURAÇÕES
# ========================================

# Metas por tipo
METAS = {
    'titulo': 80,
    'libertadores': 70,
    'rebaixamento': 45
}

METAS_LABELS = {
    'titulo': '🏆 Título',
    'libertadores': '🌎 Libertadores',
    'rebaixamento': '⚠️ Rebaixamento'
}

# Cores oficiais dos times brasileiros
CORES_TIMES = {
    'Flamengo': '#E31937', 'Palmeiras': '#006437', 'Corinthians': '#000000',
    'São Paulo': '#FF0000', 'Sao Paulo': '#FF0000', 'Grêmio': '#0088CC',
    'Gremio': '#0088CC', 'Internacional': '#D60000', 'Atlético-MG': '#000000',
    'Atletico-MG': '#000000', 'Santos': '#FFFFFF', 'Vasco': '#000000',
    'Botafogo': '#000000', 'Fluminense': '#7D2A2F', 'Bahia': '#0059B3',
    'Cruzeiro': '#003399', 'Athletico-PR': '#D41F1B', 'Fortaleza': '#CE2029',
    'Cuiabá': '#F7CA1A', 'Cuiaba': '#F7CA1A', 'Coritiba': '#00653A',
    'América-MG': '#006838', 'America-MG': '#006838', 'Goiás': '#006838',
    'Goias': '#006838', 'Avaí': '#0057A8', 'Avai': '#0057A8',
    'Red Bull Bragantino': '#E30613', 'RB Bragantino': '#E30613',
    'Atlético-GO': '#E30613', 'Atletico-GO': '#E30613', 'Ceará': '#000000',
    'Ceara': '#000000', 'Sport': '#C8102E', 'Vitória': '#DA291C',
    'Vitoria': '#DA291C', 'Chapecoense': '#008837', 'Chapecoense-sc': '#008837',
    'Criciúma': '#FFC72C', 'Criciuma': '#FFC72C', 'Juventude': '#006837',
    'Brusque': '#FF0000', 'Ponte Preta': '#000000', 'Mirassol': '#FFD700',
    'remo': '#003399',
}

def get_cor_time(nome_time):
    """Retorna cor do time ou cinza se não encontrar"""
    return CORES_TIMES.get(nome_time, '#808080')


# ========================================
# PÁGINA DE NAVEGAÇÃO
# ========================================

@bp_projecoes.route('/')
@bp_projecoes.route('/navegacao')
def navegacao():
    """Página principal com todos os gráficos disponíveis"""
    
    competicoes = Competicao.query.all()
    comp_times = {}
    
    for comp in competicoes:
        jogos = Jogo.query.filter_by(competicao_id=comp.id).limit(50).all()
        times_ids = set()
        for jogo in jogos[:30]:
            times_ids.add(jogo.time_casa_id)
            times_ids.add(jogo.time_fora_id)
        
        times = Time.query.filter(Time.id.in_(list(times_ids)[:15])).all()
        comp_times[comp.id] = times
    
    html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Visualizações de Projeções</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%);
            color: #fff;
            padding: 40px 20px;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        h1 {
            text-align: center;
            font-size: 2.5rem;
            margin-bottom: 10px;
            background: linear-gradient(45deg, #00ff88, #00ccff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .subtitle { text-align: center; color: #888; margin-bottom: 30px; }
        
        /* Filtro de Competição */
        .filter-section {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 15px;
            padding: 20px 30px;
            margin-bottom: 40px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            display: flex;
            align-items: center;
            gap: 20px;
        }
        
        .filter-label {
            font-size: 1.2rem;
            font-weight: 600;
            color: #00ff88;
            white-space: nowrap;
        }
        
        .filter-select {
            flex: 1;
            padding: 12px 20px;
            background: rgba(0, 0, 0, 0.3);
            border: 2px solid rgba(0, 255, 136, 0.3);
            border-radius: 10px;
            color: #fff;
            font-size: 1rem;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .filter-select:hover {
            border-color: #00ff88;
            background: rgba(0, 255, 136, 0.1);
        }
        
        .filter-select:focus {
            outline: none;
            border-color: #00ccff;
            box-shadow: 0 0 20px rgba(0, 255, 136, 0.3);
        }
        
        .filter-select option {
            background: #1a1a1a;
            color: #fff;
        }
        
        .competicao-section {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 40px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            display: none;
        }
        
        .competicao-section.active {
            display: block;
        }
        
        .comp-title { 
            font-size: 1.8rem; 
            margin-bottom: 30px; 
            color: #00ff88;
            text-align: center;
        }
        .tipo-graficos { margin-bottom: 35px; }
        .tipo-title {
            font-size: 1.3rem;
            margin-bottom: 15px;
            color: #00ccff;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .icon { font-size: 1.5rem; }
        .cards-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 20px;
        }
        .card {
            background: rgba(255, 255, 255, 0.08);
            border-radius: 12px;
            padding: 20px;
            transition: all 0.3s ease;
            border: 1px solid transparent;
        }
        .card:hover {
            transform: translateY(-5px);
            border-color: #00ff88;
            box-shadow: 0 10px 30px rgba(0, 255, 136, 0.2);
        }
        .card-title { font-size: 1.1rem; margin-bottom: 10px; font-weight: 600; }
        .card-desc { font-size: 0.9rem; color: #aaa; margin-bottom: 15px; }
        .card-link {
            display: inline-block;
            background: linear-gradient(45deg, #00ff88, #00ccff);
            color: #000;
            padding: 10px 20px;
            border-radius: 8px;
            text-decoration: none;
            font-weight: 600;
            transition: all 0.3s ease;
        }
        .card-link:hover {
            transform: scale(1.05);
            box-shadow: 0 5px 15px rgba(0, 255, 136, 0.4);
        }
        .badge {
            display: inline-block;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 600;
            margin-left: 10px;
        }
        .badge-video { background: #ff6b6b; }
        .badge-ranking { background: #ffd700; color: #000; }
        
        .empty-state {
            text-align: center;
            padding: 60px 20px;
            color: #888;
        }
        
        .empty-state h2 {
            font-size: 2rem;
            margin-bottom: 10px;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Visualizações de Projeções</h1>
        <div class="subtitle">Gráficos interativos baseados nas suas marcações</div>
        
        <div class="filter-section">
            <div class="filter-label">🏆 Competição:</div>
            <select class="filter-select" id="competicaoSelect" onchange="filtrarCompeticao()">
                <option value="">-- Selecione uma competição --</option>
"""
    
    # Adicionar opções do dropdown
    for comp in competicoes:
        if comp.id in comp_times and comp_times[comp.id]:
            html += f'                <option value="comp_{comp.id}">{comp.nome}</option>\n'
    
    html += """
            </select>
        </div>
        
        <div id="emptyState" class="empty-state">
            <h2>👆 Selecione uma competição acima</h2>
            <p>Escolha uma competição para ver os gráficos disponíveis</p>
        </div>
"""
    
    # Gerar seções de cada competição
    for comp in competicoes:
        if comp.id not in comp_times or not comp_times[comp.id]:
            continue
        
        times = comp_times[comp.id]
        
        html += f"""
        <div class="competicao-section" id="comp_{comp.id}">
            <h2 class="comp-title">🏆 {comp.nome}</h2>
            
            <div class="tipo-graficos">
                <h3 class="tipo-title">
                    <span class="icon">📈</span>
                    Gráficos de Ranking
                    <span class="badge badge-ranking">BARRAS</span>
                </h3>
                <div class="cards-grid">
                    <div class="card">
                        <div class="card-title">🏆 Título (80 pts)</div>
                        <div class="card-desc">Ranking de % de atingimento da meta de título</div>
                        <a href="/graficos/ranking_meta/{comp.id}/titulo" class="card-link" target="_blank">Ver Gráfico</a>
                    </div>
                    <div class="card">
                        <div class="card-title">🌎 Libertadores (70 pts)</div>
                        <div class="card-desc">Ranking de % de atingimento da Libertadores</div>
                        <a href="/graficos/ranking_meta/{comp.id}/libertadores" class="card-link" target="_blank">Ver Gráfico</a>
                    </div>
                    <div class="card">
                        <div class="card-title">⚠️ Rebaixamento (45 pts)</div>
                        <div class="card-desc">Ranking de % para evitar o rebaixamento</div>
                        <a href="/graficos/ranking_meta/{comp.id}/rebaixamento" class="card-link" target="_blank">Ver Gráfico</a>
                    </div>
                </div>
            </div>
            
            <div class="tipo-graficos">
                <h3 class="tipo-title">
                    <span class="icon">🎬</span>
                    Vídeos Animados (Bar Chart Race)
                    <span class="badge badge-video">DEMORA 10-30s</span>
                </h3>
                <div class="cards-grid">
                    <div class="card">
                        <div class="card-title">🏆 Corrida do Título</div>
                        <div class="card-desc">Animação da evolução rodada por rodada</div>
                        <a href="/graficos/video_meta/{comp.id}/titulo" class="card-link" target="_blank">Gerar Vídeo</a>
                    </div>
                    <div class="card">
                        <div class="card-title">🌎 Corrida da Libertadores</div>
                        <div class="card-desc">Evolução animada da busca pela Libertadores</div>
                        <a href="/graficos/video_meta/{comp.id}/libertadores" class="card-link" target="_blank">Gerar Vídeo</a>
                    </div>
                    <div class="card">
                        <div class="card-title">⚠️ Fuga do Rebaixamento</div>
                        <div class="card-desc">Animação da luta contra o rebaixamento</div>
                        <a href="/graficos/video_meta/{comp.id}/rebaixamento" class="card-link" target="_blank">Gerar Vídeo</a>
                    </div>
                </div>
            </div>
            
            <div class="tipo-graficos">
                <h3 class="tipo-title">
                    <span class="icon">📊</span>
                    Gráficos por Time (Linhas)
                </h3>
                <div class="cards-grid">
"""
        
        for time in times:
            html += f"""
                    <div class="card">
                        <div class="card-title">{time.nome}</div>
                        <div class="card-desc">Real vs Projeções (Título/Libertadores/Rebaixamento)</div>
                        <a href="/graficos/comparativo/{comp.id}/{time.id}" class="card-link" target="_blank">Ver Trajetória</a>
                    </div>
"""
        
        html += """
                </div>
            </div>
        </div>
"""
    
    html += """
    </div>
    
    <script>
        function filtrarCompeticao() {
            const select = document.getElementById('competicaoSelect');
            const selectedValue = select.value;
            const emptyState = document.getElementById('emptyState');
            
            // Esconder todas as seções
            const sections = document.querySelectorAll('.competicao-section');
            sections.forEach(section => {
                section.classList.remove('active');
            });
            
            if (selectedValue) {
                // Mostrar seção selecionada
                const selectedSection = document.getElementById(selectedValue);
                if (selectedSection) {
                    selectedSection.classList.add('active');
                    emptyState.style.display = 'none';
                }
            } else {
                // Mostrar estado vazio
                emptyState.style.display = 'block';
            }
        }
        
        // Selecionar primeira competição automaticamente
        window.addEventListener('DOMContentLoaded', function() {
            const select = document.getElementById('competicaoSelect');
            if (select.options.length > 1) {
                select.selectedIndex = 1; // Primeira opção real (não o placeholder)
                filtrarCompeticao();
            }
        });
    </script>
</body>
</html>
    """
    
    return html


# ========================================
# GRÁFICO DE BARRAS (RANKING)
# ========================================

@bp_projecoes.route('/ranking_meta/<int:competicao_id>/<meta>')
def ranking_meta(competicao_id, meta):
    """
    Gráfico de barras: Ranking de times por % de atingimento de uma meta
    """
    if meta not in METAS:
        return "Meta inválida! Use: titulo, libertadores ou rebaixamento", 400
    
    competicao = Competicao.query.get_or_404(competicao_id)
    meta_pontos = METAS[meta]
    
    # Buscar times da competição
    jogos = Jogo.query.filter_by(competicao_id=competicao_id).all()
    times_ids = set()
    for jogo in jogos:
        times_ids.add(jogo.time_casa_id)
        times_ids.add(jogo.time_fora_id)
    
    times = Time.query.filter(Time.id.in_(times_ids)).all()
    
    # Calcular % para cada time
    dados = []
    
    for time in times:
        # Pontos projetados TOTAIS
        pontos_proj_total = db.session.query(db.func.sum(Projecao.pontos)).join(
            Jogo, Projecao.jogo_id == Jogo.id
        ).filter(
            Projecao.time_id == time.id,
            Projecao.tipo == meta,
            Jogo.competicao_id == competicao_id
        ).scalar() or 0
        
        # % = (projeção total / meta) × 100
        pct = round((pontos_proj_total / meta_pontos * 100), 1) if meta_pontos > 0 else 0
        
        dados.append({
            'time': time.nome,
            'percentual': pct,
            'pontos_proj_total': pontos_proj_total,
            'meta': meta_pontos,
            'cor': get_cor_time(time.nome)
        })
    
    # Ordenar
    dados = sorted(dados, key=lambda x: x['percentual'], reverse=True)
    dados_json = json.dumps(dados)
    meta_label = METAS_LABELS[meta]
    
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{meta_label} - {competicao.nome}</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            margin: 0;
            padding: 20px;
            background: #1a1a1a;
            color: #fff;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        h1 {{ text-align: center; margin-bottom: 10px; }}
        .subtitle {{ text-align: center; color: #888; margin-bottom: 30px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{meta_label} - {competicao.nome}</h1>
        <div class="subtitle">% de Atingimento da Meta ({meta_pontos} pts) - Baseado nas Suas Projeções</div>
        <div id="chart"></div>
    </div>
    <script>
        var data = {dados_json};
        
        var trace = {{
            type: 'bar',
            orientation: 'h',
            y: data.map(d => d.time),
            x: data.map(d => d.percentual),
            text: data.map(d => d.percentual + '%'),
            textposition: 'outside',
            marker: {{
                color: data.map(d => d.cor || '#808080')
            }},
            hovertemplate: '<b>%{{y}}</b><br>' +
                          'Projeção Total: %{{customdata[0]}} pts<br>' +
                          'Meta: %{{customdata[1]}} pts<br>' +
                          'Atingimento: %{{x}}%<br>' +
                          '<extra></extra>',
            customdata: data.map(d => [d.pontos_proj_total, d.meta])
        }};
        
        var layout = {{
            paper_bgcolor: '#1a1a1a',
            plot_bgcolor: '#1a1a1a',
            font: {{ color: '#fff', size: 14 }},
            margin: {{t: 20, b: 80, l: 150, r: 80}},
            xaxis: {{
                title: '% de Atingimento da Meta',
                gridcolor: '#333',
                range: [0, Math.max(110, Math.max(...data.map(d => d.percentual)) * 1.1)]
            }},
            yaxis: {{ autorange: 'reversed', gridcolor: '#333' }},
            height: Math.max(600, data.length * 50),
            bargap: 0.15,
            shapes: [{{
                type: 'line',
                x0: 100, x1: 100,
                y0: -0.5, y1: data.length - 0.5,
                line: {{ color: '#00ff88', width: 2, dash: 'dash' }}
            }}]
        }};
        
        Plotly.newPlot('chart', [trace], layout, {{displayModeBar: false, responsive: true}});
    </script>
</body>
</html>
    """
    
    return html


# ========================================
# VÍDEO ANIMADO (BAR CHART RACE)
# ========================================

@bp_projecoes.route('/video_meta/<int:competicao_id>/<meta>')
def video_corrida_meta(competicao_id, meta):
    """
    Bar Chart Race: Evolução do % de atingimento rodada por rodada
    """
    from flask import Response
    import pandas as pd
    import tempfile
    import os
    
    if meta not in METAS:
        return "Meta inválida! Use: titulo, libertadores ou rebaixamento", 400
    
    competicao = Competicao.query.get_or_404(competicao_id)
    meta_pontos = METAS[meta]
    
    # Buscar jogos COM resultado
    jogos = Jogo.query.filter_by(competicao_id=competicao_id)\
        .filter(Jogo.gols_casa.isnot(None))\
        .order_by(Jogo.rodada)\
        .all()
    
    if len(jogos) < 2:
        return "Precisa ter pelo menos 2 rodadas finalizadas!", 400
    
    # Times
    times_ids = set()
    for jogo in jogos:
        times_ids.add(jogo.time_casa_id)
        times_ids.add(jogo.time_fora_id)
    
    times = {t.id: t.nome for t in Time.query.filter(Time.id.in_(times_ids)).all()}
    
    # Agrupar por rodada
    rodadas = {}
    for jogo in jogos:
        rodada_num = ''.join(filter(str.isdigit, jogo.rodada))
        if not rodada_num:
            continue
        rodada_num = int(rodada_num)
        
        if rodada_num not in rodadas:
            rodadas[rodada_num] = []
        rodadas[rodada_num].append(jogo)
    
    # Calcular evolução
    dados_evolucao = {}
    
    for rodada_num in sorted(rodadas.keys()):
        rodada_data = {}
        
        for tid in times_ids:
            # Jogos até esta rodada
            jogos_ate_agora_ids = [
                j.id for j in jogos 
                if ((j.time_casa_id == tid or j.time_fora_id == tid) and
                    int(''.join(filter(str.isdigit, j.rodada)) or '0') <= rodada_num)
            ]
            
            # Projeções até agora
            pontos_proj = db.session.query(db.func.sum(Projecao.pontos)).filter(
                Projecao.time_id == tid,
                Projecao.tipo == meta,
                Projecao.jogo_id.in_(jogos_ate_agora_ids)
            ).scalar() or 0
            
            # % = (projeção acumulada / meta) × 100
            percentual = (pontos_proj / meta_pontos * 100) if meta_pontos > 0 else 0
            
            nome_time = times.get(tid, f'Time {tid}')
            rodada_data[nome_time] = round(percentual, 1)
        
        dados_evolucao[f'Rodada {rodada_num}'] = rodada_data
    
    # DataFrame
    df = pd.DataFrame(dados_evolucao).T
    df = df.fillna(0)
    df = df.loc[:, (df != 0).any(axis=0)]
    
    if df.empty:
        return "Nenhum dado de projeção encontrado!", 404
    
    print(f"\n📊 Gerando vídeo com {len(df)} rodadas e {len(df.columns)} times...")
    
    # Criar lista de cores na mesma ordem das colunas do DataFrame
    cores_ordenadas = [get_cor_time(nome) for nome in df.columns]
    
    print(f"🎨 Aplicando cores para {len(cores_ordenadas)} times...")
    
    # Arquivo temporário
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.gif')
    temp_path = temp_file.name
    temp_file.close()
    
    try:
        import bar_chart_race as bcr
        from matplotlib.colors import ListedColormap
        
        # Criar colormap customizado
        cmap_custom = ListedColormap(cores_ordenadas)
        
        bcr.bar_chart_race(
            df=df,
            filename=temp_path,
            orientation='h',
            sort='desc',
            n_bars=10,
            fixed_order=False,
            fixed_max=True,
            steps_per_period=10,
            period_length=1500,
            figsize=(12, 8),
            cmap=cmap_custom,  # Usar colormap customizado
            title=f'{METAS_LABELS[meta]} - % de Atingimento ({meta_pontos} pts)',
            bar_label_size=12,
            tick_label_size=11,
            shared_fontdict={'family': 'sans-serif', 'weight': 'bold'},
            scale='linear',
            writer='pillow',
            bar_kwargs={'alpha': 0.8}
        )
        
        with open(temp_path, 'rb') as f:
            gif_data = f.read()
        
        os.unlink(temp_path)
        
        print(f"✅ Vídeo gerado: {len(gif_data) / 1024:.1f} KB")
        
        return Response(
            gif_data,
            mimetype='image/gif',
            headers={
                'Content-Disposition': f'attachment; filename=corrida_{meta}_{competicao.nome.replace(" ", "_")}.gif'
            }
        )
    
    except ImportError:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        return """
        <h1>⚠️ Biblioteca não instalada!</h1>
        <p>Para gerar vídeos, instale:</p>
        <pre>pip install bar-chart-race</pre>
        <p>Depois reinicie o servidor.</p>
        """, 500
    
    except Exception as e:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        
        print(f"❌ ERRO: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return f"Erro ao gerar vídeo: {str(e)}", 500


# ========================================
# GRÁFICO DE LINHAS (COMPARATIVO POR TIME)
# ========================================

@bp_projecoes.route('/comparativo/<int:competicao_id>/<int:time_id>')
def comparativo_time(competicao_id, time_id):
    """
    Gráfico de linhas: Real vs 3 Projeções (Título/Libertadores/Rebaixamento)
    """
    competicao = Competicao.query.get_or_404(competicao_id)
    time = Time.query.get_or_404(time_id)
    
    # Buscar jogos do time SEM ordenar ainda
    jogos = Jogo.query.filter(
        ((Jogo.time_casa_id == time_id) | (Jogo.time_fora_id == time_id)),
        Jogo.competicao_id == competicao_id
    ).all()
    
    print(f"\n🔍 Total de jogos encontrados: {len(jogos)}")
    
    if not jogos:
        return f"<h1>Nenhum jogo encontrado para {time.nome} em {competicao.nome}</h1>", 404
    
    # Extrair número da rodada e ordenar
    jogos_com_num = []
    for jogo in jogos:
        rodada_str = jogo.rodada
        rodada_num = ''.join(filter(str.isdigit, rodada_str))
        if rodada_num:
            jogos_com_num.append((int(rodada_num), jogo))
    
    # Ordenar por número de rodada
    jogos_com_num.sort(key=lambda x: x[0])
    jogos_ordenados = [jogo for _, jogo in jogos_com_num]
    
    print(f"🔍 Jogos ordenados: {len(jogos_ordenados)}")
    
    # Dados SEPARADOS
    rodadas_proj = []  # Todas as rodadas (para projeções)
    rodadas_real = []  # Apenas rodadas COM resultado
    pontos_reais = []
    pontos_titulo = []
    pontos_libertadores = []
    pontos_rebaixamento = []
    
    pontos_real_acum = 0
    pontos_titulo_acum = 0
    pontos_libertadores_acum = 0
    pontos_rebaixamento_acum = 0
    
    for jogo in jogos_ordenados:
        rodada_num = int(''.join(filter(str.isdigit, jogo.rodada)))
        
        print(f"🔍 Processando jogo ID {jogo.id}, Rodada {jogo.rodada} (num: {rodada_num})")
        
        # Pontos reais - SÓ se tiver resultado
        tem_resultado = jogo.gols_casa is not None and jogo.gols_fora is not None
        
        if tem_resultado:
            eh_casa = jogo.time_casa_id == time_id
            if eh_casa:
                if jogo.gols_casa > jogo.gols_fora:
                    pontos_real_acum += 3
                elif jogo.gols_casa == jogo.gols_fora:
                    pontos_real_acum += 1
            else:
                if jogo.gols_fora > jogo.gols_casa:
                    pontos_real_acum += 3
                elif jogo.gols_casa == jogo.gols_fora:
                    pontos_real_acum += 1
            
            # Adicionar aos dados de real
            rodadas_real.append(rodada_num)
            pontos_reais.append(pontos_real_acum)
        
        # Projeções - SEMPRE, mesmo sem resultado
        for tipo, lista, acum_var in [
            ('titulo', pontos_titulo, 'pontos_titulo_acum'),
            ('libertadores', pontos_libertadores, 'pontos_libertadores_acum'),
            ('rebaixamento', pontos_rebaixamento, 'pontos_rebaixamento_acum')
        ]:
            proj = Projecao.query.filter_by(
                jogo_id=jogo.id,
                time_id=time_id,
                tipo=tipo
            ).first()
            
            if proj:
                if tipo == 'titulo':
                    pontos_titulo_acum += proj.pontos
                elif tipo == 'libertadores':
                    pontos_libertadores_acum += proj.pontos
                else:
                    pontos_rebaixamento_acum += proj.pontos
                print(f"   ✅ Projeção {tipo}: {proj.pontos} pts (jogo {jogo.id})")
            else:
                print(f"   ❌ SEM projeção {tipo} para jogo {jogo.id}")
        
        # Adicionar às projeções (TODAS as rodadas)
        rodadas_proj.append(rodada_num)
        pontos_titulo.append(pontos_titulo_acum)
        pontos_libertadores.append(pontos_libertadores_acum)
        pontos_rebaixamento.append(pontos_rebaixamento_acum)
    
    print(f"📊 DADOS FINAIS:")
    print(f"   Rodadas Real: {rodadas_real} (apenas {len(rodadas_real)} com resultado)")
    print(f"   Rodadas Proj: {rodadas_proj} (todas as {len(rodadas_proj)} rodadas)")
    print(f"   Reais: {pontos_reais}")
    print(f"   Título: {pontos_titulo}")
    print(f"   Libertadores: {pontos_libertadores}")
    print(f"   Rebaixamento: {pontos_rebaixamento}")
    
    dados = {
        'rodadas_real': rodadas_real,
        'rodadas_proj': rodadas_proj,
        'reais': pontos_reais,
        'titulo': pontos_titulo,
        'libertadores': pontos_libertadores,
        'rebaixamento': pontos_rebaixamento
    }
    
    dados_json = json.dumps(dados)
    cor_time = get_cor_time(time.nome)
    
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{time.nome} - {competicao.nome}</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            margin: 0;
            padding: 20px;
            background: #1a1a1a;
            color: #fff;
        }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        h1 {{ text-align: center; margin-bottom: 10px; }}
        .subtitle {{ text-align: center; color: #888; margin-bottom: 30px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{time.nome} - {competicao.nome}</h1>
        <div class="subtitle">Real (até última rodada) vs Projeções (futuro)</div>
        <div id="chart"></div>
    </div>
    <script>
        var dados = {dados_json};
        
        var traces = [
            {{
                name: 'Pontos Reais',
                x: dados.rodadas_real,
                y: dados.reais,
                mode: 'lines+markers',
                line: {{ color: '{cor_time}', width: 4 }},
                marker: {{ size: 8, color: '{cor_time}' }}
            }},
            {{
                name: '🏆 Projeção Título (80 pts)',
                x: dados.rodadas_proj,
                y: dados.titulo,
                mode: 'lines+markers',
                line: {{ color: '#FFD700', width: 3, dash: 'dash' }},
                marker: {{ size: 6, color: '#FFD700' }}
            }},
            {{
                name: '🌎 Projeção Libertadores (70 pts)',
                x: dados.rodadas_proj,
                y: dados.libertadores,
                mode: 'lines+markers',
                line: {{ color: '#00ff88', width: 3, dash: 'dash' }},
                marker: {{ size: 6, color: '#00ff88' }}
            }},
            {{
                name: '⚠️ Projeção Rebaixamento (45 pts)',
                x: dados.rodadas_proj,
                y: dados.rebaixamento,
                mode: 'lines+markers',
                line: {{ color: '#ff3333', width: 3, dash: 'dash' }},
                marker: {{ size: 6, color: '#ff3333' }}
            }}
        ];
        
        var layout = {{
            paper_bgcolor: '#1a1a1a',
            plot_bgcolor: '#1a1a1a',
            font: {{ color: '#fff', size: 14 }},
            xaxis: {{ 
                title: 'Rodada', 
                gridcolor: '#333',
                range: [0, Math.max(...dados.rodadas_proj) + 1]
            }},
            yaxis: {{ title: 'Pontos Acumulados', gridcolor: '#333' }},
            hovermode: 'x unified',
            height: 650,
            showlegend: true,
            legend: {{ x: 0.02, y: 0.98, bgcolor: 'rgba(0,0,0,0.5)' }},
            shapes: [
                {{ type: 'line', x0: 0, x1: Math.max(...dados.rodadas_proj), y0: 80, y1: 80,
                   line: {{ color: '#FFD700', width: 1, dash: 'dot' }} }},
                {{ type: 'line', x0: 0, x1: Math.max(...dados.rodadas_proj), y0: 70, y1: 70,
                   line: {{ color: '#00ff88', width: 1, dash: 'dot' }} }},
                {{ type: 'line', x0: 0, x1: Math.max(...dados.rodadas_proj), y0: 45, y1: 45,
                   line: {{ color: '#ff3333', width: 1, dash: 'dot' }} }}
            ]
        }};
        
        Plotly.newPlot('chart', traces, layout, {{displayModeBar: false, responsive: true}});
    </script>
</body>
</html>
    """
    
    return html
