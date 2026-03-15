"""
Script para sincronizar dados de PRODUÇÃO → STAGING
Uso: python scripts/sync_prod_to_staging.py
"""

import subprocess
import os
from datetime import datetime

# URLs dos bancos (pegar do Render)
DATABASE_URL_PROD = "postgresql://brasileirao2026:OvURkhUdUJwiwZQW8kdWQZfgz8Yy6NdP@dpg-d6ad3m7pm1nc73d8hbu0-a.oregon-postgres.render.com/brasileirao2026"
DATABASE_URL_STAGING = "postgresql://brasileirao2026_staging:4JpBhB3sG7Yw69LdE9pMmGkAybVVkQeR@dpg-d6r1v0ea2pns73a9dsr0-a.oregon-postgres.render.com/brasileirao2026_staging"

def sync_databases():
    """
    Copia dados de produção para staging
    """
    print("🔄 Iniciando sincronização Produção → Staging...")
    print(f"📅 {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
    
    # 1. Fazer dump do banco de produção
    print("📦 1/3 - Fazendo backup do banco de produção...")
    dump_file = f"backup_prod_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
    
    try:
        subprocess.run([
            "pg_dump",
            DATABASE_URL_PROD,
            "-f", dump_file,
            "--no-owner",
            "--no-acl"
        ], check=True)
        print(f"✅ Backup criado: {dump_file}\n")
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro ao criar backup: {e}")
        return False
    
    # 2. Limpar staging
    print("🗑️  2/3 - Limpando banco de staging...")
    print("⚠️  ATENÇÃO: Isso vai APAGAR todos os dados do staging!")
    
    confirma = input("Continuar? (s/N): ")
    if confirma.lower() != 's':
        print("❌ Cancelado pelo usuário.")
        os.remove(dump_file)
        return False
    
    try:
        subprocess.run([
            "psql",
            DATABASE_URL_STAGING,
            "-c", "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
        ], check=True)
        print("✅ Staging limpo\n")
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro ao limpar staging: {e}")
        os.remove(dump_file)
        return False
    
    # 3. Restaurar no staging
    print("📥 3/3 - Restaurando dados no staging...")
    
    try:
        subprocess.run([
            "psql",
            DATABASE_URL_STAGING,
            "-f", dump_file
        ], check=True)
        print("✅ Dados restaurados no staging!\n")
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro ao restaurar: {e}")
        os.remove(dump_file)
        return False
    
    # 4. Limpar arquivo temporário
    os.remove(dump_file)
    print(f"🗑️  Arquivo temporário removido: {dump_file}\n")
    
    print("=" * 50)
    print("✅ SINCRONIZAÇÃO CONCLUÍDA COM SUCESSO!")
    print("=" * 50)
    print(f"\n🌐 Staging atualizado com dados de produção!")
    print(f"📍 https://brasileirao2026-staging.onrender.com\n")
    
    return True

if __name__ == "__main__":
    sync_databases()