import pytest
from backend.services.report_generator import ReportGenerator

def test_new_report_themes():
    generator = ReportGenerator()
    # Test that new themes are detectable
    security_theme = generator._detect_theme("Ajuste de senha e permissão de acesso")
    assert security_theme == "Segurança"

    infra_theme = generator._detect_theme("Timeout no banco de dados e conexão com servidor")
    assert infra_theme == "Infraestrutura"

def test_report_insights_logic():
    generator = ReportGenerator()

    # Mock data for high efficiency
    activities = [
        {"status": "concluida", "tipo": "melhoria", "title": "A"},
        {"status": "concluida", "tipo": "melhoria", "title": "B"},
        {"status": "concluida", "tipo": "melhoria", "title": "C"},
        {"status": "concluida", "tipo": "melhoria", "title": "D"},
    ]

    report = generator._build_management_report(activities)
    insight_titles = [i["title"] for i in report["insights"]]
    assert "Alta Eficiência do Ciclo" in insight_titles

def test_high_risk_module_insight():
    generator = ReportGenerator()

    # Mock data for high risk module (many corrections)
    # The condition is: tickets >= 5 and (corrections / tickets) > 0.6
    activities = [
        {"status": "concluida", "tipo": "correcao_bug", "module": "M1", "title": "1"},
        {"status": "concluida", "tipo": "correcao_bug", "module": "M1", "title": "2"},
        {"status": "concluida", "tipo": "correcao_bug", "module": "M1", "title": "3"},
        {"status": "concluida", "tipo": "correcao_bug", "module": "M1", "title": "4"},
        {"status": "concluida", "tipo": "correcao_bug", "module": "M1", "title": "5"},
    ]

    # We need to make sure modules are properly detected.
    # _build_management_report uses list_modulo() to build the summary.
    # Since we are using real models in the background with a likely empty test DB,
    # we might need to insert the module or just rely on the "Sem módulo" logic if it handles it.
    # Actually, the logic uses all_modules = list_modulo() and then builds module_rows.

    # Let's bypass the full report and test the logic if possible,
    # or ensure a module exists.

    from backend.database import ensure_tables
    from backend.models.modulo import insert_modulo, list_modulo
    ensure_tables()
    if not any(m["name"] == "M1" for m in list_modulo()):
        insert_modulo({"name": "M1", "description": "Desc"})

    report = generator._build_management_report(activities)
    insight_titles = [i["title"] for i in report["insights"]]
    assert "Módulo de Atenção Crítica" in insight_titles
