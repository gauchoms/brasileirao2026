from app import create_app, db
from sqlalchemy import text, inspect

app = create_app()

with app.app_context():
    inspector = inspect(db.engine)
    columns = [col['name'] for col in inspector.get_columns('usuario')]
    
    if 'termos_aceitos_em' not in columns:
        db.session.execute(text("ALTER TABLE usuario ADD COLUMN termos_aceitos_em TIMESTAMP"))
        print('Coluna termos_aceitos_em adicionada!')
    
    db.session.commit()
    print('Concluído!')