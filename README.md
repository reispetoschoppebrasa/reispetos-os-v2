# REI'SPETOS OS — Repositório limpo v2

Estrutura correta:

- `backend/` — FastAPI e banco
- `frontend/` — React/Vite
- `docker-compose.yml`
- `render.yaml`

## Publicação

### Vercel
- Root Directory: `frontend`
- Framework: Vite
- Variável:
  - `VITE_API_URL=https://SEU-BACKEND.onrender.com`

### Render
- Root Directory: `backend`
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Variáveis:
  - `PYTHON_VERSION=3.12.11`
  - `SECRET_KEY=<chave gerada>`
  - `FRONTEND_URL=https://SEU-FRONTEND.vercel.app`

## Importante
Não mova arquivos de `backend/` ou `frontend/` para a raiz.
