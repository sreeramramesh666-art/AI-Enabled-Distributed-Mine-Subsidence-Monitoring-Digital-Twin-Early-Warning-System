def test_csv_export(client):
    res = client.get("/api/v1/reports/export?format=csv")
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    assert "displacement_mm" in res.text


def test_pdf_report_export(client):
    res = client.get("/api/v1/reports/export?format=pdf")
    assert res.status_code == 200
    assert "application/pdf" in res.headers["content-type"]
    assert res.content.startswith(b"%PDF")
