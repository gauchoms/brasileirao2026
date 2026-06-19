"""
Script de atualização automática de resultados
Executado pelo Cron Job do Render (todo hora no :00)
O APScheduler interno roda no :30 como backup.
"""

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db

def atualizar_resultados():
    app = create_app()
    with app.app_context():
        print(f"[CRON] {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} — Iniciando atualização...")
        try:
            from app.scheduler import atualizar_resultados_job, sincronizar_jogos_job
            sincronizar_jogos_job(app)   # importa jogos novos primeiro
            atualizar_resultados_job(app) # depois atualiza placares
            print(f"[CRON] Concluído com sucesso ✅")
        except Exception as e:
            print(f"[CRON] Erro: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

if __name__ == '__main__':
    atualizar_resultados()
