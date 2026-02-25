from app import create_app, db
from sqlalchemy import text, inspect

app = create_app()

with app.app_context():
    inspector = inspect(db.engine)
    columns = [col['name'] for col in inspector.get_columns('competicao')]
    
    if 'disponivel_dashboard' not in columns:
        db.session.execute(text("ALTER TABLE competicao ADD COLUMN disponivel_dashboard INTEGER DEFAULT 0"))
        # Marca apenas Série A como disponível
        db.session.execute(text("UPDATE competicao SET disponivel_dashboard = 1 WHERE nome LIKE '%Serie A%' OR nome LIKE '%Série A%'"))
        print('Coluna disponivel_dashboard adicionada! Série A marcada.')
    
    db.session.commit()
    print('Concluido!')
