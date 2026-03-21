"""
Script de atualização automática de resultados
Executado pelos cron jobs do Render
"""

import os
import sys
from datetime import datetime

# Adicionar diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import Competicao, Jogo

def atualizar_resultados():
    """Atualiza resultados de todas as competições"""
    app = create_app()
    
    with app.app_context():
        print(f"🕐 [{datetime.now()}] Iniciando atualização automática...")
        
        try:
            # Importar função de atualização
            from app.api_football import buscar_e_atualizar_resultados
            
            competicoes = Competicao.query.all()
            print(f"📊 {len(competicoes)} competições encontradas")
            
            for comp in competicoes:
                try:
                    print(f"   🔄 Atualizando {comp.nome}...")
                    buscar_e_atualizar_resultados(comp.id)
                    print(f"   ✅ {comp.nome} atualizado!")
                except Exception as e:
                    print(f"   ❌ Erro em {comp.nome}: {e}")
            
            print(f"🎉 [{datetime.now()}] Atualização concluída!")
            
        except Exception as e:
            print(f"❌ Erro geral: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

if __name__ == '__main__':
    atualizar_resultados()
