import json
import os

from flask import Flask, render_template, request

from main import POINTS, route_info

app = Flask(__name__)

_BASE = os.path.dirname(os.path.abspath(__file__))

try:
    with open(os.path.join(_BASE, "routes.json"), encoding="utf-8") as f:
        results = json.load(f)
except FileNotFoundError:
    results = {}


@app.route("/")
def index():
    a = request.args.get("a", "")
    b = request.args.get("b", "")

    info = None
    error = None

    # TODO ahová most megyek illetve ahol már volt a csapat, az ne legyen benne

    if a and b:
        if a == b:
            error = "A két pont nem lehet ugyanaz."
        elif not results:
            error = "A routes.json nem található — futtasd először a data_from_mapy() függvényt."
        else:
            info = route_info(a, b, results)
            if info is None:
                error = f"Nem található útvonal: {a} → {b}"

    return render_template(
        "index.html",
        points=list(POINTS.keys()),
        a=a,
        b=b,
        info=info,
        error=error,
    )


if __name__ == "__main__":
    app.run(debug=True)