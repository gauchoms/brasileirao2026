"""
Script para atualização automática de resultados
Roda via Cron Job no Render
- De hora em hora (base)
- Horários extras após jogos (18h, 20h, 22h, 00h)
"""

import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.api import get_resultados_brasileirao, atualizar_pontuacao
from app.models import Jogo, Competicao, Palpite, Bolao

def atualizar_resultados():
    """
    Atualiza resultados de jogos finalizados
    Prioriza jogos das últimas 4 horas
    """
    app = create_app()
    
    with app.app_context():
        agora = datetime.now()
        print(f"🔄 Atualização automática iniciada")
        print(f"🕐 {agora.strftime('%d/%m/%Y %H:%M:%S')}\n")
        
        # Buscar competições ativas
        competicoes = Competicao.query.all()
        
        jogos_atualizados = 0
        boloes_recalculados = set()
        
        for comp in competicoes:
            try:
                print(f"📊 Processando: {comp.nome}")
                
                # Buscar jogos desta competição que ainda não têm resultado
                jogos_pendentes = Jogo.query.filter_by(
                    competicao_id=comp.id,
                    gols_casa=None
                ).all()
                
                if not jogos_pendentes:
                    print(f"   ✓ Sem jogos pendentes\n")
                    continue
                
                # Buscar resultados da API
                resultados = get_resultados_brasileirao(
                    comp.liga_id if hasattr(comp, 'liga_id') else None, 
                    comp.ano
                )
                
                if not resultados:
                    print(f"   ⚠️  Sem dados da API\n")
                    continue
                
                # Criar dicionário de resultados por api_id
                resultados_dict = {r['fixture_id']: r for r in resultados}
                
                # Processar cada jogo pendente
                for jogo in jogos_pendentes:
                    if not jogo.api_id or jogo.api_id not in resultados_dict:
                        continue
                    
                    resultado = resultados_dict[jogo.api_id]
                    
                    # Verificar se jogo está finalizado
                    if resultado.get('status') in ['Match Finished', 'FT', 'AET', 'PEN']:
                        jogo.gols_casa = resultado['gols_casa']
                        jogo.gols_fora = resultado['gols_fora']
                        
                        # Atualizar pontuação de TODOS os bolões que têm este jogo
                        palpites = Palpite.query.filter_by(jogo_id=jogo.id).all()
                        
                        for palpite in palpites:
                            atualizar_pontuacao(jogo.id)
                            boloes_recalculados.add(palpite.bolao_id)
                        
                        jogos_atualizados += 1
                        print(f"   ✅ {jogo.time_casa.nome} {jogo.gols_casa}x{jogo.gols_fora} {jogo.time_fora.nome}")
                
                db.session.commit()
                print()
                
            except Exception as e:
                print(f"   ❌ Erro: {e}\n")
                db.session.rollback()
                continue
        
        # Resumo
        print("=" * 60)
        print(f"✅ Atualização concluída!")
        print(f"📊 {jogos_atualizados} jogos finalizados")
        print(f"🎯 {len(boloes_recalculados)} bolões atualizados")
        print(f"🕐 {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        print("=" * 60 + "\n")

if __name__ == "__main__":
    atualizar_resultados()