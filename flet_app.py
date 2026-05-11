import os

import flet as ft

import db
from main import POINTS, import_from_json, route_info

RUNNERS = ["Anna", "Ádám", "Balázs", "Zoli"]
PH = "-- válassz --"

BG      = "#121420"
CARD    = "#1E2338"
BLUE    = "#2E75F3"
YELLOW  = "#F7C814"
RED     = "#D94040"
WHITE   = "#FFFFFF"
MUTED   = "#B2BCDB"
DARK    = "#141414"
DIV_CLR = "#2C2F45"


def _app_dir() -> str:
    try:
        return os.path.dirname(os.path.abspath(__file__))
    except Exception:
        return os.getcwd()


def _init_data():
    app_dir = _app_dir()
    db.DB_PATH = os.path.join(app_dir, "routes.db")
    db.clear_routes()
    db.init_db()
    json_path = os.path.join(app_dir, "routes.json")
    if os.path.exists(json_path):
        import_from_json(json_path)


def _dd(label: str, options: list, value: str = None) -> ft.Dropdown:
    return ft.Dropdown(
        label=label,
        options=[ft.dropdown.Option(o) for o in options],
        value=value or options[0],
        color=WHITE,
        bgcolor=CARD,
        border_color=BLUE,
        focused_border_color=BLUE,
        label_style=ft.TextStyle(color=MUTED),
        expand=True,
    )


def main(page: ft.Page):
    page.title = "Gulyaturmix"
    page.bgcolor = BG
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 14
    page.scroll = ft.ScrollMode.AUTO

    _init_data()

    current = db.get_current_point()

    from_dd   = _dd("Ide megyek / Itt vagyok", [PH] + list(POINTS.keys()), value=current)
    to_dd     = _dd("Következő", [PH])
    runner_dd = _dd("Futó", [PH] + RUNNERS)

    result_text = ft.Text("", color=WHITE, size=15, selectable=True)
    log_col = ft.Column([], spacing=4, tight=True)

    def _update_dests(from_pt: str):
        dests = db.get_available_destinations(from_pt)
        opts = [PH] + dests if dests else [PH]
        to_dd.options = [ft.dropdown.Option(d) for d in opts]
        to_dd.value = opts[0]

    _update_dests(current)

    def on_from_change(e):
        _update_dests(e.control.value or PH)
        page.update()

    from_dd.on_change = on_from_change

    def _refresh_log():
        log_col.controls.clear()
        visited = db.get_visited_route()
        if not visited:
            return
        log_col.controls.append(
            ft.Text("Eddig megtett út", size=13, weight=ft.FontWeight.BOLD, color=MUTED)
        )
        runner_totals = {}
        total = 0.0
        for i, r in enumerate(visited, 1):
            nc = "#ff7777" if r.get("faraway") == "F" else ("#77aaff" if r.get("faraway") == "N" else WHITE)
            rn = f"  {r['runner']}" if r.get("runner") else ""
            log_col.controls.append(ft.Row([
                ft.Text(f"{i}. {r['name']}", color=nc, size=14, expand=True),
                ft.Text(f"{r['distance_km']} km", weight=ft.FontWeight.BOLD, size=14, color=WHITE),
                ft.Text(rn, color=BLUE, size=14),
            ]))
            total += r["distance_km"]
            if r.get("runner"):
                runner_totals[r["runner"]] = round(runner_totals.get(r["runner"], 0.0) + r["distance_km"], 2)
        log_col.controls.append(ft.Divider(color=DIV_CLR))
        log_col.controls.append(
            ft.Text(f"Összesen: {round(total, 2)} km", weight=ft.FontWeight.BOLD, size=15, color=WHITE)
        )
        if runner_totals:
            log_col.controls.append(ft.Divider(color=DIV_CLR))
            log_col.controls.append(
                ft.Text("Futók összesítője", size=13, weight=ft.FontWeight.BOLD, color=MUTED)
            )
            for name, km in runner_totals.items():
                log_col.controls.append(ft.Row([
                    ft.Text(name, color=BLUE, size=14, expand=True),
                    ft.Text(f"{km} km", weight=ft.FontWeight.BOLD, size=14, color=WHITE),
                ]))

    def on_submit(e):
        a = from_dd.value or ""
        b = to_dd.value or ""
        runner = runner_dd.value or PH
        if PH in (a, b):
            result_text.value = "Válassz pontot!"
            result_text.color = "#ff5555"
            page.update()
            return
        if a == b:
            result_text.value = "A két pont nem lehet ugyanaz."
            result_text.color = "#ff5555"
            page.update()
            return
        runner_val = runner if runner != PH else None
        db.record_visit(a, b, runner_val)
        fresh = db.load_results()
        info = route_info(a, b, fresh)
        if info is None:
            result_text.value = f"Nem található: {a} → {b}"
            result_text.color = "#ff5555"
            page.update()
            return
        avg_line = f"\nÁtlag még innen: {b} - {info['b_avg_km']} km" if info["b_avg_km"] is not None else ""
        result_text.value = (
            f"{a} → {b}: {info['a_to_b_km']} km\n"
            f"Legtávolabb: {b} → {info['b_farthest_name']} {info['b_farthest_km']} km"
            f"{avg_line}\n"
            f"Összesen max: {info['total_km']} km"
        )
        result_text.color = WHITE
        from_dd.value = b
        _update_dests(b)
        _refresh_log()
        page.update()
        if info["b_farthest_name"] == "Csemetekert":
            result_text.value += "\nVége! Nincs több elérhető pont."
            page.update()

    def on_reset(e):
        db.clear_routes()
        db.init_db()
        json_path = os.path.join(_app_dir(), "routes.json")
        if os.path.exists(json_path):
            import_from_json(json_path)
        pt = db.get_current_point()
        from_dd.value = pt
        _update_dests(pt)
        result_text.value = ""
        _refresh_log()
        page.update()

    _refresh_log()

    page.add(
        ft.Text("Gulyaturmix", size=24, weight=ft.FontWeight.BOLD,
                color=WHITE, text_align=ft.TextAlign.CENTER),
        ft.Container(height=8),
        ft.Container(
            content=ft.Column([from_dd, to_dd, runner_dd], spacing=10),
            bgcolor=CARD, border_radius=12, padding=14,
        ),
        ft.Container(height=8),
        ft.Row([ft.ElevatedButton(
            "Lássuk", on_click=on_submit,
            bgcolor=YELLOW, color=DARK,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=14)),
            height=54, expand=True,
        )]),
        ft.Container(content=result_text, padding=8),
        ft.Container(content=log_col, bgcolor=CARD, border_radius=12, padding=14),
        ft.Container(height=8),
        ft.Row([ft.ElevatedButton(
            "Reset", on_click=on_reset,
            bgcolor=RED, color=WHITE,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=14)),
            height=54, expand=True,
        )]),
        ft.Container(height=20),
    )


if __name__ == "__main__":
    ft.app(target=main)