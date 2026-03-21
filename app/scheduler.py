# app/scheduler.py
# Atualização automática de resultados usando APScheduler

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
import pytz
import logging

logger = logging.getLogger(__name__)
BRASILIA = pytz.timezone('America/Sao_Paulo')


def atualizar_resultados_job(app):
    """
    Função principal que roda dentro do contexto Flask.
    Mesma lógica da rota /atualizar_resultados.
    """
    with app.app_context():
        from app.models import Jogo, Palpite, Bolao, ParticipanteBolao, Competicao
        from app.routes import calcular_pontos_palpite, RegraPontuacao
        from app.api import get_resultados_brasileirao
        from app import db

        logger.info(f"[SCHEDULER] Rodando atualização: {datetime.now(BRASILIA).strftime('%d/%m/%Y %H:%M')}")

        competicoes = Competicao.query.all()
        novos = 0
        palpites_calculados = 0

        for comp in competicoes:
            try:
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
                logger.error(f"[SCHEDULER] Erro na competição {comp.nome}: {e}")
                continue

        db.session.commit()
        logger.info(f"[SCHEDULER] Concluído: {novos} novos resultados, {palpites_calculados} palpites calculados")


def verificar_jogos_proximos(app):
    """
    Roda a cada 5 minutos e dispara atualização se houver
    jogo começando nos próximos 5 minutos ou terminando há menos de 15 minutos.
    """
    with app.app_context():
        from app.models import Jogo
        from app import db

        agora = datetime.now(BRASILIA)
        agora_str = agora.strftime('%Y-%m-%dT%H:%M')

        # Janela: jogo começa nos próximos 5 min
        em_5min = (agora + timedelta(minutes=5)).strftime('%Y-%m-%dT%H:%M')

        # Janela: jogo terminou há até 15 min (assumindo 105 min de duração padrão)
        terminou_ha_pouco = agora - timedelta(minutes=15)
        terminou_ha_pouco_str = terminou_ha_pouco.strftime('%Y-%m-%dT%H:%M')
        fim_jogo = (terminou_ha_pouco + timedelta(minutes=105)).strftime('%Y-%m-%dT%H:%M')

        jogos_proximos = Jogo.query.filter(
            Jogo.data >= agora_str,
            Jogo.data <= em_5min,
            Jogo.gols_casa == None
        ).count()

        jogos_terminando = Jogo.query.filter(
            Jogo.data >= terminou_ha_pouco_str,
            Jogo.data <= fim_jogo,
            Jogo.gols_casa == None
        ).count()

        if jogos_proximos > 0 or jogos_terminando > 0:
            logger.info(f"[SCHEDULER] Jogo detectado (próximos={jogos_proximos}, terminando={jogos_terminando}), atualizando...")
            atualizar_resultados_job(app)


def iniciar_scheduler(app):
    """
    Registra os 3 jobs e inicia o scheduler.
    Chamado dentro de create_app() no __init__.py.
    """
    scheduler = BackgroundScheduler(timezone=BRASILIA)

    # Job A+B: a cada 5 minutos, verifica se há jogo próximo ou terminando
    scheduler.add_job(
        func=verificar_jogos_proximos,
        trigger=IntervalTrigger(minutes=5),
        args=[app],
        id='verificar_jogos',
        name='Verificar jogos próximos/terminando',
        replace_existing=True
    )

    # Job C: de hora em hora, independente dos jogos
    scheduler.add_job(
        func=atualizar_resultados_job,
        trigger=IntervalTrigger(hours=1),
        args=[app],
        id='atualizar_hora',
        name='Atualização horária',
        replace_existing=True
    )

    scheduler.start()
    logger.info("[SCHEDULER] Iniciado com 2 jobs ativos")
    return scheduler
