"""
Descobrir IDs corretos no banco PostgreSQL
"""

from app import create_app, db
from app.models import Competicao, Time, Jogo, Projecao
from sqlalchemy import func

app = create_app()

with app.app_context():
    print("\n" + "="*70)
    print("🔍 VERIFICANDO IDs NO BANCO POSTGRESQL")
    print("="*70)
    
    # 1. Qual banco está sendo usado?
    print(f"\n📊 Banco conectado: {db.engine.url}")
    
    # 2. Competições
    print("\n🏆 COMPETIÇÕES:")
    competicoes = Competicao.query.all()
    for comp in competicoes:
        total_jogos = Jogo.query.filter_by(competicao_id=comp.id).count()
        print(f"   ID {comp.id:2d} - {comp.nome:40s} - {total_jogos} jogos")
    
    # 3. Times com mais jogos
    print("\n⚽ TIMES (top 10 com mais jogos):")
    times_jogos = db.session.query(
        Time.id,
        Time.nome,
        func.count(Jogo.id).label('total_jogos')
    ).join(
        Jogo, 
        (Jogo.time_casa_id == Time.id) | (Jogo.time_fora_id == Time.id)
    ).group_by(
        Time.id, Time.nome
    ).order_by(
        func.count(Jogo.id).desc()
    ).limit(10).all()
    
    for time_id, nome, total in times_jogos:
        print(f"   ID {time_id:3d} - {nome:30s} - {total} jogos")
    
    # 4. Times com projeções
    print("\n📊 TIMES COM PROJEÇÕES (top 10):")
    times_proj = db.session.query(
        Time.id,
        Time.nome,
        func.count(Projecao.id).label('total_proj')
    ).join(
        Projecao, Projecao.time_id == Time.id
    ).group_by(
        Time.id, Time.nome
    ).order_by(
        func.count(Projecao.id).desc()
    ).limit(10).all()
    
    for time_id, nome, total in times_proj:
        # Pegar competição desse time
        jogo = Jogo.query.filter(
            (Jogo.time_casa_id == time_id) | (Jogo.time_fora_id == time_id)
        ).first()
        
        comp_info = ""
        if jogo:
            comp = Competicao.query.get(jogo.competicao_id)
            if comp:
                comp_info = f"Competição: {comp.id} - {comp.nome}"
        
        print(f"   ID {time_id:3d} - {nome:30s} - {total:4d} projeções")
        if comp_info:
            print(f"        └─ {comp_info}")
            print(f"        └─ URL: http://127.0.0.1:5000/graficos/comparativo/{jogo.competicao_id}/{time_id}")
    
    print("\n" + "="*70)
    print("✅ Use as URLs acima para acessar os gráficos!")
    print("="*70 + "\n")
