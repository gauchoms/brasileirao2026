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

    _scheduler.start()
    print("[SCHEDULER] Iniciado com 2 jobs ativos ✅")
    return _scheduler
