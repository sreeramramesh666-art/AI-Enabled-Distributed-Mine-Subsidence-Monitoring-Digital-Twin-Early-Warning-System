from datetime import datetime, timezone, timedelta
from backend.app.services.report_service import sanitize_csv_cell


def test_csv_export(client):
    res = client.get("/api/v1/reports/export?format=csv")
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    assert "displacement_mm" in res.text


def test_csv_export_filters_and_errors(client):
    # CSV for non-existent node returns 404
    assert client.get("/api/v1/reports/export?format=csv&node_id=GHOST-NODE-999").status_code == 404

    now = datetime.now(timezone.utc)
    t_start = (now - timedelta(hours=2)).isoformat()
    t_end = now.isoformat()

    # Valid time range
    res_time = client.get(f"/api/v1/reports/export?format=csv&start_time={t_start}&end_time={t_end}")
    assert res_time.status_code == 200

    # Invalid time range (start > end) returns 400
    bad_time = client.get(f"/api/v1/reports/export?format=csv&start_time={t_end}&end_time={t_start}")
    assert bad_time.status_code == 400


def test_csv_formula_injection_sanitization():
    # Dangerous spreadsheet formula injection characters
    assert sanitize_csv_cell("=1+1") == "'=1+1"
    assert sanitize_csv_cell("+cmd|' /C calc'!A0") == "'+cmd|' /C calc'!A0"
    assert sanitize_csv_cell("-2+3") == "'-2+3"
    assert sanitize_csv_cell("@SUM(1,2)") == "'@SUM(1,2)"
    # Safe values
    assert sanitize_csv_cell("NODE-01") == "NODE-01"
    assert sanitize_csv_cell(12.34) == "12.34"
    assert sanitize_csv_cell(None) == ""


def test_pdf_report_export(client):
    res = client.get("/api/v1/reports/export?format=pdf")
    assert res.status_code == 200
    assert "application/pdf" in res.headers["content-type"]
    assert res.content.startswith(b"%PDF")

    # PDF for non-existent node returns 404
    assert client.get("/api/v1/reports/export?format=pdf&node_id=GHOST-NODE-999").status_code == 404
