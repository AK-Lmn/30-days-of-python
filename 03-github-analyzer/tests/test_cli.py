from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch
from click.testing import CliRunner

from github_analyzer.cli import main
from github_analyzer.models import (
    CommitAnalytics,
    LanguageBreakdown,
    LanguageShare,
    RateLimitStatus,
    RepoAnalysis,
    RepoHealthCheck,
    RepositoryItem,
    UserAnalysis,
    UserProfile,
)


def test_cli_version():
    runner = CliRunner()
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "github-analyzer" in result.output


def test_cli_rate_limit():
    runner = CliRunner()
    mock_status = RateLimitStatus(
        limit=60,
        remaining=55,
        reset_time=datetime(2026, 9, 14, 12, 0, 0, tzinfo=timezone.utc),
        used=5,
    )

    with patch("github_analyzer.client.GitHubClient.get_rate_limit", return_value=mock_status):
        result = runner.invoke(main, ["rate-limit"])
        assert result.exit_code == 0
        assert "GitHub REST API Rate Limit Status" in result.output
        assert "55" in result.output


def test_cli_cache_clear(tmp_path: Path):
    runner = CliRunner()
    with patch("github_analyzer.cli.ResponseCache") as mock_cache_cls:
        mock_instance = MagicMock()
        mock_instance.clear.return_value = 5
        mock_cache_cls.return_value = mock_instance

        result = runner.invoke(main, ["cache", "clear"])
        assert result.exit_code == 0
        assert "Cache cleared successfully" in result.output
        assert "5" in result.output


def test_cli_user_command(tmp_path: Path):
    runner = CliRunner()
    now = datetime(2026, 9, 14, 12, 0, 0, tzinfo=timezone.utc)
    u = UserProfile("testuser", "Test User", "A coder", None, None, None, None, 3, 0, 100, 10, now, now, "", "")
    analysis = UserAnalysis(
        user=u,
        total_repositories=3,
        source_repositories_count=3,
        forked_repositories_count=0,
        total_stars=25,
        total_forks=5,
        total_watchers=25,
        languages=LanguageBreakdown(100, [LanguageShare("Python", 100, 100.0)]),
    )

    export_file = tmp_path / "user_out.md"
    with patch("github_analyzer.cli.analyze_user", return_value=analysis):
        result = runner.invoke(
            main,
            ["user", "testuser", "--export", "md", "--output", str(export_file)],
        )
        assert result.exit_code == 0
        assert "Test User" in result.output
        assert export_file.exists()


def test_cli_repo_command_invalid_format():
    runner = CliRunner()
    result = runner.invoke(main, ["repo", "invalid-repo-without-slash"])
    assert result.exit_code != 0
    assert "owner/repo" in result.output


def test_cli_repo_command(tmp_path: Path):
    runner = CliRunner()
    now = datetime(2026, 9, 14, 12, 0, 0, tzinfo=timezone.utc)
    repo = RepositoryItem(
        id=1,
        name="test-repo",
        full_name="owner/test-repo",
        description="Demo repo",
        is_fork=False,
        is_private=False,
        is_archived=False,
        html_url="",
        stars=10,
        forks=2,
        watchers=10,
        open_issues=0,
        default_branch="main",
        language="Python",
        license_name="MIT",
        size_kb=50,
        created_at=now,
        updated_at=now,
        pushed_at=now,
    )
    analysis = RepoAnalysis(
        repository=repo,
        languages=LanguageBreakdown(100, [LanguageShare("Python", 100, 100.0)]),
        commit_analytics=CommitAnalytics(0),
        contributors=[],
        health=RepoHealthCheck(True, True, True, True, True, 100),
    )

    export_file = tmp_path / "repo_out.json"
    with patch("github_analyzer.cli.analyze_repo", return_value=analysis):
        result = runner.invoke(
            main,
            ["repo", "owner/test-repo", "--export", "json", "--output", str(export_file)],
        )
        assert result.exit_code == 0
        assert "owner/test-repo" in result.output
        assert export_file.exists()


def test_cli_compare_command():
    runner = CliRunner()
    now = datetime(2026, 9, 14, 12, 0, 0, tzinfo=timezone.utc)
    u1 = UserProfile("alice", "Alice", None, None, None, None, None, 1, 0, 10, 5, now, now, "", "")
    u2 = UserProfile("bob", "Bob", None, None, None, None, None, 2, 0, 20, 5, now, now, "", "")
    analysis1 = UserAnalysis(u1, 1, 1, 0, 10, 2, 10, LanguageBreakdown(0, []))
    analysis2 = UserAnalysis(u2, 2, 2, 0, 20, 4, 20, LanguageBreakdown(0, []))

    with patch("github_analyzer.cli.analyze_user", side_effect=[analysis1, analysis2]):
        result = runner.invoke(main, ["compare", "alice", "bob", "--type", "user"])
        assert result.exit_code == 0
        assert "User Comparison" in result.output
        assert "alice" in result.output
        assert "bob" in result.output
