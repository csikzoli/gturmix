import os
import sys

from kivy.app import App
from kivy.uix.label import Label
from kivy.utils import platform


class GulyaturmixApp(App):
    def build(self):
        lines = [
            f"platform: {platform}",
            f"python: {sys.version[:30]}",
            f"cwd: {os.getcwd()}",
        ]
        try:
            import sqlite3
            lines.append("sqlite3: OK")
        except Exception as e:
            lines.append(f"sqlite3: FAIL {e}")
        try:
            import db
            lines.append(f"db: OK")
            lines.append(f"DB_PATH: {db.DB_PATH[-40:]}")
        except Exception as e:
            lines.append(f"db: FAIL {e}")
        try:
            from main import POINTS
            lines.append(f"main/POINTS: OK ({len(POINTS)} pont)")
        except Exception as e:
            lines.append(f"main: FAIL {e}")
        try:
            if platform == "android":
                json_src = os.path.join(os.path.dirname(__file__), "routes.json")
                lines.append(f"routes.json: {'OK' if os.path.exists(json_src) else 'MISSING'}")
                lines.append(f"__file__ dir: {os.path.dirname(__file__)[-40:]}")
        except Exception as e:
            lines.append(f"path check: FAIL {e}")

        return Label(
            text="\n".join(lines),
            halign="left", valign="top",
            font_size="13sp",
        )


if __name__ == "__main__":
    GulyaturmixApp().run()