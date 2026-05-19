import os
import json
from datetime import datetime, timedelta
from backend.database import get_conn, run_query
from backend.config import TABLE_HOMOLOGACAO, TABLE_CUSTOMIZACAO, TABLE_ATIVIDADE, TABLE_RELEASE, TABLE_REPORT_CYCLE

os.environ["CS_ALLOW_INSECURE_SECRETS"] = "1"

def seed():
    conn = get_conn()
    now = datetime.utcnow()

    # Create an open cycle
    conn.execute(f"""
        INSERT INTO {TABLE_REPORT_CYCLE}
        (scope_type, cycle_number, period_label, status, opened_at, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, ("reports", 1, "Cycle 1", "aberto", now.isoformat(), now.isoformat()))

    # Seed 500 homologacoes
    h_data = []
    for i in range(500):
        h_data.append((
            f"Module {i%10}", i%10, "pendente", (now - timedelta(days=i%30)).isoformat(),
            "Obs", "1.0", "1.0", "1.0", "Sim", "Sim", "Sim", "{}",
            now.isoformat(), now.isoformat(), f"Client {i%20}", i%20, now.isoformat()
        ))

    conn.executemany(f"""
        INSERT INTO {TABLE_HOMOLOGACAO}
        (module, module_id, status, check_date, observation, latest_version, homologation_version,
         production_version, homologated, client_presentation, applied, monthly_versions,
         requested_production_date, production_date, client, client_id, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, h_data)

    # Seed 500 customizacoes
    c_data = []
    for i in range(500):
        c_data.append((
            "Desenvolvimento", f"Prop {i}", f"Subject {i}", f"Client {i%20}", f"Module {i%10}", i%10,
            "Owner", (now - timedelta(days=i%30)).isoformat(), "aberto", 10.0, 1000.0, "Obs", None, i%20, now.isoformat()
        ))

    conn.executemany(f"""
        INSERT INTO {TABLE_CUSTOMIZACAO}
        (stage, proposal, subject, client, module, module_id, owner, received_at, status, pf, value, observations, pdf_path, client_id, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, c_data)

    # Seed 500 activities
    a_data = []
    for i in range(500):
        a_data.append((
            f"Activity {i}", i%20, i%10, "Owner", "Executor", "concluida", "Normal",
            now.isoformat(), "Desc", None, now.isoformat(), now.isoformat(), now.isoformat(),
            1, "Tipo", "Ticket", "Erro", "Resolucao"
        ))

    conn.executemany(f"""
        INSERT INTO {TABLE_ATIVIDADE}
        (title, client_id, module_id, owner, executor, status, priority, due_date, description, pdf_path, created_at, updated_at, completed_at, release_id, tipo, ticket, descricao_erro, resolucao)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, a_data)

    # Seed 100 releases
    r_data = []
    for i in range(100):
        r_data.append((
            f"Module {i%10}", i%10, f"Release {i}", "1.0", now.isoformat(), "Notes", f"Client {i%20}", None, i%20, now.isoformat()
        ))

    conn.executemany(f"""
        INSERT INTO {TABLE_RELEASE}
        (module, module_id, release_name, version, applies_on, notes, client, pdf_path, client_id, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, r_data)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    seed()
