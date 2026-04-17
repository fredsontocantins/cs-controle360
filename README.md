# CS controle (homologação + customização)

This lightweight Python helper ingests the provided Excel workbooks and normalizes the information so the Customer Success team can base a version/homologação/customização control system on a single JSON snapshot.

## What it knows

- `Controle de Homologação.xlsx` is parsed by skipping the layout rows and keeping the current version status, homologação/prodution versions, and the monthly version columns (`Versão JAN/2026`, `Versão FEV/2026`, etc.).
- `modelo Customização.xlsx` feeds all four tabs (`Em Elaboração`, `Em Aprovação`, `Aprovadas` e `Propostas Aprovadas SC`). The loader trims the repeated headers, drops the Google Sheets `QUERY` totals, and exposes every proposal with a normalized schema (proposal number, cliente, módulo, responsáveis, valores, links, etapa).

## Installation

```bash
python3 -m pip install -r requirements.txt
```

## Docker

Há um `Dockerfile` + `docker-compose.yml` na raiz que empacotam a aplicação web
com persistência do SQLite e dos PDFs enviados em volumes nomeados.

```bash
# copie o template e ajuste senhas / secret em produção
cp .env.example .env

# build + start em segundo plano
docker compose up -d --build

# logs e saúde
docker compose logs -f app
```

A API responde em `http://localhost:8000` (login padrão `admin` / `admin`). Os
dados vivem em `cs_data` (SQLite) e os uploads em `cs_uploads`. Para encerrar:

```bash
docker compose down        # sem remover os volumes
docker compose down -v     # remove o banco e os uploads também
```

## Usage

The entry point is `cs_control.cli`. The two most useful commands are:

```bash
# print a quick overview for the CS squad
python3 -m cs_control.cli summary

# materialize a JSON file that downstream services (dashboards, automations) can import
python3 -m cs_control.cli export --output data/control_snapshot.json
```

Both commands accept `--homologacao-file` and `--customization-file` if your Excel files move. The exported snapshot looks like:

```json
{
  "built_at": "2026-03-27T00:00:00Z",
  "sources": {
    "homologation": "/home/casa/Downloads/homologacao/Controle de Homologação.xlsx",
    "customization": "/home/casa/Downloads/homologacao/modelo Customização.xlsx"
  },
  "homologation": [
    {
      "status": "Em Andamento",
      "module": "Catálogo",
      "latest_version": "3.45.0",
      "homologation_version": "3.45.0",
      "production_version": "3.17.0",
      "homologated": "Não",
      "applied": "Pendente",
      "monthly_versions": {
        "JAN/2026": null,
        "MAR/2026": "3.17.0"
      }
    }
  ],
  "customizations": [
    {
      "stage": "em_elaboracao",
      "proposal": "008/2025",
      "subject": "Abaixo, listo os itens ...",
      "client": "SC",
      "module": "Pat. Mobiliário",
      "owner": "Rosiel L. Vital",
      "links": {
        "proposal_link": null,
        "proposal_file": null
      }
    }
  ]
}
```

You can load this JSON into a dashboard, a log, or any CS tooling to keep real‐time control over version rollouts, homologações e customizações.

Para facilitar o uso do painel, `cs_web` já carrega um snapshot pronto (`cs_web/data/initial_snapshot.json`) com homologações, customizações, releases, módulos e clientes de exemplo. Substitua esse arquivo pelo JSON gerado pela CLI se quiser importar os dados mais recentes das planilhas, mas também é possível manter o histórico apenas manipulando os registros pela interface web.

## Next steps

1. Automate the CLI on every spreadsheet refresh so the JSON stays up to date (cron + `cs_control.cli export`).
2. Point your dashboard or operational runbook at `data/control_snapshot.json`; the normalized schema makes it easy to filter by stage, status, or module.
3. If more customers or tabs appear, add a new entry in `CUSTOMIZATION_STAGE_SPECS` within `cs_control/loader.py`.

## Web console & CRUD

`cs_web.main` runs FastAPI, exposes REST endpoints, and serves both the public dashboard and an admin interface. Start it with:

```bash
uvicorn cs_web.main:app --reload
```

### Autenticação

A partir da versão atual o console exige login. Por padrão o primeiro boot cria um
usuário `admin` / `admin` (sobrescreva com `CS_ADMIN_USERNAME` e `CS_ADMIN_PASSWORD`).
A sessão é armazenada em um cookie httpOnly assinado (`cs_session`); defina
`CS_SESSION_SECRET` em produção. Papéis suportados:

| Papel   | Pode                                               |
|---------|----------------------------------------------------|
| admin   | Tudo: gerenciar e exportar, acessar `/admin`       |
| viewer  | Somente leitura (dashboard e páginas por entidade) |

### Dashboard e páginas por entidade

Visit `http://127.0.0.1:8000/` to see the dashboard built from the SQLite store (initially seeded from the bundled snapshot). The page displays homologação cards, pipeline summaries, a table that highlights both the requested and the actual production dates for each rollout, charts por módulo/cliente, and release cards that show when a release applies plus links to PDFs.

Além do dashboard há páginas dedicadas por entidade (acessíveis a qualquer usuário logado):

- `/homologations` — tabela com busca textual + filtro por homologado (Sim/Não) e paginação.
- `/customizations` — funil + tabela com busca e filtro por etapa.
- `/releases` — cards ordenáveis com busca textual.
- `/modules` — catálogo em grid.
- `/clients` — tabela com busca.

Todas as páginas aceitam `?q=...&page=N` e mostram 20 registros por página.

### Admin console

Go to `http://127.0.0.1:8000/admin` to add new homologações/customizações, editar ou apagar dados, cadastrar módulos e clientes, e exportar os registros de homologação, customização e release. O painel exibe botões para gerar planilhas (XLSX), PDF resumido ou o JSON completo via `/admin/export`, e utiliza o snapshot em `cs_web/data/initial_snapshot.json` como ponto de partida para os dados carregados.

As customizações agora aceitam uploads de PDF (igual aos releases) em vez daquela textarea de links JSON, e o painel adiciona botões de visualização sempre que um documento estiver anexado.

### API

CRUD endpoints expose the same data:

- `POST /api/homologation` / `PUT /api/homologation/{id}` / `DELETE /api/homologation/{id}`
- `POST /api/customizations` / `PUT /api/customizations/{id}` / `DELETE /api/customizations/{id}`
- `GET /api/homologation`, `GET /api/customizations`, `GET /api/snapshot`

Supply the token via the `X-API-Key` header or `?api_key=` query string to mutate data.
# cs-controle360
