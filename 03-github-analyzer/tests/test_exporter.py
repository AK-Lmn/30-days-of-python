import json
from datetime import datetime, timezone
from pathlib import Path

from github_analyzer.exporter import (
    export_repo_to_json,
    export_repo_to_markdown,
    export_user_to_json,
    export_user_to_markdown,
    save_export_file,
)
from github_analyzer.models import (
    CommitAnalytics,
    ContributorItem,
    LanguageBreakdown,
    LanguageShare,
    RepoAnalysis,
    RepoHealthCheck,
    RepositoryItem,
    UserAnalysis,
    UserProfile,
)


def create_sample_user_analysis() -> UserAnalysis:
    now = datetime(2026, 9, 14, 12, 0, 0, tzinfo=timezone.utc)
    u = UserProfile(
        login="octocat",
        name="The Octocat",
        bio="GitHub mascot",
        company="@github",
        location="San Francisco",
        blog="https://github.blog",
        email=None,
        public_repos=5,
        public_gists=2,
        followers=2500,
        following=10,
        created_at=now,
        updated_at=now,
        html_url="https://github.com/octocat",
        avatar_url="https://avatars.githubusercontent.com/u/583231",
    )
    langs = LanguageBreakdown(
        total_bytes=1000,
        languages=[LanguageShare(name="Ruby", bytes_count=1000, percentage=100.0)],
    )
    repo = RepositoryItem(
        id=1,
        name="Spoon-Knife",
        full_name="octocat/Spoon-Knife",
        description="This repo is for spooning-and-knifing.",
        is_fork=False,
        is_private=False,
        is_archived=False,
        html_url="https://github.com/octocat/Spoon-Knife",
        stars=12000,
        forks=14000,
        watchers=12000,
        open_issues=10,
        default_branch="main",
        language="Ruby",
        license_name="MIT",
        size_kb=100,
        created_at=now,
        updated_at=now,
        pushed_at=now,
    )
    return UserAnalysis(
        user=u,
        total_repositories=5,
        source_repositories_count=4,
        forked_repositories_count=1,
        total_stars=15000,
        total_forks=16000,
        total_watchers=15000,
        languages=langs,
        top_starred_repos=[repo],
    )


def create_sample_repo_analysis() -> RepoAnalysis:
    now = datetime(2026, 9, 14, 12, 0, 0, tzinfo=timezone.utc)
    repo = RepositoryItem(
        id=1296269,
        name="Hello-World",
        full_name="octocat/Hello-World",
        description="My first repo on GitHub!",
        is_fork=False,
        is_private=False,
        is_archived=False,
        html_url="https://github.com/octocat/Hello-World",
        stars=2500,
        forks=2200,
        watchers=2500,
        open_issues=5,
        default_branch="master",
        language="C",
        license_name="MIT",
        size_kb=12,
        created_at=now,
        updated_at=now,
        pushed_at=now,
    )
    langs = LanguageBreakdown(
        total_bytes=500,
        languages=[LanguageShare(name="C", bytes_count=500, percentage=100.0)],
    )
    commits = CommitAnalytics(total_sampled_commits=10)
    contribs = [ContributorItem("octocat", 10, "", "https://github.com/octocat")]
    health = RepoHealthCheck(True, True, True, False, True, 85)
    return RepoAnalysis(repo, langs, commits, health, contribs)


def test_export_user_to_json():
    analysis = create_sample_user_analysis()
    out = export_user_to_json(analysis)
    parsed = json.loads(out)
    assert parsed["user"]["login"] == "octocat"
    assert parsed["total_stars"] == 15000
    assert parsed["languages"]["languages"][0]["name"] == "Ruby"


def test_export_user_to_markdown():
    analysis = create_sample_user_analysis()
    md = export_user_to_markdown(analysis)
    assert "# GitHub Analysis: octocat" in md
    assert "| Total Followers | 2,500 |" in md
    assert "| Ruby | 100.0% |" in md
    assert "[Spoon-Knife](https://github.com/octocat/Spoon-Knife)" in md


def test_export_repo_to_json():
    analysis = create_sample_repo_analysis()
    out = export_repo_to_json(analysis)
    parsed = json.loads(out)
    assert parsed["repository"]["full_name"] == "octocat/Hello-World"
    assert parsed["health"]["health_score"] == 85


def test_export_repo_to_markdown():
    analysis = create_sample_repo_analysis()
    md = export_repo_to_markdown(analysis)
    assert "# Repository Analysis: octocat/Hello-World" in md
    assert "| Stars | 2,500 |" in md
    assert "| C | 100.0% | 500 |" in md
    assert "[octocat](https://github.com/octocat)" in md


def test_save_export_file(tmp_path: Path):
    target = tmp_path / "subdir" / "report.md"
    save_export_file("# Test Output", target)
    assert target.exists()
    assert target.read_text(encoding="utf-8") == "# Test Output"
