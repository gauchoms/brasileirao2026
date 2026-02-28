# PROJETO BRASILEIRÃO 2026 - RESUMO TÉCNICO COMPLETO

**Data:** 28/02/2026  
**Status:** Sistema 90% completo, responsivo mobile, aguardando ajustes finais

---

## 🎯 ÍNDICE RÁPIDO
1. Visão Geral
2. Arquitetura do Sistema
3. Funcionalidades Implementadas
4. Pendências Críticas
5. Banco de Dados
6. Deployment Render
7. Variáveis de Ambiente
8. Problemas Conhecidos

---

## 📋 VISÃO GERAL

### Stack Tecnológica
- **Backend:** Flask + SQLAlchemy
- **Frontend:** HTML/CSS/JS (sem framework)
- **Banco:** SQLite (local) / PostgreSQL (produção)
- **Deploy:** Render.com
- **APIs:** API-Football, SendGrid

### URLs Importantes
- **Produção:** https://brasileirao2026.onrender.com
- **Render Dashboard:** https://dashboard.render.com

---

## 🏗️ ARQUITETURA

### Estrutura de Diretórios
Brasileirao2026/
├── app/
│   ├── __init__.py          # Factory pattern, filtros Jinja2
│   ├── models.py            # Models SQLAlchemy
│   ├── routes.py            # Todas as rotas
│   ├── comprovante.py       # Hash e QR Code de palpites
│   ├── utils.py             # Conversão timezone UTC→Brasília
│   └── templates/
├── requirements.txt
├── config.py
├── run.py
└── .env

---

## ✅ FUNCIONALIDADES IMPLEMENTADAS

### 1. TIPOS DE BOLÃO (3 Modalidades)
A) Campeonato Completo - Todos jogos de UMA competição
B) Time + Campeonato - Jogos de UM time em UMA competição
C) Time + Ano Completo - Todos jogos de UM time no ano

### 2. SISTEMA DE PONTUAÇÃO ACUMULATIVA
- Pontos Base: Acertar resultado (vitória/empate)
- +Bônus: Acertar gols do vencedor
- +Bônus: Acertar gols do perdedor
- +Bônus: Acertar diferença de gols
- +Bônus Elástico (opcional): Jogos com N+ gols

**Checkbox Crítico:**
☑ Acertos parciais só valem se acertar o resultado

**Exemplo:**
Jogo real: Grêmio 3x1 Inter
Config: resultado=5, gols_venc=3, gols_perd=2, diferença=1

Palpite 3x1 → 11 pts (5+3+2+1) ✅ Placar exato
Palpite 2x1 → 7 pts (5+2) ✓resultado ✓gols_perd
Palpite 1x3 → 0 pts (errou resultado)

**Função:** app/routes.py → calcular_pontos_palpite()

### 3. DASHBOARD PERSONALIZÁVEL
- Admin marca quais competições aparecem
- Flag: Competicao.disponivel_dashboard
- Rota: /admin/toggle_dashboard_competicao

### 4. TAB "TODOS OS PALPITES"
- Lista jogos expansível
- Mostra palpites após jogo iniciar
- Pontuação se encerrado

### 5. RESPONSIVIDADE MOBILE
- Menu hamburguer ☰
- Todas páginas ajustadas
- @media (max-width: 768px)

### 6. COMPARTILHAMENTO BOLÃO
- Botão Copiar Link
- Botão WhatsApp

### 7. TIMEZONE BRASÍLIA
- Filtro |brasilia nos templates
- app/utils.py → converter_utc_brasilia()

### 8. TAB "REGRAS" NO BOLÃO
- Sistema de pontos explicado
- Simulador automático com exemplos

---

## 🔴 PENDÊNCIAS CRÍTICAS

### 1. SUBSTITUIR regra_pontuacao por regra
Ctrl+Shift+F → regra_pontuacao → Replace: regra (só .html)

### 2. MIGRAÇÃO RENDER
Rota: /migrar_pontuacao_acumulativa_render
Adiciona colunas: pontos_resultado, requer_resultado_correto

### 3. TESTAR PONTUAÇÃO
Criar bolão → palpites → atualizar resultados → verificar

---

## 💾 BANCO DE DADOS

**Local:** DATABASE_URL=sqlite:///brasileirao.db
**Produção:** PostgreSQL (auto Render)

**Admin Local:**
username: admin
password: admin123

---

## 🚀 DEPLOYMENT RENDER

### Environment Variables
API_FOOTBALL_KEY=3933fb4c71088beac7cc02e6d1370750
DATABASE_URL=(auto)
SECRET_KEY=(configurar)

### Deploy
git add .
git commit -m "msg"
git push

---

## 🔑 .ENV LOCAL

SECRET_KEY=brasileirao2026_chave_secreta_super_segura_123456789
DATABASE_URL=sqlite:///brasileirao.db
API_FOOTBALL_KEY=3933fb4c71088beac7cc02e6d1370750
SENDGRID_API_KEY=opcional

---

## 🛠️ COMANDOS ÚTEIS

### Rodar
cd C:\Projetos\Brasileirao2026
venv\Scripts\activate
python run.py

### Criar Admin
python
from app import create_app, db
from app.models import Usuario
app = create_app()
with app.app_context():
    admin = Usuario(username='admin', email='admin@brasileirao2026.com', is_admin=True)
    admin.set_password('admin123')
    db.session.add(admin)
    db.session.commit()
exit()

---

## 🎯 PRÓXIMOS PASSOS

1. Fix regra_pontuacao → regra
2. Deploy + migração
3. Testar pontuação
4. Mercado Pago (R$ 15/bolão)

---

**PARA PRÓXIMA CONVERSA:**
"Claude, continue o projeto Brasileirão 2026. Leia RESUMO_COMPLETO.md"
