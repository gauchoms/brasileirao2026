from app import create_app, db
from sqlalchemy import text, inspect

app = create_app()

with app.app_context():
    inspector = inspect(db.engine)
    columns = [col['name'] for col in inspector.get_columns('regra_pontuacao')]
    
    if 'data_criacao' not in columns:
        # Adiciona sem default primeiro
        db.session.execute(text("ALTER TABLE regra_pontuacao ADD COLUMN data_criacao DATETIME"))
        # Preenche valores existentes
        db.session.execute(text("UPDATE regra_pontuacao SET data_criacao = datetime('now') WHERE data_criacao IS NULL"))
        print('Coluna data_criacao adicionada!')
    
    db.session.commit()
    print('Concluido!')
