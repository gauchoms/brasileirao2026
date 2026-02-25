from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    # Permite NULL em competicao_id criando uma nova tabela
    db.session.execute(text("""
        CREATE TABLE IF NOT EXISTS bolao_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome VARCHAR(100) NOT NULL,
            competicao_id INTEGER,
            dono_id INTEGER NOT NULL,
            codigo_convite VARCHAR(10) NOT NULL UNIQUE,
            regra_pontuacao_id INTEGER NOT NULL,
            tipo_acesso VARCHAR(20) DEFAULT 'publico',
            tipo_bolao VARCHAR(30) DEFAULT 'campeonato_completo',
            time_especifico_id INTEGER,
            ano INTEGER,
            status_pagamento VARCHAR(20) DEFAULT 'pendente',
            valor_pago FLOAT DEFAULT 0.0,
            data_pagamento DATETIME,
            status VARCHAR(20) DEFAULT 'ativo',
            data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (competicao_id) REFERENCES competicao(id),
            FOREIGN KEY (dono_id) REFERENCES usuario(id),
            FOREIGN KEY (regra_pontuacao_id) REFERENCES regra_pontuacao(id),
            FOREIGN KEY (time_especifico_id) REFERENCES time(id)
        )
    """))
    
    # Copia dados da tabela antiga
    db.session.execute(text("""
        INSERT INTO bolao_new 
        SELECT * FROM bolao
    """))
    
    # Remove tabela antiga
    db.session.execute(text("DROP TABLE bolao"))
    
    # Renomeia nova tabela
    db.session.execute(text("ALTER TABLE bolao_new RENAME TO bolao"))
    
    db.session.commit()
    print('Tabela bolao recriada com competicao_id nullable!')