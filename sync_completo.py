"""
Sincronização COMPLETA: Schema + Dados
Copia TUDO de produção (estrutura + registros)
"""

import os
import subprocess
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Carregar variáveis do .env.sync
load_dotenv('.env.sync')

# ========================================
# CONFIGURAÇÕES
# ========================================

PROD_URL = os.getenv('PROD_DATABASE_URL')
LOCAL_URL = os.getenv('LOCAL_DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/brasileirao_dev')

BACKUP_DIR = Path("backups")
BACKUP_DIR.mkdir(exist_ok=True)

# ========================================
# FUNÇÕES
# ========================================

def verificar_config():
    """Verifica se configuração está OK"""
    print("\n🔍 Verificando configuração...")
    
    if not PROD_URL or "user:pass" in PROD_URL:
        print("❌ PROD_DATABASE_URL não configurada!")
        print("   Edite .env.sync com a URL real do Render")
        return False
    
    print(f"✅ Produção: {PROD_URL[:30]}...")
    print(f"✅ Local: {LOCAL_URL}")
    return True


def dump_schema_producao():
    """Faz dump APENAS do schema (estrutura) de produção"""
    print("\n📐 Fazendo dump do SCHEMA de produção...")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    schema_file = BACKUP_DIR / f"schema_{timestamp}.sql"
    
    cmd = f'pg_dump --schema-only "{PROD_URL}" -f "{schema_file}"'
    
    try:
        subprocess.run(cmd, shell=True, check=True, capture_output=True)
        print(f"   ✅ Schema salvo: {schema_file.name}")
        return schema_file
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Erro: {e}")
        return None
    except FileNotFoundError:
        print("   ❌ pg_dump não encontrado!")
        print("      Instale PostgreSQL client: https://www.postgresql.org/download/")
        return None


def dump_dados_producao():
    """Faz dump APENAS dos dados de produção"""
    print("\n📦 Fazendo dump dos DADOS de produção...")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dados_file = BACKUP_DIR / f"dados_{timestamp}.sql"
    
    cmd = f'pg_dump --data-only "{PROD_URL}" -f "{dados_file}"'
    
    try:
        subprocess.run(cmd, shell=True, check=True, capture_output=True)
        size_kb = dados_file.stat().st_size / 1024
        print(f"   ✅ Dados salvos: {dados_file.name} ({size_kb:.1f} KB)")
        return dados_file
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Erro: {e}")
        return None


def limpar_banco_local():
    """Limpa banco local (dropa e recria)"""
    print("\n🗑️ Limpando banco local...")
    
    # Extrair nome do banco da URL
    db_name = LOCAL_URL.split('/')[-1].split('?')[0]
    base_url = LOCAL_URL.rsplit('/', 1)[0]
    
    # Conectar ao postgres (não ao banco específico)
    postgres_url = base_url + '/postgres'
    
    # Dropar
    cmd_drop = f'psql "{postgres_url}" -c "DROP DATABASE IF EXISTS {db_name};"'
    subprocess.run(cmd_drop, shell=True, capture_output=True)
    
    # Criar
    cmd_create = f'psql "{postgres_url}" -c "CREATE DATABASE {db_name};"'
    subprocess.run(cmd_create, shell=True, check=True, capture_output=True)
    
    print(f"   ✅ Banco '{db_name}' limpo e recriado")


def restaurar_schema_local(schema_file):
    """Restaura schema no banco local"""
    print("\n📐 Restaurando SCHEMA no banco local...")
    
    cmd = f'psql "{LOCAL_URL}" -f "{schema_file}"'
    
    try:
        subprocess.run(cmd, shell=True, check=True, capture_output=True)
        print("   ✅ Schema restaurado!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Erro: {e}")
        return False


def restaurar_dados_local(dados_file):
    """Restaura dados no banco local"""
    print("\n📦 Restaurando DADOS no banco local...")
    
    cmd = f'psql "{LOCAL_URL}" -f "{dados_file}"'
    
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print("   ✅ Dados restaurados!")
        
        # Contar registros de algumas tabelas
        contar_registros()
        return True
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Erro: {e}")
        if e.stderr:
            print(f"   Detalhes: {e.stderr.decode()[:200]}")
        return False


def contar_registros():
    """Conta registros nas principais tabelas"""
    print("\n📊 Verificando dados...")
    
    tabelas = ['time', 'jogo', 'projecao', 'competicao', 'usuario']
    
    for tabela in tabelas:
        cmd = f'psql "{LOCAL_URL}" -t -c "SELECT COUNT(*) FROM {tabela};"'
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            count = result.stdout.strip()
            print(f"   {tabela}: {count} registros")
        except:
            pass


# ========================================
# MAIN
# ========================================

def main():
    print("\n" + "="*70)
    print("🔄 SINCRONIZAÇÃO COMPLETA: SCHEMA + DADOS")
    print("="*70)
    
    # 1. Verificar config
    if not verificar_config():
        return
    
    # 2. Confirmação
    print("\n⚠️ ATENÇÃO: Isso vai SUBSTITUIR completamente o banco local!")
    resposta = input("Deseja continuar? [s/N]: ")
    if resposta.lower() != 's':
        print("❌ Cancelado")
        return
    
    # 3. Dump schema
    schema_file = dump_schema_producao()
    if not schema_file:
        return
    
    # 4. Dump dados
    dados_file = dump_dados_producao()
    if not dados_file:
        return
    
    # 5. Limpar local
    limpar_banco_local()
    
    # 6. Restaurar schema
    if not restaurar_schema_local(schema_file):
        return
    
    # 7. Restaurar dados
    if not restaurar_dados_local(dados_file):
        return
    
    # Resumo
    print("\n" + "="*70)
    print("✅ SINCRONIZAÇÃO CONCLUÍDA COM SUCESSO!")
    print("="*70)
    
    print(f"\n📁 Backups salvos em: {BACKUP_DIR}/")
    print(f"   - Schema: {schema_file.name}")
    print(f"   - Dados: {dados_file.name}")
    
    print("\n🎯 PRÓXIMO PASSO:")
    print("   Execute: python run.py")
    print("   Acesse: http://127.0.0.1:5000/graficos/comparativo/1/12")
    
    print("\n" + "="*70 + "\n")


if __name__ == "__main__":
    main()