import os
import shutil

from kivy.app import App
from kivy.core.window import Window
from kivy.utils import platform
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.graphics import Color, RoundedRectangle

import db
from main import POINTS, import_from_json, route_info

RUNNERS = ["Anna", "Ádám", "Balázs", "Zoli"]
PLACEHOLDER = "-- válassz --"

BG          = (0.07, 0.08, 0.13, 1)
CARD        = (0.12, 0.14, 0.22, 1)
BLUE        = (0.18, 0.46, 0.95, 1)
BLUE_DIM    = (0.13, 0.33, 0.70, 1)
GRAY        = (0.22, 0.24, 0.32, 1)
GRAY_DIM    = (0.17, 0.19, 0.26, 1)
RED_SOFT    = (0.85, 0.25, 0.25, 1)
YELLOW      = (0.97, 0.78, 0.08, 1)
YELLOW_DIM  = (0.78, 0.60, 0.04, 1)
WHITE       = (1, 1, 1, 1)
WHITE_DIM   = (0.70, 0.74, 0.84, 1)
DARK        = (0.08, 0.08, 0.12, 1)


def _card(widget, color=CARD, radius=10):
    with widget.canvas.before:
        Color(*color)
        rect = RoundedRectangle(pos=widget.pos, size=widget.size, radius=[radius])
    widget.bind(pos=lambda *_: setattr(rect, "pos", widget.pos))
    widget.bind(size=lambda *_: setattr(rect, "size", widget.size))


def _section_label(text):
    lbl = Label(
        text=text, size_hint_y=None, height=26, font_size="12sp",
        halign="left", valign="middle", color=WHITE_DIM,
    )
    lbl.bind(size=lambda *_: setattr(lbl, "text_size", (lbl.width, None)))
    return lbl


def _result_label():
    lbl = Label(
        text="", size_hint_y=None, markup=True,
        halign="left", valign="top", color=WHITE, font_size="15sp",
        padding=(0, 8),
    )
    lbl.bind(width=lambda *_: setattr(lbl, "text_size", (lbl.width, None)))
    lbl.bind(texture_size=lambda *_: setattr(lbl, "height", lbl.texture_size[1] + 8))
    return lbl


def _spinner(values, text=None):
    sp = Spinner(
        text=text or values[0],
        values=values,
        size_hint_y=None, height=50,
        font_size="15sp",
        color=WHITE,
        background_normal="",
        background_down="",
    )
    _update_spinner_color(sp, sp.text)
    sp.bind(text=lambda inst, val: _update_spinner_color(inst, val))
    return sp


def _update_spinner_color(sp, text):
    sp.background_color = GRAY if text == PLACEHOLDER else BLUE


def _button(text, color, active_color, text_color=WHITE, radius=0):
    btn = Button(
        text=text, size_hint_y=None, height=54,
        font_size="16sp", bold=True, color=text_color,
        background_normal="", background_down="",
        background_color=color if radius == 0 else (0, 0, 0, 0),
    )
    if radius:
        with btn.canvas.before:
            bg = Color(*color)
            rect = RoundedRectangle(pos=btn.pos, size=btn.size, radius=[radius])
        btn.bind(pos=lambda *_: setattr(rect, "pos", btn.pos))
        btn.bind(size=lambda *_: setattr(rect, "size", btn.size))
        btn.bind(on_press=lambda *_: setattr(bg, "rgba", active_color))
        btn.bind(on_release=lambda *_: setattr(bg, "rgba", color))
    else:
        btn.bind(on_press=lambda *_: setattr(btn, "background_color", active_color))
        btn.bind(on_release=lambda *_: setattr(btn, "background_color", color))
    return btn


def _divider():
    d = Label(size_hint_y=None, height=1)
    with d.canvas.before:
        Color(0.2, 0.22, 0.32, 1)
        RoundedRectangle(pos=d.pos, size=d.size)
    d.bind(pos=lambda *_: None, size=lambda *_: None)
    return d


class GulyaturmixApp(App):
    def build(self):
        Window.clearcolor = BG
        self._init_data()

        scroll = ScrollView()
        root = BoxLayout(orientation="vertical", padding=[14, 18, 14, 14],
                         spacing=12, size_hint_y=None)
        root.bind(minimum_height=root.setter("height"))

        # Cím
        title = Label(
            text="Gulyaturmix", font_size="24sp", bold=True,
            color=WHITE, size_hint_y=None, height=46,
            halign="center",
        )
        title.bind(size=lambda *_: setattr(title, "text_size", (title.width, None)))
        root.add_widget(title)

        # --- Form kártya ---
        form = BoxLayout(orientation="vertical", padding=14, spacing=10,
                         size_hint_y=None)
        form.bind(minimum_height=form.setter("height"))
        _card(form)

        form.add_widget(_section_label("Ide megyek / Itt vagyok"))
        current = db.get_current_point()
        self.from_sp = _spinner([PLACEHOLDER] + list(POINTS.keys()), text=current)
        self.from_sp.bind(text=self._on_from_changed)
        form.add_widget(self.from_sp)

        form.add_widget(_section_label("Következő - Állítsd be ha a fentihez értél!"))
        self.to_sp = _spinner(self._destinations(current))
        form.add_widget(self.to_sp)

        form.add_widget(_section_label("Futó - Váltásnál állítsd át!"))
        self.runner_sp = _spinner([PLACEHOLDER] + RUNNERS)
        form.add_widget(self.runner_sp)

        root.add_widget(form)

        go_btn = _button("Lássuk", YELLOW, YELLOW_DIM, text_color=DARK, radius=14)
        go_btn.bind(on_press=self._on_submit)
        root.add_widget(go_btn)

        # --- Eredmény ---
        self.result_lbl = _result_label()
        root.add_widget(self.result_lbl)

        # --- Napló kártya ---
        self.log_box = BoxLayout(orientation="vertical", padding=14, spacing=6,
                                 size_hint_y=None)
        self.log_box.bind(minimum_height=self.log_box.setter("height"))
        _card(self.log_box)
        root.add_widget(self.log_box)

        # Reset
        reset_btn = _button("Reset", RED_SOFT, (0.65, 0.15, 0.15, 1), radius=14)
        reset_btn.bind(on_press=self._on_reset)
        root.add_widget(reset_btn)

        scroll.add_widget(root)
        self._refresh_visited()
        return scroll

    # ------------------------------------------------------------------

    def _init_data(self):
        if platform == "android":
            data_dir = self.user_data_dir
            db.DB_PATH = os.path.join(data_dir, "routes.db")
            db.init_db()
            with db.get_connection() as conn:
                count = conn.execute("SELECT COUNT(*) FROM routes").fetchone()[0]
            if count == 0:
                src = os.path.join(os.path.dirname(__file__), "routes.json")
                dst = os.path.join(data_dir, "routes.json")
                if os.path.exists(src):
                    shutil.copy(src, dst)
                import_from_json(dst)
        else:
            db.init_db()
            with db.get_connection() as conn:
                count = conn.execute("SELECT COUNT(*) FROM routes").fetchone()[0]
            if count == 0:
                src = os.path.join(os.path.dirname(__file__), "routes.json")
                if os.path.exists(src):
                    import_from_json(src)

    def _destinations(self, from_point):
        dests = db.get_available_destinations(from_point)
        return [PLACEHOLDER] + dests if dests else [PLACEHOLDER]

    def _on_from_changed(self, _, text):
        opts = self._destinations(text)
        self.to_sp.values = opts
        self.to_sp.text = opts[0]

    def _on_submit(self, _):
        a = self.from_sp.text
        b = self.to_sp.text
        runner = self.runner_sp.text

        if PLACEHOLDER in (a, b):
            self._set_result("[color=ff5555]Válassz pontot![/color]")
            return
        if a == b:
            self._set_result("[color=ff5555]A két pont nem lehet ugyanaz.[/color]")
            return

        runner_val = runner if runner != PLACEHOLDER else None
        db.record_visit(a, b, runner_val)
        fresh = db.load_results()
        info = route_info(a, b, fresh)

        if info is None:
            self._set_result(f"[color=ff5555]Nem található útvonal: {a} → {b}[/color]")
            return

        avg_line = (
            f"[color=aabbff]Átlag még innen:[/color]  [b]{b} - {info['b_avg_km']} km[/b]\n"
            if info["b_avg_km"] is not None else ""
        )
        self._set_result(
            f"[b]{a} -> {b}:[/b]  {info['a_to_b_km']} km\n"
            f"[color=aabbff]Legtávolabb innen:[/color]  "
            f"[b]{b} -> {info['b_farthest_name']}[/b]  {info['b_farthest_km']} km\n"
            f"{avg_line}"
            f"[color=aabbff]Összesen max:[/color]  [b]{info['total_km']} km[/b]"
        )

        self.from_sp.text = b
        self._refresh_visited()

        if info["b_farthest_name"] == "Csemetekert":
            self._set_result(
                self.result_lbl.text
                + "\n[color=ff5555][b]Vége! Nincs több elérhető pont.[/b][/color]"
            )

    def _on_reset(self, _):
        db.clear_routes()
        db.init_db()
        if platform == "android":
            json_path = os.path.join(self.user_data_dir, "routes.json")
        else:
            json_path = os.path.join(os.path.dirname(__file__), "routes.json")
        import_from_json(json_path)
        current = db.get_current_point()
        self.from_sp.text = current
        self._on_from_changed(None, current)
        self._set_result("")
        self._refresh_visited()

    def _set_result(self, text):
        self.result_lbl.text = text

    def _refresh_visited(self):
        self.log_box.clear_widgets()
        visited = db.get_visited_route()
        if not visited:
            return

        header = Label(
            text="Eddig megtett út", font_size="13sp", bold=True,
            color=WHITE_DIM, size_hint_y=None, height=24, halign="left",
        )
        header.bind(size=lambda *_: setattr(header, "text_size", (header.width, None)))
        self.log_box.add_widget(header)

        runner_totals: dict[str, float] = {}
        for i, r in enumerate(visited, 1):
            runner_str = f"  [color=aabbff]{r['runner']}[/color]" if r.get("runner") else ""
            color = "ff7777" if r.get("faraway") == "F" else ("77aaff" if r.get("faraway") == "N" else "ffffff")
            row = Label(
                text=f"[color={color}]{i}. {r['name']}[/color]"
                     f"  [b]{r['distance_km']} km[/b]{runner_str}",
                markup=True, size_hint_y=None, font_size="14sp",
                halign="left", valign="middle", color=WHITE,
            )
            row.bind(size=lambda inst, _: setattr(inst, "text_size", (inst.width, None)))
            row.bind(texture_size=lambda inst, _: setattr(inst, "height", inst.texture_size[1] + 2))
            self.log_box.add_widget(row)

            if r.get("runner"):
                runner_totals[r["runner"]] = round(
                    runner_totals.get(r["runner"], 0.0) + r["distance_km"], 2
                )

        total = round(sum(r["distance_km"] for r in visited), 2)
        self.log_box.add_widget(_divider())
        total_lbl = Label(
            text=f"[b]Összesen: {total} km[/b]", markup=True,
            size_hint_y=None, height=30, font_size="15sp",
            halign="left", color=WHITE,
        )
        total_lbl.bind(size=lambda *_: setattr(total_lbl, "text_size", (total_lbl.width, None)))
        self.log_box.add_widget(total_lbl)

        if runner_totals:
            self.log_box.add_widget(_divider())
            rt_header = Label(
                text="Futók összesítője", font_size="13sp", bold=True,
                color=WHITE_DIM, size_hint_y=None, height=24, halign="left",
            )
            rt_header.bind(size=lambda *_: setattr(rt_header, "text_size", (rt_header.width, None)))
            self.log_box.add_widget(rt_header)
            for name, km in runner_totals.items():
                r_lbl = Label(
                    text=f"[color=aabbff]{name}[/color]  [b]{km} km[/b]",
                    markup=True, size_hint_y=None, height=26, font_size="14sp",
                    halign="left", color=WHITE,
                )
                r_lbl.bind(size=lambda inst, _: setattr(inst, "text_size", (inst.width, None)))
                self.log_box.add_widget(r_lbl)


if __name__ == "__main__":
    GulyaturmixApp().run()