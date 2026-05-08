import json
from itertools import combinations, permutations
from unittest.mock import MagicMock, patch

import pytest

import main

DUMMY_RESPONSE = {
    "route": {
        "length": 4823,
        "duration": 3465,
        "routePoints": [
            {
                "originalPosition": [
                    18.845393657684326,
                    47.64045365870486
                ],
                "mappedPosition": [
                    18.845397,
                    47.6404523
                ],
                "snapDistance": 0,
                "restricted": "false",
                "restrictionType": "null"
            },
            {
                "originalPosition": [
                    18.803897202014927,
                    47.660472301017535
                ],
                "mappedPosition": [
                    18.8039038,
                    47.6604707
                ],
                "snapDistance": 0,
                "restricted": "false",
                "restrictionType": "null"
            }
        ]
    }
}

EXPECTED_PAIRS = [f"{a}_{b}" for a, b in permutations(main.POINTS.keys(), 2)]
EXPECTED_COUNT = len(EXPECTED_PAIRS)
EXPECTED_API_CALLS = len(list(combinations(main.POINTS.keys(), 2)))


def _mock_get(data):
    m = MagicMock()
    m.json.return_value = data
    m.raise_for_status.return_value = None
    return m


@patch("main.requests.get")
def test_plan_route_returns_correct_data(mock_get):
    mock_get.return_value = _mock_get(DUMMY_RESPONSE)

    result = main.plan_route(main.POINTS["Kisgulya"], main.POINTS["Fenyősor"])

    assert result["route"]["length"] == 4823
    mock_get.assert_called_once()


@patch("main.time.sleep")
@patch("main.requests.get")
def test_all_pairs_mocked(mock_get, mock_sleep, tmp_path, capsys, monkeypatch):
    mock_get.return_value = _mock_get(DUMMY_RESPONSE)
    monkeypatch.chdir(tmp_path)

    main.main()

    out = capsys.readouterr().out
    print(f"\n--- Konzol kimenet ({EXPECTED_COUNT} tárolt útvonal, {EXPECTED_API_CALLS} API hívás) ---")
    print(out)
    print("-------------------------------------------")

    assert mock_get.call_count == EXPECTED_API_CALLS

    routes_file = tmp_path / "routes.json"
    assert routes_file.exists()

    saved = json.loads(routes_file.read_text(encoding="utf-8"))

    assert len(saved) == EXPECTED_COUNT

    for key in EXPECTED_PAIRS:
        assert key in saved, f"Hiányzó útvonal: {key}"
        assert saved[key]["distance_km"] == pytest.approx(4.823, abs=0.001)


def test_farthest_from():
    results = {
        "A_B": {"from": "A", "to": "B", "distance_km": 2.5, "status": "L"},
        "A_C": {"from": "A", "to": "C", "distance_km": 7.1, "status": "L"},
        "A_D": {"from": "A", "to": "D", "distance_km": 3.0, "status": "L"},
        "B_A": {"from": "B", "to": "A", "distance_km": 2.5, "status": "L"},
    }
    result = main.farthest_from("A", results)
    assert result["to"] == "C"
    assert result["distance_km"] == 7.1


def test_farthest_from_ignores_non_L_status():
    results = {
        "A_B": {"from": "A", "to": "B", "distance_km": 2.5, "status": "L"},
        "A_C": {"from": "A", "to": "C", "distance_km": 7.1, "status": "V"},
        "A_D": {"from": "A", "to": "D", "distance_km": 3.0, "status": "N"},
    }
    result = main.farthest_from("A", results)
    assert result["to"] == "B"


def test_farthest_from_fallback_to_csemetekert():
    results = {
        "A_B": {"from": "A", "to": "B", "distance_km": 2.5, "status": "V"},
        "A_Csemetekert": {"from": "A", "to": "Csemetekert", "distance_km": 1.0, "status": "N"},
    }
    result = main.farthest_from("A", results)
    assert result["to"] == "Csemetekert"


def test_farthest_from_ignores_errors():
    results = {
        "A_B": {"from": "A", "to": "B", "distance_km": 2.5, "status": "L"},
        "A_C": {"from": "A", "to": "C", "error": "HTTP 500", "status": "L"},
    }
    result = main.farthest_from("A", results)
    assert result["to"] == "B"


def test_farthest_from_unknown_name():
    assert main.farthest_from("Nincs ilyen", {}) is None


def test_route_info():
    results = {
        "A_B": {"from": "A", "to": "B", "distance_km": 3.0, "status": "L"},
        "B_A": {"from": "B", "to": "A", "distance_km": 3.0, "status": "L"},
        "B_C": {"from": "B", "to": "C", "distance_km": 8.5, "status": "L"},
        "B_D": {"from": "B", "to": "D", "distance_km": 5.0, "status": "L"},
    }
    info = main.route_info("A", "B", results)
    assert info["a_to_b_km"] == 3.0
    assert info["b_farthest_name"] == "C"
    assert info["b_farthest_km"] == 8.5


def test_route_info_missing_pair():
    assert main.route_info("X", "Y", {}) is None


def test_route_info_error_pair():
    results = {"A_B": {"from": "A", "to": "B", "error": "HTTP 404"}}
    assert main.route_info("A", "B", results) is None


@patch("main.time.sleep")
@patch("main.requests.get")
def test_data_from_mapy(mock_get, mock_sleep, tmp_path, capsys, monkeypatch):
    mock_get.return_value = _mock_get(DUMMY_RESPONSE)
    monkeypatch.chdir(tmp_path)

    main.data_from_mapy()

    assert mock_get.call_count == len(main.POINTS) * (len(main.POINTS) - 1) / 2

    routes_file = tmp_path / "routes.json"
    assert routes_file.exists()

    saved = json.loads(routes_file.read_text(encoding="utf-8"))

    assert "Margit utca_Kisgulya" in saved
    assert "Kisgulya_Margit utca" in saved
    assert saved["Margit utca_Kisgulya"]["distance_km"] == pytest.approx(4.823, abs=0.001)
    assert saved["Margit utca_Kisgulya"]["from"] == "Margit utca"
    assert saved["Kisgulya_Margit utca"]["from"] == "Kisgulya"