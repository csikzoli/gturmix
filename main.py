import json
import os
import sys
import time
from itertools import combinations

import requests
from dotenv import load_dotenv

import db

load_dotenv()

API_KEY = os.getenv("MAPY_API_KEY")
API_URL = "https://api.mapy.cz/v1/routing/route"

ROUTE_TYPE = "foot_fast"

# Névvel ellátott GPS koordináták: név → (hosszúság, szélesség)
POINTS = {
    "Kisgulya": (18.845393657684326, 47.64045365870486),
    "Száz éves fenyő": (18.84560286998749, 47.643271040313174),
    "Pihenő": (18.840737342834476, 47.64581721536194),
    "Deák Ferenc utca": (18.842561244964603, 47.641364490161884),
    "Jenga": (18.835228085517887, 47.648614431387436),
    "Csemetekert": (18.850302100181583, 47.644830564670364),
    "Szántói utca": (18.853295445442203, 47.63867893751516),
    "Homok nyereg": (18.858128786087036, 47.64169701197495),
    "Fehér hegy": (18.864668011665344, 47.638469292334314),
    "Gázvezeték": (18.86585891246796, 47.631574027316596),
    "Sas szikla": (18.87106239795685, 47.633856885529084),
    "Fenyősor": (18.83635997772217, 47.64331621838276),
    "Csévi utca": (18.82667183876038, 47.64627981439696),
    "Megyehatár": (18.829343318939213, 47.65354352757998),
    "Pilisvörösvár": (18.88837337493897, 47.630534688285714),
    "Pilisjászfalu": (18.799586892127994, 47.660347373232376),
    "Nagy-Somlyó": (18.805493116378788, 47.659227310909),
    "Bányaudvar": (18.803897202014927, 47.660472301017535),
    "Harangvirág út": (18.80046129226685, 47.66441438470421),
    "Tinnyei út": (18.8050988316536, 47.66838764550879),
    "Szőlő sor": (18.80993485450745, 47.67226263819827),
    "Csévi temető": (18.81664037704468, 47.668619587540654),
    "Piliscsév": (18.818582296371464, 47.67365048862443),
    "Lőrinc-nyereg": (18.811367154121402, 47.66163989129076),
    "Ferenc-forrás": (18.81782323122025, 47.65016091922408),
    "Tinnye-hegy": (18.815720379352573, 47.65873592615439),
    "Őr-hegy": (18.881649076938633, 47.6240699914852),
    "Iluska-sztráda": (18.870407938957218, 47.63862467224277),
    "Sólyom-szikla": (18.875528275966648, 47.63202024346056),
    "Kopár-csárda": (18.866440951824192, 47.62207218082063),
    "Gázmáneum": (18.855414390563965, 47.62867648602552),
    "Jenői fasor": (18.885492682456974, 47.63382051768726),
    "Saint-Gobain kilátó": (18.87797445058823, 47.62776509254425),
    "Északkeleti átjáró": (18.86813342571259, 47.6275839302682),
    "Margit utca": (18.88567, 47.628149)
}


def plan_route(start: tuple, end: tuple) -> dict:
    if not API_KEY or API_KEY == "ide_ird_az_api_kulcsodat":
        print("Hiba: Adj meg érvényes MAPY_API_KEY értéket a .env fájlban.")
        sys.exit(1)

    params = {
        "apikey": API_KEY,
        "start": f"{start[0]},{start[1]}",
        "end": f"{end[0]},{end[1]}",
        "routeType": ROUTE_TYPE,
    }

    response = requests.get(API_URL, params=params)
    response.raise_for_status()
    return response.json()


def farthest_from(name: str, results: dict) -> dict | None:
    candidates = [
        entry for entry in results.values()
        if entry.get("from") == name and "error" not in entry and entry.get("status") == "L"
    ]
    if candidates:
        return max(candidates, key=lambda e: e["distance_km"])
    else:
        db.record_visit(name, "Csemetekert")
        return results.get(f"{name}_Csemetekert")


def route_info(a: str, b: str, results: dict) -> dict | None:
    a_to_b = results.get(f"{a}_{b}")
    if a_to_b is None or "error" in a_to_b:
        return None
    farthest = farthest_from(b, results)
    candidates = [
        e for e in results.values()
        if e.get("from") == b and "error" not in e and e.get("status") == "L"
    ]
    b_avg_km = round(sum(e["distance_km"] for e in candidates) / len(candidates), 2) if candidates else None
    dist = a_to_b["distance_km"]
    info = {
        "a_to_b_km": round(dist, 2),
        "b_farthest_name": farthest["to"] if farthest else None,
        "b_farthest_km": round(farthest["distance_km"], 2) if farthest else None,
        "b_avg_km": b_avg_km,
        "total_km": round(dist + farthest["distance_km"] if farthest else 0, 2),
    }
    print(f"{a} → {b}: {info['a_to_b_km']} km")
    if info["b_farthest_name"]:
        print(f"{b} legtávolabb: {info['b_farthest_name']} ({info['b_farthest_km']} km), átlag: {b_avg_km} km")
    return info


def data_from_mapy():
    names = list(POINTS.keys())
    unique_pairs = list(combinations(names, 2))
    # unique_pairs = [("Margit utca", x) for x in names if x != "Margit utca"]
    total = len(names) * (len(names) - 1)

    print(f"Pontok száma: {len(names)}, API hívások: {len(unique_pairs)}, tárolt útvonalak: {total}")
    print(f"Típus: {ROUTE_TYPE}\n")

    results = {}

    for from_name, to_name in unique_pairs:
        fwd_key = f"{from_name}_{to_name}"
        rev_key = f"{to_name}_{from_name}"
        print(f"  {fwd_key} ... ", end="", flush=True)

        try:
            data = plan_route(POINTS[from_name], POINTS[to_name])
            route = data.get("route", data)
            distance_m = route.get("length", 0)
            route_points = route.get("routePoints")

            entry = {
                "distance_km": round(distance_m / 1000, 3),
                "raw": route_points,
            }
            results[fwd_key] = {"from": from_name, "to": to_name, **entry}
            results[rev_key] = {"from": to_name, "to": from_name, **entry}
            print(f"{distance_m / 1000:.2f} km")
        except requests.HTTPError as e:
            print(f"HIBA: {e}")
            results[fwd_key] = {"from": from_name, "to": to_name, "error": str(e)}
            results[rev_key] = {"from": to_name, "to": from_name, "error": str(e)}

        time.sleep(0.2)

    # print(f"eredmény: \n{results}")

    output_file = "routes.json"
    # output_file = "routes-m.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nMind a(z) {len(results)} útvonal mentve: {output_file}")

def import_from_json(json_path: str = "routes.json"):
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    db.init_db()
    count = 0
    for entry in data.values():
        if "error" in entry:
            continue
        rp = entry.get("raw") or []
        from_pos = ",".join(str(c) for c in rp[0]["originalPosition"]) if len(rp) > 0 else None
        to_pos = ",".join(str(c) for c in rp[1]["originalPosition"]) if len(rp) > 1 else None
        db.insert_route_single(entry["from"], entry["to"], entry["distance_km"], from_pos, to_pos)
        count += 1
    print(f"{count} bejegyzés importálva → routes.db")
    db.set_faraway()


def main():
    data_from_mapy()
    with open("routes.json", encoding="utf-8") as f:
        results = json.load(f)
        route_info("Kisgulya", "Fenyősor", results)


if __name__ == "__main__":
    main()