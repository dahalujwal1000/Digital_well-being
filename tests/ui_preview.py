"""Deterministic visual smoke checks; no personal usage data is opened."""
import sys
import tempfile
from pathlib import Path
from datetime import date
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PIL import ImageGrab
from src.dashboard import data_source, mock_data
from src.dashboard.app import DigitalWellbeingApp

with mock.patch.object(data_source, "_real", return_value=None):
    app = DigitalWellbeingApp()
    errors = []
    app.report_callback_exception = lambda *args: errors.append(args)
    app.geometry("1080x780+20+20")
    app.update()
    output = Path(tempfile.gettempdir()) / "digital-wellbeing-ui-preview"
    output.mkdir(exist_ok=True)
    for name in app.pages:
        app._show(name)
        app.update()
        ImageGrab.grab(bbox=(app.winfo_rootx(), app.winfo_rooty(),
                            app.winfo_rootx()+app.winfo_width(),
                            app.winfo_rooty()+app.winfo_height())).save(
                                output / (name.replace(" & ", "-")+".png"))
    for scaling in (1.3333, 1.6667, 2.0):
        app.tk.call("tk", "scaling", scaling)
        app.geometry("780x560")
        for name in app.pages:
            app._show(name)
            app.update()
    empty = mock_data.DayStats(day=date.today())
    app.home_tab.render(empty)
    app.apps_tab.render(empty)
    app.sessions_tab.render(empty)
    app.apps_tab.query.set("missing app")
    app._go_to_date(date.today())
    app.update()
    assert app._selected == "Overview"
    assert not errors, errors
    app.destroy()
    print("UI checks passed. Screenshots:", output)
