import pytest

import db
import app as app_module

FAKE_ROUTES = [
    ("Kisgulya",   "Fenyősor",    1.234, "18.845,47.640", "18.836,47.643"),
    ("Fenyősor",   "Kisgulya",    1.234, "18.836,47.643", "18.845,47.640"),
    ("Fenyősor",   "Pihenő",      0.8,   "18.836,47.643", "18.840,47.645"),
    ("Fenyősor",   "Csemetekert", 2.1,   "18.836,47.643", "18.850,47.644"),
]


@pytest.fixture
def client(tmp_path, monkeypatch):
    # a valódi SQLite kódot egy ideiglenes fájlra irányítja
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.db"))

    # valódi tábla létrehozás és sorok beszúrása
    db.init_db()
    for from_p, to_p, dist, from_pos, to_pos in FAKE_ROUTES:
        db.insert_route_single(from_p, to_p, dist, from_pos, to_pos)

    # valódi DB olvasás, az eredmény kerül az app.results-ba
    monkeypatch.setattr(app_module, "results", db.load_results())
    app_module.app.config["TESTING"] = True
    return app_module.app.test_client()


def test_index_no_params(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "Kisgulya".encode() in r.data


def test_index_valid_pair(client):
    r = client.get("/?a=Kisgulya&b=Fenyősor")
    assert r.status_code == 200
    # assert "1.234".encode() in r.data
    # assert "Csemetekert".encode() in r.data


def test_index_same_point_error(client):
    r = client.get("/?a=Kisgulya&b=Kisgulya")
    assert r.status_code == 200
    assert "ugyanaz".encode() in r.data


def test_index_empty_results(client, monkeypatch):
    monkeypatch.setattr(app_module, "results", {})
    r = client.get("/?a=Kisgulya&b=Fenyősor")
    assert r.status_code == 200
    assert "routes".encode() in r.data.lower()


def test_index_unknown_pair(client):
    r = client.get("/?a=Kisgulya&b=Pilisvörösvár")
    assert r.status_code == 200
    assert "Nem található".encode() in r.data