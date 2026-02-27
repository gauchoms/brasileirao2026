from app import create_app, db
from sqlalchemy import text, inspect

app = create_app()

with app.app_context():
    inspector = inspect(db.engine)
    columns = [col['name'] for col in inspector.get_columns('palpite')]
    
    if 'hash_comprovante' not in columns:
        db.session.execute(text("ALTER TABLE palpite ADD COLUMN hash_comprovante VARCHAR(64)"))
        print('Coluna hash_comprovante adicionada!')
    
    if 'timestamp_preciso' not in columns:
        db.session.execute(text("ALTER TABLE palpite ADD COLUMN timestamp_preciso BIGINT"))
        print('Coluna timestamp_preciso adicionada!')
    
    db.session.commit()
    print('Concluído!')