"""
Script de diagnóstico - Verificar projeções
"""

from app import create_app, db
from app.models import Projecao, Usuario, Jogo, Time, Competicao

app = create_app()

with app.app_context():
    print("\n" + "="*60)
    print("🔍 DIAGNÓSTICO DE PROJEÇÕES")
    print("="*60)
    
    # 1. Verificar usuários admin
    print("\n1️⃣ USUÁRIOS ADMIN:")
    admins = Usuario.query.filter_by(is_admin=True).all()
    if admins:
        for admin in admins:
            print(f"   ✅ {admin.username} (ID: {admin.id}) - is_admin: {admin.is_admin}")
    else:
        print("   ❌ NENHUM USUÁRIO ADMIN ENCONTRADO!")
    
    # 2. Verificar total de projeções
    print("\n2️⃣ PROJEÇÕES NO BANCO:")
    total_proj = Projecao.query.count()
    print(f"   Total de projeções: {total_proj}")
    
    if total_proj > 0:
        print("\n   Primeiras 10 projeções:")
        projs = Projecao.query.limit(10).all()
        for p in projs:
            time = Time.query.get(p.time_id)
            jogo = Jogo.query.get(p.jogo_id)
            print(f"   - Jogo {p.jogo_id} | Time: {time.nome if time else '?'} | Tipo: {p.tipo} | Pontos: {p.pontos}")
    
    # 3. Verificar jogos
    print("\n3️⃣ JOGOS NO BANCO:")
    total_jogos = Jogo.query.count()
    print(f"   Total de jogos: {total_jogos}")
    
    jogos_com_resultado = Jogo.query.filter(Jogo.gols_casa.isnot(None)).count()
    print(f"   Jogos com resultado: {jogos_com_resultado}")
    
    jogos_sem_resultado = Jogo.query.filter(Jogo.gols_casa.is_(None)).count()
    print(f"   Jogos sem resultado (futuros): {jogos_sem_resultado}")
    
    # 4. Verificar competições
    print("\n4️⃣ COMPETIÇÕES:")
    comps = Competicao.query.all()
    for comp in comps:
        jogos_comp = Jogo.query.filter_by(competicao_id=comp.id).count()
        print(f"   - {comp.nome} (ID: {comp.id}) - {jogos_comp} jogos")
    
    # 5. Sugestão
    print("\n5️⃣ AÇÕES NECESSÁRIAS:")
    if not admins:
        print("   ⚠️ CRIAR USUÁRIO ADMIN:")
        print("      Execute: python -c \"from app import create_app, db; from app.models import Usuario; app = create_app(); app.app_context().push(); u = Usuario.query.first(); u.is_admin = True; db.session.commit(); print('✅ Admin criado!')\"")
    
    if total_proj == 0:
        print("   ⚠️ MARCAR PROJEÇÕES:")
        print("      1. Acesse: http://127.0.0.1:5000/projecoes")
        print("      2. Faça login como admin")
        print("      3. Selecione um time e uma meta")
        print("      4. Clique em Vence/Empata/Perde nos jogos")
    
    print("\n" + "="*60)
    print("✅ DIAGNÓSTICO COMPLETO")
    print("="*60 + "\n")
