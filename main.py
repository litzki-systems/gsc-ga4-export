"""
GSC + GA4 Export Tool
Entry point: GUI (default) or headless (--headless).

tkinter is imported only on the GUI path, so --headless runs on a server with
no display and no python3-tk installed.
© Litzki Systems LLC
"""
import sys

from config import load_env
from runner import run_headless


def main():
    env = load_env()
    if "--headless" in sys.argv:
        run_headless(env)
    else:
        from gui import launch   # imports tkinter — GUI path only
        launch(env)


if __name__ == "__main__":
    main()
