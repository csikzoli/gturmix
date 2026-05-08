from flask import Flask, redirect, render_template, request, url_for

import db
from main import POINTS, import_from_json, route_info

app = Flask(__name__)

RUNNERS = ["Anna", "Ádám", "Balázs", "Zoli"]

try:
    results = db.load_results()
except Exception:
    results = {}


@app.route("/")
def index():
    a = request.args.get("a") or db.get_current_point()
    b = request.args.get("b", "")
    runner = request.args.get("runner", "")

    info = None
    error = None

    if a and b:
        if a == b:
            error = "A két pont nem lehet ugyanaz."
        elif not results:
            error = "A routes.json nem található — futtasd először a data_from_mapy() függvényt."
        else:
            db.record_visit(a, b, runner or None)
            fresh_results = db.load_results()
            info = route_info(a, b, fresh_results)
            if info is None:
                error = f"Nem található útvonal: {a} → {b}"
            else:
                from_label = a
                a = b

    game_over = info is not None and info["b_farthest_name"] == "Csemetekert"
    visited = db.get_visited_route()
    runner_totals = {}
    for r in visited:
        if r["runner"]:
            runner_totals[r["runner"]] = round(runner_totals.get(r["runner"], 0.0) + r["distance_km"], 2)

    return render_template(
        "index.html",
        runners=RUNNERS,
        runner=runner,
        points=list(POINTS.keys()),
        destinations=db.get_available_destinations(a),
        a=a,
        b=b,
        from_label=locals().get("from_label", a),
        info=info,
        error=error,
        game_over=game_over,
        visited=visited,
        visited_total=round(sum(r["distance_km"] for r in visited), 2),
        runner_totals=runner_totals,
    )


@app.route("/reset", methods=["GET"])
def reset():
    db.clear_routes()
    db.init_db()
    import_from_json()
    global results
    results = db.load_results()
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)