# 🔄 Sincronização de Banco de Dados

Sistema para sincronizar dados do banco de **PRODUÇÃO** → **LOCAL** periodicamente.

---

## 📋 **POR QUE USAR?**

- ✅ Trabalhar com dados reais localmente
- ✅ Testar mudanças sem afetar produção
- ✅ Debugging com dados reais
- ✅ Desenvolvimento sem depender de internet

---

## ⚙️ **CONFIGURAÇÃO INICIAL**

### **1. Instalar dependências**

```bash
pip install psycopg2-binary python-dotenv
```

### **2. Configurar credenciais**

Copie o arquivo `.env.sync.example` para `.env.sync`:

```bash
cp .env.sync.example .env.sync
```

Edite `.env.sync` com suas credenciais reais:

```bash
# Banco de PRODUÇÃO (Render, Heroku, etc)
PROD_DATABASE_URL=postgresql://user:pass@host:5432/db

# Banco LOCAL
LOCAL_DATABASE_URL=postgresql://localhost:5432/brasileirao_dev
# OU
LOCAL_DATABASE_URL=sqlite:///instance/app.db
```

---

## 🚀 **COMO USAR**

### **Opção 1: Script Simples (RECOMENDADO)**

```bash
python sync_simples.py
```

**O que faz:**
- Conecta nos dois bancos
- Limpa dados locais
- Copia todos os registros de produção
- Mostra progresso por tabela

**Vantagens:**
- ✅ Funciona com PostgreSQL ou SQLite
- ✅ Não precisa de ferramentas externas
- ✅ Fácil de entender e modificar

---

### **Opção 2: Script Completo (com dumps)**

```bash
python sync_database.py
```

**Menu interativo:**
```
1. Dump PostgreSQL → Restaurar local
2. Sincronizar via Python
3. Apenas fazer backup
```

---

## 📅 **SINCRONIZAÇÃO AUTOMÁTICA**

### **Adicionar ao crontab (Linux/Mac)**

Sincronizar todo dia às 2h da manhã:

```bash
crontab -e
```

Adicione:
```bash
0 2 * * * cd /caminho/projeto && python sync_simples.py
```

### **Adicionar ao Task Scheduler (Windows)**

1. Abra "Agendador de Tarefas"
2. Criar Tarefa Básica
3. Nome: "Sync Banco Brasileirão"
4. Gatilho: Diariamente às 02:00
5. Ação: Iniciar programa
   - Programa: `python`
   - Argumentos: `C:\Projetos\Brasileirao2026\sync_simples.py`

---

## 🛡️ **SEGURANÇA**

**⚠️ NUNCA FAÇA COMMIT DO `.env.sync`!**

Adicione ao `.gitignore`:
```
.env.sync
backups/*.sql
```

---

## 🔍 **TROUBLESHOOTING**

### **Erro: "psycopg2 not found"**

```bash
pip install psycopg2-binary
```

### **Erro: "could not connect to server"**

Verifique:
- ✅ Credenciais do banco estão corretas?
- ✅ Firewall permite conexão?
- ✅ IP está liberado no Render/Heroku?

### **Erro: "permission denied"**

Seu usuário precisa de permissão para:
- Ler do banco de produção
- Escrever no banco local

---

## 📊 **TABELAS SINCRONIZADAS**

Por padrão, sincroniza (nessa ordem):

1. `competicao`
2. `time`
3. `jogo`
4. `meta`
5. `projecao` ← **SUAS MARCAÇÕES!**
6. `usuario`
7. `bolao`
8. `palpite`

---

## ⚡ **DICAS DE PERFORMANCE**

### **Sincronizar apenas algumas tabelas**

Edite `sync_simples.py`:

```python
TABELAS = [
    'competicao',
    'time',
    'jogo',
    'projecao',  # Apenas o essencial
]
```

### **Sincronizar apenas dados novos**

(TODO: implementar sincronização incremental)

---

## 📞 **SUPORTE**

Dúvidas? Problemas?
- Verifique os logs do script
- Teste conexão manual: `psql "postgresql://..."`
- Confira se as URLs estão corretas

---

## ✅ **CHECKLIST**

- [ ] Instalou `psycopg2-binary`
- [ ] Criou `.env.sync` com credenciais
- [ ] Adicionou `.env.sync` ao `.gitignore`
- [ ] Testou `python sync_simples.py`
- [ ] Verificou que dados foram copiados
- [ ] (Opcional) Configurou sincronização automática

---

**Pronto! Agora você pode trabalhar com dados reais localmente!** 🎯
