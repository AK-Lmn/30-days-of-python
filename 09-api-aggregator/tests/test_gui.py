from unittest.mock import patch
from api_aggregator.gui import AggregatorGui


def test_gui_initialization():
    with patch("customtkinter.CTk.mainloop"):
        app = AggregatorGui()
        assert app.current_domain == "news"
        assert app.engine is not None
        app._select_domain("crypto")
        assert app.current_domain == "crypto"
        app._select_domain("weather")
        assert app.current_domain == "weather"
        app.destroy()
