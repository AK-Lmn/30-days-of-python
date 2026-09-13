from unittest.mock import patch
from github_analyzer.gui import GitHubAnalyzerApp


def test_gui_initialization():
    with patch.object(GitHubAnalyzerApp, "_refresh_rate_limit_async"):
        app = GitHubAnalyzerApp()
        app.withdraw()
        assert app.title() == "GitHub Analyzer — Desktop Dashboard"
        assert app.tab_user is not None
        assert app.tab_repo is not None
        assert app.tab_compare is not None
        assert app.tab_settings is not None
        app.destroy()
