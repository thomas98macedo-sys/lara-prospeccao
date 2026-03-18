LARA — Prospecção B2B | Backup v1 Stable
=========================================
Data: 2026-03-10
Status: Funcionando (auth Firebase OK, busca Google Places OK)

Arquivos:
  - index.html    -> App completa (HTML + CSS + JS + Firebase)
  - server.py     -> Backend proxy Python para Google Places API
  - .claude/      -> Configuração do servidor de dev (launch.json)

Para rodar:
  cd "LARA PROJECT CODING/backup-v1-stable"
  python3 server.py
  Acesse http://localhost:8080

Firebase Config:
  - apiKey: AIzaSyCzdhnOZw0P95391IzXUZ7L-X_u-V3xofQ
  - Projeto: lara-prospector
  - Admin: thomas98macedo@gmail.com

Funcionalidades ativas:
  - Auth: login email/senha, registro, Google OAuth
  - Busca: Google Places Text Search + Details (via proxy)
  - Tabela: paginada, 20/página, estrelas, status, telefone
  - Export: CSV com BOM UTF-8
  - Admin: KPIs, top nichos/cidades, histórico (Firestore)
