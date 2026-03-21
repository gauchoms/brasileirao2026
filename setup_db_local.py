"""
Setup do Banco de Dados Local
Cria banco PostgreSQL local e aplica schema
"""

import subprocess
import os
from pathlib import Path

# ========================================
# CONFIGURAÇÕES
# ========================================

DB_NAME = "brasileirao_dev"
DB_USER = "postgres"  # Altere se necessário
DB_PASSWORD = "postgres"  # Altere se necessário
DB_HOST = "localhost"
DB_PORT = "5432"

# ========================================
# FUNÇÕES
# ========================================

def verificar_postgres_instalado():
    """Verifica se PostgreSQL está instalado"""
    print("\n🔍 Verificando instalação do PostgreSQL...")
    
    try:
        result = subprocess.run(
            ["psql", "--version"],
            capture_output=True,
            text=True,
            check=True
        )
        print(f"   ✅ {result.stdout.strip()}")
        return True
    except FileNotFoundError:
        print("   ❌ PostgreSQL não encontrado!")
        print("\n📥 Baixe e instale PostgreSQL:")
        print("   Windows: https://www.postgresql.org/download/windows/")
        print("   Mac: brew install postgresql")
        print("   Linux: sudo apt install postgresql")
        return False
    except subprocess.CalledProcessError:
        return False


def criar_banco():
    """Cria o banco de dados"""
    print(f"\n🗄️ Criando banco '{DB_NAME}'...")
    
    # Conectar como superuser para criar o banco
    cmd = [
        "psql",
        "-U", DB_USER,
        "-h", DB_HOST,
        "-p", DB_PORT,
        "-c", f"CREATE DATABASE {DB_NAME};"
    ]
    
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        print(f"   ✅ Banco '{DB_NAME}' criado!")
        return True
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode() if e.stderr else str(e)
        
        if "already exists" in error_msg:
            print(f"   ⚠️ Banco '{DB_NAME}' já existe!")
            
            resposta = input("\n   Deseja RECRIAR o banco? (TODOS os dados serão perdidos!) [s/N]: ")
            if resposta.lower() == 's':
                dropar_e_recriar()
                return True
            else:
                print("   ℹ️ Mantendo banco existente")
                return True
        else:
            print(f"   ❌ Erro ao criar banco: {error_msg}")
            return False


def dropar_e_recriar():
    """Dropa e recria o banco"""
    print(f"   🗑️ Dropando banco '{DB_NAME}'...")
    
    # Drop
    cmd_drop = [
        "psql",
        "-U", DB_USER,
        "-h", DB_HOST,
        "-p", DB_PORT,
        "-c", f"DROP DATABASE IF EXISTS {DB_NAME};"
    ]
    
    subprocess.run(cmd_drop, check=True, capture_output=True)
    print("   ✅ Banco dropado")
    
    # Create
    cmd_create = [
        "psql",
        "-U", DB_USER,
        "-h", DB_HOST,
        "-p", DB_PORT,
        "-c", f"CREATE DATABASE {DB_NAME};"
    ]
    
    subprocess.run(cmd_create, check=True, capture_output=True)
    print(f"   ✅ Banco '{DB_NAME}' recriado!")


def criar_schema():
    """Cria schema usando Flask-Migrate"""
    print("\n📋 Criando schema (tabelas)...")
    
    # Atualizar config.py para usar banco local
    print("   ℹ️ Certifique-se que config.py usa o banco local!")
    print(f"   DATABASE_URL = postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")
    
    input("\n   Pressione ENTER quando config.py estiver configurado...")
    
    # Executar migrations
    print("\n   🔄 Executando migrations...")
    
    try:
        # Criar migrations se não existir
        if not Path("migrations").exists():
            print("   📝 Inicializando Flask-Migrate...")
            subprocess.run(["flask", "db", "init"], check=True)
        
        # Gerar migration
        print("   📝 Gerando migration...")
        subprocess.run(["flask", "db", "migrate", "-m", "Initial schema"], check=True)
        
        # Aplicar migration
        print("   ⬆️ Aplicando migration...")
        subprocess.run(["flask", "db", "upgrade"], check=True)
        
        print("   ✅ Schema criado com sucesso!")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Erro ao criar schema: {e}")
        print("\n   💡 Tente manualmente:")
        print("      flask db init")
        print("      flask db migrate -m 'Initial schema'")
        print("      flask db upgrade")
        return False


def testar_conexao():
    """Testa conexão com o banco"""
    print("\n🔌 Testando conexão...")
    
    cmd = [
        "psql",
        "-U", DB_USER,
        "-h", DB_HOST,
        "-p", DB_PORT,
        "-d", DB_NAME,
        "-c", "SELECT version();"
    ]
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("   ✅ Conexão bem-sucedida!")
        print(f"   {result.stdout.split('|')[0].strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Erro na conexão: {e}")
        return False


def criar_env_local():
    """Cria arquivo .env.local com configurações"""
    print("\n📝 Criando .env.local...")
    
    env_content = f"""# Banco de dados LOCAL
DATABASE_URL=postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}

# Flask
FLASK_APP=run.py
FLASK_ENV=development
SECRET_KEY=dev-secret-key-change-in-production

# Debug
DEBUG=True
"""
    
    with open(".env.local", "w") as f:
        f.write(env_content)
    
    print("   ✅ Arquivo .env.local criado!")
    print("\n   💡 Para usar:")
    print("      # No seu config.py:")
    print("      from dotenv import load_dotenv")
    print("      load_dotenv('.env.local')")


# ========================================
# MAIN
# ========================================

def main():
    print("\n" + "="*70)
    print("🗄️ SETUP DO BANCO DE DADOS LOCAL")
    print("="*70)
    
    # 1. Verificar PostgreSQL
    if not verificar_postgres_instalado():
        return
    
    # 2. Criar banco
    if not criar_banco():
        return
    
    # 3. Testar conexão
    if not testar_conexao():
        return
    
    # 4. Criar .env.local
    criar_env_local()
    
    # 5. Criar schema
    print("\n" + "="*70)
    print("PRÓXIMO PASSO: Criar Schema")
    print("="*70)
    
    criar = input("\nDeseja criar o schema agora? [s/N]: ")
    if criar.lower() == 's':
        criar_schema()
    else:
        print("\n💡 Para criar o schema depois:")
        print("   1. Configure config.py para usar .env.local")
        print("   2. Execute:")
        print("      flask db init")
        print("      flask db migrate -m 'Initial schema'")
        print("      flask db upgrade")
    
    # Resumo
    print("\n" + "="*70)
    print("✅ SETUP CONCLUÍDO!")
    print("="*70)
    print(f"\n📊 Banco criado: {DB_NAME}")
    print(f"🔗 Connection string: postgresql://{DB_USER}:***@{DB_HOST}:{DB_PORT}/{DB_NAME}")
    print(f"📝 Configuração: .env.local")
    
    print("\n📋 PRÓXIMOS PASSOS:")
    print("   1. Configure config.py para usar DATABASE_URL do .env.local")
    print("   2. Execute: python sync_simples.py (para copiar dados de produção)")
    print("   3. Execute: python run.py (para iniciar app)")
    
    print("\n" + "="*70 + "\n")


if __name__ == "__main__":
    main()
