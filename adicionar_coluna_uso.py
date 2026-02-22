from app import create_app, db
from sqlalchemy import text, inspect

app = create_app()

with app.app_context():
    # Verifica se a coluna já existe
    inspector = inspect(db.engine)
    columns = [col['name'] for col in inspector.get_columns('competicao')]
    
    if 'uso' not in columns:
        db.session.execute(text("ALTER TABLE competicao ADD COLUMN uso VARCHAR(20) DEFAULT 'ambos'"))
        db.session.commit()
        print('Coluna uso adicionada!')
    else:
        print('Coluna uso já existe!')
