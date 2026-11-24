def test_health_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json == {"status": "ok"}
    assert response.headers["Cache-Control"] == "no-store"


def test_health_503_when_db_fails(app, client, tmp_path):
    # Point DATABASE_PATH at a directory: sqlite3 cannot open it as a db file.
    app.config["DATABASE_PATH"] = str(tmp_path)
    response = client.get("/health")
    assert response.status_code == 503
    assert response.json == {"status": "error"}
