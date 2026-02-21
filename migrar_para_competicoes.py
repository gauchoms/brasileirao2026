from app import create_app, db
from app.models import Competicao, Jogo

app = create_app()

with app.app_context():
    # Cria a competição Brasileirão 2026
    brasileirao = Competicao.query.filter_by(nome='Brasileirão Série A 2026').first()
    
    if not brasileirao:
        brasileirao = Competicao(
            nome='Brasileirão Série A 2026',
            ano=2026,
            tipo='brasileirao',
            api_league_id=71
        )
        db.session.add(brasileirao)
        db.session.commit()
        print(f"Competição criada: {brasileirao.nome} (ID: {brasileirao.id})")
    else:
        print(f"Competição já existe: {brasileirao.nome} (ID: {brasileirao.id})")
    
    # Associa todos os jogos existentes ao Brasileirão
    jogos = Jogo.query.all()
    atualizado = 0
    
    for jogo in jogos:
        if not hasattr(jogo, 'competicao_id') or jogo.competicao_id is None:
            jogo.competicao_id = brasileirao.id
            atualizado += 1
    
    db.session.commit()
    print(f"{atualizado} jogos associados ao Brasileirão 2026")