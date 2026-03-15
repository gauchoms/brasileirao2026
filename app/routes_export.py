"""
Rotas de exportação de dados para geração de conteúdo
Bar chart races, comparações, estatísticas
"""

from flask import Blueprint, jsonify, Response
from app.models import Time, Jogo, Competicao
from app import db
import csv
import io
from datetime import datetime

bp_export = Blueprint('export', __name__, url_prefix='/export')

@bp_export.route('/evolucao_tabela/<int:competicao_id>')
def evolucao_tabela(competicao_id):
    """
    Exporta evolução da tabela rodada por rodada
    Formato ideal para Bar Chart Race (Flourish)
    
    Retorna CSV com colunas:
    rodada, time, pontos, posicao, jogos, vitorias, empates, derrotas, gols_pro, gols_contra, saldo
    """
    competicao = Competicao.query.get_or_404(competicao_id)
    
    # Buscar todos os jogos da competição
    jogos = Jogo.query.filter_by(
        competicao_id=competicao_id
    ).order_by(Jogo.data).all()
    
    # Estrutura: {rodada: {time_id: stats}}
    evolucao = {}
    times_stats = {}
    
    for jogo in jogos:
        if jogo.gols_casa is None:  # Jogo não foi realizado
            continue
        
        # Extrair número da rodada
        rodada_str = jogo.rodada.replace('Regular Season - ', '').replace('Rodada ', '')
        try:
            rodada = int(rodada_str)
        except:
            continue
        
        # Inicializar rodada se não existe
        if rodada not in evolucao:
            # Copiar stats da rodada anterior
            if rodada > 1 and (rodada - 1) in evolucao:
                evolucao[rodada] = {k: v.copy() for k, v in evolucao[rodada - 1].items()}
            else:
                evolucao[rodada] = {}
        
        # Inicializar times se não existem
        for time_id in [jogo.time_casa_id, jogo.time_fora_id]:
            if time_id not in evolucao[rodada]:
                evolucao[rodada][time_id] = {
                    'pontos': 0,
                    'jogos': 0,
                    'vitorias': 0,
                    'empates': 0,
                    'derrotas': 0,
                    'gols_pro': 0,
                    'gols_contra': 0,
                    'saldo': 0
                }
        
        # Atualizar estatísticas
        stats_casa = evolucao[rodada][jogo.time_casa_id]
        stats_fora = evolucao[rodada][jogo.time_fora_id]
        
        stats_casa['jogos'] += 1
        stats_fora['jogos'] += 1
        
        stats_casa['gols_pro'] += jogo.gols_casa
        stats_casa['gols_contra'] += jogo.gols_fora
        stats_fora['gols_pro'] += jogo.gols_fora
        stats_fora['gols_contra'] += jogo.gols_casa
        
        if jogo.gols_casa > jogo.gols_fora:
            stats_casa['vitorias'] += 1
            stats_casa['pontos'] += 3
            stats_fora['derrotas'] += 1
        elif jogo.gols_fora > jogo.gols_casa:
            stats_fora['vitorias'] += 1
            stats_fora['pontos'] += 3
            stats_casa['derrotas'] += 1
        else:
            stats_casa['empates'] += 1
            stats_fora['empates'] += 1
            stats_casa['pontos'] += 1
            stats_fora['pontos'] += 1
        
        stats_casa['saldo'] = stats_casa['gols_pro'] - stats_casa['gols_contra']
        stats_fora['saldo'] = stats_fora['gols_pro'] - stats_fora['gols_contra']
    
    # Gerar CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        'rodada', 'time', 'pontos', 'posicao', 'jogos', 
        'vitorias', 'empates', 'derrotas', 
        'gols_pro', 'gols_contra', 'saldo'
    ])
    
    # Dados
    for rodada in sorted(evolucao.keys()):
        # Ordenar times por pontos, saldo, gols_pro
        times_ordenados = sorted(
            evolucao[rodada].items(),
            key=lambda x: (x[1]['pontos'], x[1]['saldo'], x[1]['gols_pro']),
            reverse=True
        )
        
        for posicao, (time_id, stats) in enumerate(times_ordenados, 1):
            time = Time.query.get(time_id)
            if not time:
                continue
            
            writer.writerow([
                rodada,
                time.nome,
                stats['pontos'],
                posicao,
                stats['jogos'],
                stats['vitorias'],
                stats['empates'],
                stats['derrotas'],
                stats['gols_pro'],
                stats['gols_contra'],
                stats['saldo']
            ])
    
    # Retornar CSV
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename=evolucao_{competicao.nome.replace(" ", "_")}.csv'
        }
    )


@bp_export.route('/projecoes/<int:competicao_id>')
def projecoes_competicao(competicao_id):
    """
    Exporta projeções de pontos com 3 cenários + % de atingimento de metas
    CALCULA em tempo real baseado nos jogos já realizados
    """
    competicao = Competicao.query.get_or_404(competicao_id)
    
    # Buscar todos os jogos da competição
    jogos = Jogo.query.filter_by(competicao_id=competicao_id).all()
    
    # Calcular pontos atuais e jogos restantes por time
    tabela = {}
    jogos_por_time = {}
    
    for jogo in jogos:
        # Contar total de jogos por time
        for time_id in [jogo.time_casa_id, jogo.time_fora_id]:
            if time_id not in jogos_por_time:
                jogos_por_time[time_id] = {'total': 0, 'realizados': 0}
            jogos_por_time[time_id]['total'] += 1
        
        # Processar apenas jogos finalizados
        if jogo.gols_casa is None:
            continue
        
        # Inicializar times
        for time_id in [jogo.time_casa_id, jogo.time_fora_id]:
            if time_id not in tabela:
                tabela[time_id] = {
                    'pontos': 0,
                    'jogos': 0,
                    'vitorias': 0,
                    'saldo': 0,
                    'gols_pro': 0
                }
            jogos_por_time[time_id]['realizados'] += 1
        
        # Calcular pontos
        if jogo.gols_casa > jogo.gols_fora:
            tabela[jogo.time_casa_id]['pontos'] += 3
            tabela[jogo.time_casa_id]['vitorias'] += 1
        elif jogo.gols_fora > jogo.gols_casa:
            tabela[jogo.time_fora_id]['pontos'] += 3
            tabela[jogo.time_fora_id]['vitorias'] += 1
        else:
            tabela[jogo.time_casa_id]['pontos'] += 1
            tabela[jogo.time_fora_id]['pontos'] += 1
        
        tabela[jogo.time_casa_id]['jogos'] += 1
        tabela[jogo.time_fora_id]['jogos'] += 1
        tabela[jogo.time_casa_id]['gols_pro'] += jogo.gols_casa
        tabela[jogo.time_fora_id]['gols_pro'] += jogo.gols_fora
        tabela[jogo.time_casa_id]['saldo'] += (jogo.gols_casa - jogo.gols_fora)
        tabela[jogo.time_fora_id]['saldo'] += (jogo.gols_fora - jogo.gols_casa)
    
    # Metas
    METAS = {
        'titulo': 80,
        'libertadores': 70,
        'rebaixamento': 45
    }
    
    # Gerar CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        'time', 'posicao', 'pontos_atuais', 'jogos_realizados', 'jogos_restantes',
        'proj_otimista', 'proj_realista', 'proj_pessimista',
        'meta_titulo', 'perc_titulo_otimista', 'perc_titulo_realista', 'perc_titulo_pessimista',
        'meta_libertadores', 'perc_liberta_otimista', 'perc_liberta_realista', 'perc_liberta_pessimista',
        'meta_rebaixamento', 'perc_salvo_otimista', 'perc_salvo_realista', 'perc_salvo_pessimista',
        'distancia_lider', 'distancia_z4'
    ])
    
    # Ordenar tabela
    times_ordenados = sorted(
        tabela.items(),
        key=lambda x: (x[1]['pontos'], x[1]['vitorias'], x[1]['saldo'], x[1]['gols_pro']),
        reverse=True
    )
    
    # Pegar pontos do líder e do 17º
    pontos_lider = times_ordenados[0][1]['pontos'] if times_ordenados else 0
    pontos_z4 = times_ordenados[16][1]['pontos'] if len(times_ordenados) > 16 else 0
    
    # Dados
    for posicao, (time_id, stats) in enumerate(times_ordenados, 1):
        time = Time.query.get(time_id)
        if not time:
            continue
        
        jogos_realizados = jogos_por_time[time_id]['realizados']
        jogos_restantes = jogos_por_time[time_id]['total'] - jogos_realizados
        pontos_atuais = stats['pontos']
        
        # Calcular projeções baseado na média atual
        if jogos_realizados > 0:
            media_pontos = pontos_atuais / jogos_realizados
            
            # Otimista: ganhar todos os jogos restantes
            proj_otimista = pontos_atuais + (jogos_restantes * 3)
            
            # Realista: manter a média atual
            proj_realista = pontos_atuais + (jogos_restantes * media_pontos)
            
            # Pessimista: metade da média atual
            proj_pessimista = pontos_atuais + (jogos_restantes * media_pontos * 0.5)
        else:
            proj_otimista = jogos_restantes * 3
            proj_realista = jogos_restantes * 1.5
            proj_pessimista = jogos_restantes * 0.5
        
        # Calcular % de atingimento das metas
        def calcular_perc(projecao, meta):
            return round((projecao / meta * 100), 1) if meta > 0 else 0
        
        perc_titulo_otimista = calcular_perc(proj_otimista, METAS['titulo'])
        perc_titulo_realista = calcular_perc(proj_realista, METAS['titulo'])
        perc_titulo_pessimista = calcular_perc(proj_pessimista, METAS['titulo'])
        
        perc_liberta_otimista = calcular_perc(proj_otimista, METAS['libertadores'])
        perc_liberta_realista = calcular_perc(proj_realista, METAS['libertadores'])
        perc_liberta_pessimista = calcular_perc(proj_pessimista, METAS['libertadores'])
        
        # Para rebaixamento: 100% = está seguro (acima de 45)
        perc_salvo_otimista = min(100, calcular_perc(proj_otimista, METAS['rebaixamento']))
        perc_salvo_realista = min(100, calcular_perc(proj_realista, METAS['rebaixamento']))
        perc_salvo_pessimista = min(100, calcular_perc(proj_pessimista, METAS['rebaixamento']))
        
        # Distâncias
        distancia_lider = pontos_lider - pontos_atuais
        distancia_z4 = pontos_atuais - pontos_z4
        
        writer.writerow([
            time.nome,
            posicao,
            pontos_atuais,
            jogos_realizados,
            jogos_restantes,
            round(proj_otimista, 1),
            round(proj_realista, 1),
            round(proj_pessimista, 1),
            METAS['titulo'],
            perc_titulo_otimista,
            perc_titulo_realista,
            perc_titulo_pessimista,
            METAS['libertadores'],
            perc_liberta_otimista,
            perc_liberta_realista,
            perc_liberta_pessimista,
            METAS['rebaixamento'],
            perc_salvo_otimista,
            perc_salvo_realista,
            perc_salvo_pessimista,
            distancia_lider,
            distancia_z4
        ])
    
    # Retornar CSV
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename=projecoes_{competicao.nome.replace(" ", "_")}.csv'
        }
    )


@bp_export.route('/bolao_ranking/<int:bolao_id>')
def bolao_ranking_evolucao(bolao_id):
    """
    Exporta evolução do ranking de um bolão jogo por jogo
    Perfeito para Bar Chart Race dos participantes!
    
    Formato CSV:
    jogo, participante, pontos_acumulados, posicao, avatar
    """
    from app.models import Bolao, Palpite, Usuario, Jogo
    
    bolao = Bolao.query.get_or_404(bolao_id)
    
    # Buscar todos os palpites de jogos finalizados, ordenados por data
    palpites = Palpite.query.filter_by(bolao_id=bolao_id)\
        .join(Jogo)\
        .filter(Jogo.gols_casa.isnot(None))\
        .order_by(Jogo.data)\
        .all()
    
    if not palpites:
        # Retornar CSV vazio se não houver dados
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['jogo', 'participante', 'pontos_acumulados', 'posicao', 'avatar'])
        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename=ranking_{bolao.nome.replace(" ", "_")}.csv'
            }
        )
    
    # Estrutura: {nr_jogo: {usuario_id: pontos}}
    evolucao = {}
    usuarios_nomes = {}
    jogos_processados = set()
    contador_jogo = 0
    
    for palpite in palpites:
        jogo = palpite.jogo
        
        # Se esse jogo ainda não foi processado, incrementa contador
        if jogo.id not in jogos_processados:
            contador_jogo += 1
            jogos_processados.add(jogo.id)
            
            # Copiar pontos do jogo anterior (deep copy!)
            if contador_jogo > 1 and (contador_jogo - 1) in evolucao:
                evolucao[contador_jogo] = {k: v for k, v in evolucao[contador_jogo - 1].items()}
            else:
                evolucao[contador_jogo] = {}
        
        # Guardar nome do usuário
        if palpite.usuario_id not in usuarios_nomes:
            usuario = Usuario.query.get(palpite.usuario_id)
            if usuario:
                usuarios_nomes[palpite.usuario_id] = usuario.username
        
        # Garantir que usuário existe antes de adicionar pontos
        if palpite.usuario_id not in evolucao[contador_jogo]:
            evolucao[contador_jogo][palpite.usuario_id] = 0
        
        # Adicionar pontos deste jogo
        evolucao[contador_jogo][palpite.usuario_id] += palpite.pontos_obtidos
    
    # Gerar CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        'jogo', 'participante', 'pontos_acumulados', 'posicao', 'avatar'
    ])
    
    # Dados
    for nr_jogo in sorted(evolucao.keys()):
        # Ordenar participantes por pontos
        participantes_ordenados = sorted(
            evolucao[nr_jogo].items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        for posicao, (usuario_id, pontos) in enumerate(participantes_ordenados, 1):
            # Buscar dados do usuário
            usuario = Usuario.query.get(usuario_id)
            
            if not usuario:
                continue
            
            # Determinar avatar para visualização
            if usuario.avatar_tipo == 'sugerido' and usuario.avatar_sugerido_id:
                avatares = ['⚽', '🏆', '👟', '🥅', '🔥', '⭐', '⚡', '💪', '🎯', '👊', '🚀', '💎']
                avatar = avatares[usuario.avatar_sugerido_id - 1] if usuario.avatar_sugerido_id <= len(avatares) else '👤'
            else:
                avatar = '👤'
            
            writer.writerow([
                nr_jogo,
                usuario.username,
                pontos,
                posicao,
                avatar
            ])
    
    # Retornar CSV
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename=ranking_{bolao.nome.replace(" ", "_")}.csv'
        }
    )

@bp_export.route('/bolao_video/<int:bolao_id>')
def bolao_video_ranking(bolao_id):
    """
    Gera vídeo/GIF da evolução do ranking do bolão
    Bar Chart Race automático!
    """
    import pandas as pd
    import bar_chart_race as bcr
    import os
    import tempfile
    from flask import flash, redirect, url_for
    from app.models import Bolao, Palpite, Usuario
    
    bolao = Bolao.query.get_or_404(bolao_id)

    
    # Buscar todos os palpites do bolão
    palpites = Palpite.query.filter_by(bolao_id=bolao_id).all()
    
    print(f"🔍 DEBUG: Total de palpites: {len(palpites)}")  # DEBUG

    # Verificar se tem palpites
    if not palpites:
        flash('⚠️ Este bolão ainda não tem palpites suficientes para gerar um vídeo!', 'warning')
        return redirect(url_for('main.bolao_detalhes', bolao_id=bolao_id))
    
    # Estrutura: {rodada: {usuario: pontos}}
    evolucao = {}
    usuarios_nomes = {}
    
    for palpite in palpites:
        jogo = palpite.jogo
        
        # Só jogos finalizados
        if jogo.gols_casa is None:
            continue
        
        # Extrair rodada
        rodada_str = jogo.rodada.replace('Regular Season - ', '').replace('Rodada ', '')
        try:
            rodada = int(rodada_str)
        except:
            continue
        
        # Inicializar rodada
        if rodada not in evolucao:
            if rodada > 1 and (rodada - 1) in evolucao:
                evolucao[rodada] = evolucao[rodada - 1].copy()
            else:
                evolucao[rodada] = {}
        
        # Guardar nome do usuário
        if palpite.usuario_id not in usuarios_nomes:
            usuario = Usuario.query.get(palpite.usuario_id)
            if usuario:
                usuarios_nomes[palpite.usuario_id] = usuario.username
        
        # Inicializar participante
        if palpite.usuario_id not in evolucao[rodada]:
            evolucao[rodada][palpite.usuario_id] = 0
        
        # Adicionar pontos
        evolucao[rodada][palpite.usuario_id] += palpite.pontos_obtidos
    
        
    print(f"🔍 DEBUG: Rodadas com dados: {len(evolucao)}")  # DEBUG
    print(f"🔍 DEBUG: Participantes: {len(usuarios_nomes)}")  # DEBUG
    
    # Validações
    if not evolucao:
    
        print("❌ DEBUG: Sem evolução (nenhum jogo finalizado)!")  # DEBUG
        flash('⚠️ Nenhum jogo foi finalizado ainda! Aguarde os primeiros resultados.', 'warning')
        return redirect(url_for('main.bolao_detalhes', bolao_id=bolao_id))
    
    
    if len(evolucao) < 2:
        print(f"❌ DEBUG: Poucas rodadas ({len(evolucao)} < 2)!")  # DEBUG
        flash('⚠️ É preciso ter pelo menos 2 rodadas finalizadas para gerar o vídeo!', 'warning')
        return redirect(url_for('main.bolao_detalhes', bolao_id=bolao_id))
    
    if len(usuarios_nomes) < 2:
        print(f"❌ DEBUG: Poucos participantes ({len(usuarios_nomes)} < 2)!")  # DEBUG
        flash('⚠️ É preciso ter pelo menos 2 participantes com palpites para gerar o vídeo!', 'warning')
        return redirect(url_for('main.bolao_detalhes', bolao_id=bolao_id))
    

    # Converter para DataFrame
    df_data = {}

    # Verificar se é bolão de campeonato ou time
    eh_campeonato = bolao.competicao_id is not None

    if eh_campeonato:
        # Usar número da rodada
        for rodada in sorted(evolucao.keys()):
            rodada_data = {}
            for usuario_id, pontos in evolucao[rodada].items():
                nome = usuarios_nomes.get(usuario_id, f'Usuário {usuario_id}')
                rodada_data[nome] = pontos
            df_data[f'Rodada {rodada}'] = rodada_data
    else:
        # Usar contador sequencial de jogos
        contador = 0
        for rodada in sorted(evolucao.keys()):
            contador += 1
            rodada_data = {}
            for usuario_id, pontos in evolucao[rodada].items():
                nome = usuarios_nomes.get(usuario_id, f'Usuário {usuario_id}')
                rodada_data[nome] = pontos
            df_data[f'Jogo {contador}'] = rodada_data

    df = pd.DataFrame(df_data).T

    df = df.fillna(0)
    
    # Criar arquivo temporário
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.gif')
    temp_path = temp_file.name
    temp_file.close()
    
    try:
        # Gerar Bar Chart Race
        bcr.bar_chart_race(
            df=df,
            filename=temp_path,
            orientation='h',
            sort='asc',
            n_bars=min(10, len(usuarios_nomes)),  # Top 10 ou menos se tiver menos participantes
            fixed_order=False,
            fixed_max=True,
            steps_per_period=10,
            period_length=3500,
            figsize=(8, 5),
            cmap='dark24',
            title=f'🏆 {bolao.nome} - Evolução do Ranking',
            bar_label_size=10,
            tick_label_size=9,
            shared_fontdict={'family': 'sans-serif', 'weight': 'bold'},
            scale='linear',
            writer='pillow',
            bar_kwargs={'alpha': 0.8},
            filter_column_colors=True
        )
        
        # Ler arquivo gerado
        with open(temp_path, 'rb') as f:
            gif_data = f.read()
        
        # Limpar arquivo temporário
        os.unlink(temp_path)
        
        # Retornar GIF
        return Response(
            gif_data,
            mimetype='image/gif',
            headers={
                'Content-Disposition': f'attachment; filename=ranking_{bolao.nome.replace(" ", "_")}.gif'
            }
        )
    
    except Exception as e:
        # Limpar em caso de erro
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        
        # ADICIONAR PRINT DO ERRO
        print(f"❌ ERRO ao gerar vídeo: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        
        flash(f'❌ Erro ao gerar vídeo: {str(e)}', 'danger')
        return redirect(url_for('main.bolao_detalhes', bolao_id=bolao_id))