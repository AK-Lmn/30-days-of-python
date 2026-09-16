from unittest.mock import MagicMock, patch
from api_cli.gui import UniversalApiApp, run_gui


def test_gui_imports_and_structure():
    assert UniversalApiApp is not None
    assert callable(run_gui)


def test_gui_textbox_parsing():
    with patch("customtkinter.CTk.__init__", return_value=None):
        app = UniversalApiApp.__new__(UniversalApiApp)
        pairs = app._parse_textbox_pairs("Authorization: Bearer test\nlimit=20\n# comment\n\ninvalid")
        assert pairs["Authorization"] == "Bearer test"
        assert pairs["limit"] == "20"
