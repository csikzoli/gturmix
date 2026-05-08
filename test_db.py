import pytest
import db


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.db"))
    db.init_db()


def insert(from_p, to_p, dist=1.0, status="L", seq=0):
    with db.get_connection() as conn:
        conn.execute(
            "INSERT INTO routes (name, from_point, to_point, distance_km, status, sequence_number)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (f"{from_p}_{to_p}", from_p, to_p, dist, status, seq),
        )


def get_row(name):
    with db.get_connection() as conn:
        return conn.execute(
            "SELECT status, sequence_number FROM routes WHERE name = ?", (name,)
        ).fetchone()


# --- get_current_point ---

def test_get_current_point_all_zero_returns_csemetekert():
    insert("A", "B", seq=0)
    insert("A", "C", seq=0)
    assert db.get_current_point() == "Csemetekert"


def test_get_current_point_returns_max_from_point():
    insert("A", "B", seq=0)
    insert("Fenyősor", "C", seq=3)
    insert("Kisgulya", "D", seq=1)
    assert db.get_current_point() == "Fenyősor"


def test_get_current_point_empty_db_returns_csemetekert():
    assert db.get_current_point() == "Csemetekert"


# --- get_available_destinations ---

def test_get_available_destinations_returns_only_L_status():
    insert("A", "B", status="L")
    insert("A", "C", status="V")
    insert("A", "D", status="N")
    insert("A", "E", status="L")
    result = db.get_available_destinations("A")
    assert result == ["B", "E"]


def test_get_available_destinations_sorted():
    insert("A", "Zöld", status="L")
    insert("A", "Alma", status="L")
    insert("A", "Közép", status="L")
    result = db.get_available_destinations("A")
    assert result == sorted(result)


def test_get_available_destinations_unknown_point():
    assert db.get_available_destinations("Nincs ilyen") == []


def test_get_available_destinations_ignores_other_from_points():
    insert("A", "B", status="L")
    insert("X", "B", status="L")
    assert db.get_available_destinations("A") == ["B"]
    assert db.get_available_destinations("X") == ["B"]


# --- record_visit ---

def test_record_visit_sets_ab_to_V():
    insert("A", "B")
    db.record_visit("A", "B")
    status, _ = get_row("A_B")
    assert status == "V"


def test_record_visit_increments_sequence_number():
    insert("A", "B", seq=0)
    insert("X", "Y", seq=5)
    db.record_visit("A", "B")
    _, seq = get_row("A_B")
    assert seq == 6


def test_record_visit_sets_ba_to_N():
    insert("A", "B")
    insert("B", "A")
    db.record_visit("A", "B")
    status, _ = get_row("B_A")
    assert status == "N"


def test_record_visit_sets_all_a_related_to_N():
    insert("A", "C")
    insert("A", "D")
    insert("X", "A")
    insert("A", "B")
    db.record_visit("A", "B")
    assert get_row("A_C")[0] == "N"
    assert get_row("A_D")[0] == "N"
    assert get_row("X_A")[0] == "N"


def test_record_visit_does_not_affect_unrelated_records():
    insert("A", "B")
    insert("X", "Y")
    db.record_visit("A", "B")
    status, _ = get_row("X_Y")
    assert status == "L"


# --- clear_routes ---

def test_clear_routes_removes_all_rows():
    insert("A", "B")
    insert("X", "Y")
    db.clear_routes()
    with db.get_connection() as conn:
        count = conn.execute("SELECT COUNT(*) FROM routes").fetchone()[0]
    assert count == 0


def test_clear_routes_on_empty_table():
    db.clear_routes()
    with db.get_connection() as conn:
        count = conn.execute("SELECT COUNT(*) FROM routes").fetchone()[0]
    assert count == 0


def test_clear_routes_without_table_does_not_raise(tmp_path, monkeypatch):
    fresh_db = str(tmp_path / "fresh.db")
    monkeypatch.setattr(db, "DB_PATH", fresh_db)
    db.clear_routes()


# --- get_visited_route ---

def test_get_visited_route_empty():
    assert db.get_visited_route() == []


def test_get_visited_route_excludes_zero_sequence():
    insert("A", "B", seq=0)
    insert("A", "C", seq=0)
    assert db.get_visited_route() == []


def test_get_visited_route_ordered_by_sequence():
    insert("A", "C", dist=3.0, seq=3)
    insert("A", "B", dist=1.5, seq=1)
    insert("A", "D", dist=2.0, seq=2)
    result = db.get_visited_route()
    assert [r["name"] for r in result] == ["A_B", "A_D", "A_C"]


def test_get_visited_route_correct_fields():
    insert("A", "B", dist=4.5, seq=1)
    result = db.get_visited_route()
    assert result[0] == {"name": "A_B", "distance_km": 4.5}


def test_get_visited_route_excludes_unvisited():
    insert("A", "B", dist=1.0, seq=1)
    insert("X", "Y", dist=9.9, seq=0)
    result = db.get_visited_route()
    assert len(result) == 1
    assert result[0]["name"] == "A_B"


# --- set_faraway ---

def get_faraway(name):
    with db.get_connection() as conn:
        return conn.execute(
            "SELECT faraway FROM routes WHERE name = ?", (name,)
        ).fetchone()[0]


def test_set_faraway_sets_F_on_max():
    insert("A", "B", dist=2.0)
    insert("A", "C", dist=7.0)
    insert("A", "D", dist=4.0)
    db.set_faraway()
    assert get_faraway("A_C") == "F"


def test_set_faraway_sets_N_on_min():
    insert("A", "B", dist=2.0)
    insert("A", "C", dist=7.0)
    insert("A", "D", dist=4.0)
    db.set_faraway()
    assert get_faraway("A_B") == "N"


def test_set_faraway_middle_stays_null():
    insert("A", "B", dist=2.0)
    insert("A", "C", dist=7.0)
    insert("A", "D", dist=4.0)
    db.set_faraway()
    assert get_faraway("A_D") is None


def test_set_faraway_per_from_point():
    insert("A", "B", dist=1.0)
    insert("A", "C", dist=5.0)
    insert("X", "Y", dist=3.0)
    insert("X", "Z", dist=9.0)
    db.set_faraway()
    assert get_faraway("A_C") == "F"
    assert get_faraway("A_B") == "N"
    assert get_faraway("X_Z") == "F"
    assert get_faraway("X_Y") == "N"


def test_set_faraway_single_record_gets_N():
    insert("A", "B", dist=5.0)
    db.set_faraway()
    assert get_faraway("A_B") == "N"