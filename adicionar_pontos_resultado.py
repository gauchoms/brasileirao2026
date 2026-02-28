from app import create_app, db
from sqlalchemy import text, inspect

app = create_app()

with app.app_context():
    inspector = inspect(db.engine)
    columns = [col['name'] for col in inspector.get_columns('regra_pontuacao')]
    
    # Adiciona nova coluna pontos_resultado
    if 'pontos_resultado' not in columns:
        db.session.execute(text("ALTER TABLE regra_pontuacao ADD COLUMN pontos_resultado INTEGER DEFAULT 5"))
        print('Coluna pontos_resultado adicionada!')
    
    # Adiciona checkbox de regra
    if 'requer_resultado_correto' not in columns:
        db.session.execute(text("ALTER TABLE regra_pontuacao ADD COLUMN requer_resultado_correto INTEGER DEFAULT 1"))
        print('Coluna requer_resultado_correto adicionada!')
    
    # Remove coluna modo (se existir)
    if 'modo' in columns:
        # SQLite não permite DROP COLUMN facilmente, então só ignora
        print('Coluna modo será ignorada (SQLite não suporta DROP COLUMN)')
    
    # Atualiza valores padrão para regras antigas
    db.session.execute(text("""
        UPDATE regra_pontuacao 
        SET pontos_resultado = 5,
            pontos_gols_vencedor = 3,
            pontos_gols_perdedor = 2,
            pontos_diferenca_gols = 1
        WHERE pontos_resultado IS NULL
    """))
    
    db.session.commit()
    print('Concluído!')