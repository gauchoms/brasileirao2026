"""
Sincronizador Simples - Copia dados de Produção → Local
Usa SQLAlchemy para conectar nos dois bancos
"""

from sqlalchemy import create_engine, MetaData, Table
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

# ========================================
# CONFIGURAÇÕES - EDITE AQUI!
# ========================================

# URL do banco de PRODUÇÃO (PostgreSQL no Render)
PROD_URL = os.getenv('PROD_DATABASE_URL') or "postgresql://user:pass@host:5432/db"

# URL do banco LOCAL
# Para PostgreSQL local:
LOCAL_URL = "postgresql://localhost:5432/brasileirao_dev"
# Para SQLite:
# LOCAL_URL = "sqlite:///instance/app.db"

# Tabelas para sincronizar (ordem importa por causa de FKs!)
TABELAS = [
    'competicao',
    'time',
    'jogo',
    'meta',
    'projecao',
    'usuario',
    'avatar_sugerido',
    'regra_pontuacao',
    'bolao',
    'participante_bolao',
    'palpite',
    # ... adicione outras se necessário
]

# ========================================
# FUNÇÕES
# ========================================

def sincronizar():
    """Sincroniza dados de produção para local"""
    
    print("\n" + "="*70)
    print("🔄 SINCRONIZAÇÃO: PRODUÇÃO → LOCAL")
    print("="*70)
    
    # Conectar nos dois bancos
    print(f"\n📡 Conectando em PRODUÇÃO...")
    engine_prod = create_engine(PROD_URL)
    Session_prod = sessionmaker(bind=engine_prod)
    session_prod = Session_prod()
    
    print(f"📂 Conectando em LOCAL...")
    engine_local = create_engine(LOCAL_URL)
    Session_local = sessionmaker(bind=engine_local)
    session_local = Session_local()
    
    # Metadados
    metadata_prod = MetaData()
    metadata_prod.reflect(bind=engine_prod)
    
    metadata_local = MetaData()
    metadata_local.reflect(bind=engine_local)
    
    # Sincronizar cada tabela
    total_copiado = 0
    
    for tabela_nome in TABELAS:
        if tabela_nome not in metadata_prod.tables:
            print(f"   ⚠️ Tabela '{tabela_nome}' não existe em produção, pulando...")
            continue
        
        print(f"\n📋 Sincronizando tabela: {tabela_nome}")
        
        # Pegar tabela
        tabela_prod = Table(tabela_nome, metadata_prod, autoload_with=engine_prod)
        tabela_local = Table(tabela_nome, metadata_local, autoload_with=engine_local)
        
        # Ler dados de produção
        dados_prod = session_prod.execute(tabela_prod.select()).fetchall()
        
        if not dados_prod:
            print(f"   ℹ️ Tabela vazia em produção")
            continue
        
        # Limpar tabela local
        print(f"   🗑️ Limpando dados locais...")
        session_local.execute(tabela_local.delete())
        session_local.commit()
        
        # Inserir dados
        print(f"   ⬇️ Copiando {len(dados_prod)} registros...")
        
        for row in dados_prod:
            # Converter row para dict
            row_dict = dict(row._mapping)
            session_local.execute(tabela_local.insert().values(**row_dict))
        
        session_local.commit()
        
        total_copiado += len(dados_prod)
        print(f"   ✅ {len(dados_prod)} registros copiados")
    
    # Fechar conexões
    session_prod.close()
    session_local.close()
    
    print("\n" + "="*70)
    print(f"✅ SINCRONIZAÇÃO CONCLUÍDA! Total: {total_copiado} registros")
    print("="*70 + "\n")


def verificar_configuracao():
    """Verifica se as URLs estão configuradas corretamente"""
    
    print("\n🔍 Verificando configuração...")
    
    if "user:pass@host" in PROD_URL:
        print("❌ ERRO: Edite PROD_URL com a URL real do banco de produção!")
        print("   Exemplo: postgresql://user_abc:xyz123@dpg-xyz.oregon-postgres.render.com/db_abc")
        return False
    
    print("✅ Configuração OK!")
    return True


# ========================================
# MAIN
# ========================================

if __name__ == "__main__":
    if verificar_configuracao():
        try:
            sincronizar()
        except Exception as e:
            print(f"\n❌ ERRO: {e}")
            print("\nVerifique:")
            print("  1. As URLs dos bancos estão corretas?")
            print("  2. Você tem acesso de rede aos dois bancos?")
            print("  3. psycopg2 está instalado? (pip install psycopg2-binary)")
