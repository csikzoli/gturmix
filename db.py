import json
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "routes.db")


def get_connection() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH)


def init_db():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS routes (
                id                   INTEGER PRIMARY KEY AUTOINCREMENT,
                name                 TEXT    NOT NULL,
                from_point           TEXT    NOT NULL,
                to_point             TEXT    NOT NULL,
                distance_km          REAL    NOT NULL,
                fromOriginalPosition TEXT,
                toOriginalPosition   TEXT,
                sequence_number      INTEGER NOT NULL DEFAULT 0,
                status               TEXT    NOT NULL DEFAULT 'L',
                faraway              TEXT,
                runner               TEXT
            )
        """)
    print(f"db kész")

def insert_route_single(from_point: str, to_point: str, distance_km: float, from_pos: str | None, to_pos: str | None):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO routes (name, from_point, to_point, distance_km, fromOriginalPosition, toOriginalPosition)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (f"{from_point}_{to_point}", from_point, to_point, distance_km, from_pos, to_pos),
        )


def clear_routes():
    with get_connection() as conn:
        conn.execute("DROP TABLE IF EXISTS routes")


def get_current_point() -> str:
    try:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT to_point, MAX(sequence_number) FROM routes"
            ).fetchone()
        if row and row[1]:
            return row[0]
    except Exception:
        pass
    return "Csemetekert"


def get_available_destinations(from_point: str) -> list[str]:
    try:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT to_point FROM routes WHERE from_point = ? AND status = 'L' ORDER BY to_point",
                (from_point,),
            ).fetchall()
        return [row[0] for row in rows]
    except Exception:
        return []


def get_visited_route() -> list[dict]:
    try:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT name, distance_km, faraway, runner FROM routes"
                " WHERE sequence_number > 0 ORDER BY sequence_number",
            ).fetchall()
        return [{"name": row[0], "distance_km": round(row[1], 2), "faraway": row[2], "runner": row[3]} for row in rows]
    except Exception:
        return []


def record_visit(a: str, b: str, runner: str = None):
    with get_connection() as conn:
        if runner is None:
            row = conn.execute(
                "SELECT runner FROM routes"
                " WHERE sequence_number = (SELECT MAX(sequence_number) FROM routes)"
            ).fetchone()
            if row:
                runner = row[0]
        conn.execute(
            "UPDATE routes SET status = 'N' WHERE from_point = ? OR to_point = ?",
            (a, a),
        )
        conn.execute(
            "UPDATE routes SET status = 'V',"
            " sequence_number = (SELECT COALESCE(MAX(sequence_number), 0) + 1 FROM routes),"
            " runner = ?"
            " WHERE name = ?",
            (runner, f"{a}_{b}"),
        )


def set_faraway():
    with get_connection() as conn:
        conn.execute("""
            UPDATE routes SET faraway = 'F'
            WHERE id IN (
                SELECT id FROM routes r1
                WHERE distance_km = (
                    SELECT MAX(distance_km) FROM routes r2
                    WHERE r2.from_point = r1.from_point
                )
            )
        """)
        conn.execute("""
            UPDATE routes SET faraway = 'N'
            WHERE id IN (
                SELECT id FROM routes r1
                WHERE distance_km = (
                    SELECT MIN(distance_km) FROM routes r2
                    WHERE r2.from_point = r1.from_point
                )
            )
        """)


def load_results() -> dict:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT from_point, to_point, distance_km, fromOriginalPosition, toOriginalPosition, sequence_number, status"
            " FROM routes"
        ).fetchall()
    results = {}
    for from_point, to_point, distance_km, from_orig, to_orig, sequence_number, status in rows:
        key = f"{from_point}_{to_point}"
        results[key] = {
            "from": from_point,
            "to": to_point,
            "distance_km": distance_km,
            "fromOriginalPosition": from_orig,
            "toOriginalPosition": to_orig,
            "sequence_number": sequence_number,
            "status": status,
        }
    return results