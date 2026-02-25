from app import create_app, db
from sqlalchemy import text, inspect

app = create_app()

with app.app_context():
    inspector = inspect(db.engine)
    columns = [col['name'] for col in inspector.get_columns('regra_pontuacao')]
    
    if 'modo' not in columns:
        db.session.execute(text("ALTER TABLE regra_pontuacao ADD COLUMN modo VARCHAR(20) DEFAULT 'acertos_parciais'"))
        print('Coluna modo adicionada!')
    
    db.session.commit()
    print('Concluido!')
