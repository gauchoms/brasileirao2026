# app/scheduler.py
# Atualização automática de resultados usando APScheduler
# Compatível com Gunicorn (single worker) no Render

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timedelta
import pytz
import logging
import os

logger = logging.getLogger(__name__)
BRASILIA = pytz.timezone('America/Sao_Paulo')

# Instância global para evitar duplicatas
_scheduler = None


def atualizar_resultados_job(app):
    """
    Atualiza placares e recalcula pontos de todos os bolões.
    Mesma lógica da rota /atualizar_resultados.
    """
    with app.app_context():
        try:
            from app.models import Jogo, Palpite, Bolao, ParticipanteBolao, Competicao, RegraPontuacao
            from app.routes import calcular_pontos_palpite
            from app.api import get_resultados_brasileirao
            from app import db

            print(f"[SCHEDULER] Rodando atualização: {datetime.now(BRASILIA).strftime('%d/%m/%Y %H:%M')}")

            competicoes = Competicao.query.all()
            novos = 0
            palpites_calculados = 0

            for comp in competicoes:
                try:
                    data = get_resultados_brasileirao(league_id=comp.api_league_id, season=comp.ano)
                    jogos = data.get('response', [])

                    for fixture in jogos:
                        api_id = fixture['fixture']['id']
                        # Usa placar do tempo normal (90min) — decisão do bolão
                        _sc = fixture.get('score', {}).get('fulltime', {})
                        gols_casa = _sc.get('home') if _sc.get('home') is not None else fixture['goals']['home']
                        gols_fora = _sc.get('away') if _sc.get('away') is not None else fixture['goals']['away']
                        status_api = fixture['fixture']['status']['short']

                        jogo = Jogo.query.filter_by(api_id=api_id).first()

                        if jogo:
                            # Atualiza status sempre (captura PST, remarcações, etc)
                            jogo.status = status_api
                            # Se foi remarcado (saiu de PST), atualiza a data
                            nova_data = fixture['fixture'].get('date')
                            if nova_data and status_api != 'PST':
                                jogo.data = nova_data

                        if jogo and gols_casa is not None and gols_fora is not None:
                            tinha_placar = jogo.gols_casa is not None and jogo.gols_fora is not None

                            if not tinha_placar:
                                jogo.gols_casa = gols_casa
                                jogo.gols_fora = gols_fora
                                novos += 1

                                palpites = Palpite.query.filter_by(jogo_id=jogo.id).all()
                                for palpite in palpites:
                                    bolao = Bolao.query.get(palpite.bolao_id)
                                    regra = RegraPontuacao.query.get(bolao.regra_pontuacao_id)
                                    pontos = calcular_pontos_palpite(palpite, jogo, regra)
                                    palpite.pontos_obtidos = pontos
                                    palpites_calculados += 1

                                    participante = ParticipanteBolao.query.filter_by(
                                        bolao_id=palpite.bolao_id,
                                        usuario_id=palpite.usuario_id
                                    ).first()
                                    if participante:
                                        total = db.session.query(db.func.sum(Palpite.pontos_obtidos)).filter_by(
                                            bolao_id=palpite.bolao_id,
                                            usuario_id=palpite.usuario_id
                                        ).scalar() or 0
                                        participante.pontos_totais = total

                            elif jogo.gols_casa != gols_casa or jogo.gols_fora != gols_fora:
                                jogo.gols_casa = gols_casa
                                jogo.gols_fora = gols_fora

                except Exception as e:
                    print(f"[SCHEDULER] Erro na competição {comp.nome}: {e}")
                    continue

            db.session.commit()
            print(f"[SCHEDULER] Concluído: {novos} novos resultados, {palpites_calculados} palpites calculados")

        except Exception as e:
            print(f"[SCHEDULER] Erro geral: {e}")


def verificar_jogos_proximos(app):
    """
    Roda a cada 5 minutos.
    Dispara atualização se houver jogo começando nos próximos 5 min
    ou que deveria ter terminado (início + 105 min) há menos de 15 min.
    """
    with app.app_context():
        try:
            from app.models import Jogo

            agora = datetime.now(BRASILIA)
            em_5min = agora + timedelta(minutes=5)
            ha_120min = agora - timedelta(minutes=120)
            ha_105min = agora - timedelta(minutes=105)

            agora_str = agora.strftime('%Y-%m-%dT%H:%M')
            em_5min_str = em_5min.strftime('%Y-%m-%dT%H:%M')
            ha_120min_str = ha_120min.strftime('%Y-%m-%dT%H:%M')
            ha_105min_str = ha_105min.strftime('%Y-%m-%dT%H:%M')

            jogos_proximos = Jogo.query.filter(
                Jogo.data >= agora_str,
                Jogo.data <= em_5min_str,
                Jogo.gols_casa == None
            ).count()

            jogos_terminando = Jogo.query.filter(
                Jogo.data >= ha_120min_str,
                Jogo.data <= ha_105min_str,
                Jogo.gols_casa == None
            ).count()

            if jogos_proximos > 0 or jogos_terminando > 0:
                print(f"[SCHEDULER] Jogo detectado (próximos={jogos_proximos}, terminando={jogos_terminando}), atualizando...")
                atualizar_resultados_job(app)

        except Exception as e:
            print(f"[SCHEDULER] Erro ao verificar jogos: {e}")


def sincronizar_jogos_job(app):
    """
    Roda de hora em hora.
    Importa jogos NOVOS que ainda não estão no banco para todos os bolões ativos.
    Mesma lógica do botão 'Atualizar Jogos' no detalhe do bolão.
    """
    with app.app_context():
        try:
            from app.models import Bolao, Jogo, Time
            from app.api import get_jogos_competicao, processar_jogos, importar_jogos_time_ano
            from app import db

            print(f"[SCHEDULER] Sincronizando jogos: {datetime.now(BRASILIA).strftime('%d/%m/%Y %H:%M')}")

            boloes = Bolao.query.filter_by(status='ativo').all()
            total_novos = 0

            for bolao in boloes:
                try:
                    if bolao.tipo_bolao == 'time_ano_completo':
                        time = Time.query.get(bolao.time_especifico_id)
                        if time and time.api_id:
                            resultado = importar_jogos_time_ano(time.api_id, bolao.ano)
                            total_novos += resultado.get('total_jogos', 0)

                    elif bolao.tipo_bolao in ['campeonato_completo', 'time_campeonato']:
                        if bolao.competicao and bolao.competicao.api_league_id:
                            jogos_data = get_jogos_competicao(bolao.competicao.api_league_id, bolao.competicao.ano)
                            jogos = processar_jogos(jogos_data)

                            times_cadastrados = {}

                            for jogo in jogos:
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
                                total_novos += 1

                            db.session.commit()

                except Exception as e:
                    print(f"[SCHEDULER] Erro ao sincronizar bolão {bolao.id}: {e}")
                    continue

            print(f"[SCHEDULER] Sincronização concluída: {total_novos} jogos novos ✅")

        except Exception as e:
            print(f"[SCHEDULER] Erro geral na sincronização: {e}")




def enviar_alertas_palpites_job(app):
    """
    Roda a cada 30 minutos.
    Para cada bolão com envia_alertas=True, verifica jogos nas próximas
    24h e 1h e envia email para participantes que ainda não palpitaram.
    """
    with app.app_context():
        try:
            from app.models import Bolao, Jogo, Palpite, ParticipanteBolao
            from app.email import email_alerta_palpite
            from app import db
            from datetime import datetime, timedelta

            agora = datetime.utcnow()
            janela_24h_inicio = agora + timedelta(hours=23)
            janela_24h_fim    = agora + timedelta(hours=25)
            janela_1h_inicio  = agora + timedelta(minutes=30)
            janela_1h_fim     = agora + timedelta(hours=2)

            enviados_24h = 0
            enviados_1h  = 0

            boloes = Bolao.query.filter_by(envia_alertas=True, status='ativo').all()

            for bolao in boloes:
                # Jogos do bolão com alerta pendente
                jogos = Jogo.query.join(
                    Bolao, Bolao.competicao_id == Jogo.competicao_id
                ).filter(
                    Bolao.id == bolao.id,
                    Jogo.gols_casa == None,
                    Jogo.data != None
                ).all()

                for jogo in jogos:
                    try:
                        data_str = jogo.data.replace('+00:00','').replace('Z','').split('+')[0][:19]
                        try:
                            data_utc = datetime.strptime(data_str, '%Y-%m-%dT%H:%M:%S')
                        except:
                            data_utc = datetime.strptime(data_str[:16], '%Y-%m-%dT%H:%M')

                        eh_24h = janela_24h_inicio <= data_utc <= janela_24h_fim
                        eh_1h  = janela_1h_inicio  <= data_utc <= janela_1h_fim

                        if not eh_24h and not eh_1h:
                            continue

                        # Participantes que ainda não palpitaram
                        participantes = ParticipanteBolao.query.filter_by(bolao_id=bolao.id).all()

                        for part in participantes:
                            ja_palpitou = Palpite.query.filter_by(
                                bolao_id=bolao.id,
                                usuario_id=part.usuario_id,
                                jogo_id=jogo.id
                            ).first()

                            if ja_palpitou:
                                continue

                            if eh_24h and not jogo.alerta_24h_enviado:
                                email_alerta_palpite(part.usuario, jogo, bolao, 24)
                                enviados_24h += 1

                            elif eh_1h and not jogo.alerta_1h_enviado:
                                email_alerta_palpite(part.usuario, jogo, bolao, 1)
                                enviados_1h += 1

                        # Marcar como enviado (mesmo que alguns não tenham email)
                        if eh_24h and not jogo.alerta_24h_enviado:
                            jogo.alerta_24h_enviado = True
                        if eh_1h and not jogo.alerta_1h_enviado:
                            jogo.alerta_1h_enviado = True

                    except Exception as e:
                        print(f"[ALERTAS] Erro jogo {jogo.id}: {e}")
                        continue

            db.session.commit()
            if enviados_24h or enviados_1h:
                print(f"[ALERTAS] {enviados_24h} alertas 24h + {enviados_1h} alertas 1h enviados ✅")

        except Exception as e:
            print(f"[ALERTAS] Erro geral: {e}")

def iniciar_scheduler(app):
    """
    Inicia o scheduler com proteção contra duplicatas.
    Seguro para Gunicorn no Render com WEB_CONCURRENCY=1.
    """
    global _scheduler

    # Evita iniciar múltiplas vezes
    if _scheduler is not None and _scheduler.running:
        print("[SCHEDULER] Já está rodando, ignorando.")
        return _scheduler

    _scheduler = BackgroundScheduler(timezone=BRASILIA)

    # Job A+B: a cada 5 minutos, verifica jogos próximos ou terminando
    _scheduler.add_job(
        func=verificar_jogos_proximos,
        trigger=IntervalTrigger(minutes=5),
        args=[app],
        id='verificar_jogos',
        name='Verificar jogos próximos/terminando',
        replace_existing=True
    )

    # Job C: de hora em hora, independente dos jogos
    _scheduler.add_job(
        func=atualizar_resultados_job,
        trigger=IntervalTrigger(hours=1),
        args=[app],
        id='atualizar_hora',
        name='Atualização horária',
        replace_existing=True
    )

    # Job D: de hora em hora, importa jogos novos para todos os bolões ativos
    _scheduler.add_job(
        func=sincronizar_jogos_job,
        trigger=IntervalTrigger(hours=1),
        args=[app],
        id='sincronizar_jogos',
        name='Sincronizar jogos novos',
        replace_existing=True
    )

    # Job G: a cada 30 minutos, alertas de palpites pendentes
    _scheduler.add_job(
        func=enviar_alertas_palpites_job,
        trigger=IntervalTrigger(minutes=30),
        args=[app],
        id='alertas_palpites',
        name='Alertas palpites pendentes',
        replace_existing=True
    )

    _scheduler.start()
    print("[SCHEDULER] Iniciado com 7 jobs ativos ✅")
    print("[SCHEDULER] Iniciado com 3 jobs ativos ✅")
    return _scheduler
