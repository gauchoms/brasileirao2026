"""
Descobrir quais times têm projeções marcadas
"""

from app import create_app, db
from app.models import Projecao, Time, Jogo, Competicao
from sqlalchemy import func

app = create_app()

with app.app_context():
    print("\n" + "="*70)
    print("🔍 TIMES COM PROJEÇÕES MARCADAS")
    print("="*70)
    
    # Buscar times com projeções
    times_com_proj = db.session.query(
        Projecao.time_id,
        Time.nome,
        func.count(Projecao.id).label('total_projecoes')
    ).join(
        Time, Projecao.time_id == Time.id
    ).group_by(
        Projecao.time_id,
        Time.nome
    ).order_by(
        func.count(Projecao.id).desc()
    ).all()
    
    if not times_com_proj:
        print("\n❌ NENHUM time com projeções!")
    else:
        print(f"\n📊 {len(times_com_proj)} times têm projeções:\n")
        
        for time_id, nome, total in times_com_proj[:20]:  # Top 20
            print(f"   Time ID {time_id:3d} - {nome:30s} - {total:4d} projeções")
            
            # Pegar competição desse time
            jogo = Jogo.query.filter(
                (Jogo.time_casa_id == time_id) | (Jogo.time_fora_id == time_id)
            ).first()
            
            if jogo:
                comp = Competicao.query.get(jogo.competicao_id)
                if comp:
                    print(f"        └─ Competição: {comp.nome} (ID: {comp.id})")
                    print(f"        └─ URL: http://127.0.0.1:5000/graficos/comparativo/{comp.id}/{time_id}")
    
    print("\n" + "="*70)
    print("✅ Use as URLs acima para ver os gráficos!")
    print("="*70 + "\n")
