# CS Controle 360

Sistema de controle operacional para CS com foco em homologação, releases, atividades, relatórios gerenciais, inteligência local de PDFs e playbooks preditivos.

## Stack atual

- Backend: FastAPI + SQLite
- Frontend: React + Vite
- Inteligência de PDFs: processamento local e determinístico, sem chamadas externas de IA
- Playbooks: geração manual, por erros, por release e por previsões locais
- Relatórios: texto, HTML e PDF

## Como executar

```bash
./run.sh
```

O script sobe:
- backend em `http://127.0.0.1:8000`
- frontend em `http://127.0.0.1:5173` ou na próxima porta livre

Se quiser subir apenas a API:

```bash
./run-server.sh
```

## Organização

- [backend/](/home/casa/Downloads/homologacao/backend) concentra API, modelos, schemas e serviços
- [frontend/](/home/casa/Downloads/homologacao/frontend) concentra telas, componentes e client HTTP
- [run.sh](/home/casa/Downloads/homologacao/run.sh) sobe backend e frontend juntos
- [run-server.sh](/home/casa/Downloads/homologacao/run-server.sh) sobe apenas o backend

## Fluxos principais

### 1. Homologação, customização, atividade e release

CRUDs operacionais com vínculo entre telas, relatórios e inteligência de PDF.

### 2. PDFs e inteligência local

- Upload múltiplo de PDFs por tela
- Leitura e extração local do conteúdo
- Cache por hash do arquivo
- Reprocessamento apenas quando o PDF muda
- Ciclo de prestação de contas com abertura e fechamento mensal
- Auditoria de documentos lidos, novos, alterados e legados

### 3. Relatórios gerenciais

- Consolidação por módulo, release e ticket
- Exportação em texto, HTML e PDF
- Indicadores executivos, temas recorrentes e previsões locais

### 4. Playbooks inteligentes

- Criação manual
- Geração por erros do mês
- Geração por release
- Geração por previsões da aplicação
- Exportação e fechamento como prestado

## Política de repositório

O repositório usa o novo stack como base ativa. O código legado não faz parte do fluxo em execução.

O `.gitignore` foi reforçado para evitar que o workspace volte a encher de:
- caches Python
- `node_modules`
- `dist`
- bancos SQLite locais
- PDFs gerados
- artefatos temporários

## Desenvolvimento

Instalação do backend:

```bash
python3 -m pip install -r requirements.txt
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Backend:

```bash
uvicorn backend.main:app --reload
```

## Testes

Para rodar os testes do backend:

```bash
export CS_ALLOW_INSECURE_SECRETS=1
export PYTHONPATH=.
python3 -m pytest tests/
```

## Variáveis de ambiente

| Variável | Default | Descrição |
| --- | --- | --- |
| `CS_ADMIN_AUTH_ENABLED` | `1` | Liga autenticação. Desabilitar apenas em dev. |
| `CS_API_KEY` | *(sem default em prod)* | Chave usada como fallback do `CS_AUTH_SECRET`. Obrigatória quando `AUTH_ENABLED=1`. |
| `CS_AUTH_SECRET` | `CS_API_KEY` | Segredo da assinatura de tokens. Defina explicitamente em produção. |
| `CS_AUTH_TOKEN_MAX_AGE_SECONDS` | `604800` | Expiração da sessão em segundos. |
| `CS_ALLOW_INSECURE_SECRETS` | `0` | Autoriza os defaults inseguros (`cs-secret`) apenas em dev local. |
| `CS_CORS_ORIGINS` | `http://localhost:5173,...` | Lista separada por vírgula dos `allow_origins` do CORS em produção. |
| `CS_RESET_SAMPLE_DATA_ON_STARTUP` | `0` | Se `1`, apaga os dados e reaplica a massa demo a cada boot. **Nunca ligue em produção.** |
| `GOOGLE_CLIENT_ID` | `""` | Client ID para o login via Google. |

Em produção, exporte `CS_API_KEY` e `CS_AUTH_SECRET` explicitamente — o backend recusa subir caso os defaults inseguros continuem ativos com autenticação ligada.

## Observação

A inteligência da aplicação é local. O sistema lê os PDFs já incluídos, aprende regras a partir deles e reaproveita esse contexto em relatórios, dashboard e playbooks sem depender de tokens ou chamadas externas.
