from datetime import datetime, timezone
from unittest.mock import MagicMock

from github_analyzer.analyzer import (
    analyze_repo,
    analyze_user,
    calculate_language_breakdown,
    compare_repositories,
    compare_users,
    compute_health_score,
    parse_datetime,
    parse_repository_item,
    parse_user_profile,
)
from github_analyzer.client import GitHubClient
from github_analyzer.models import (
    CommitAnalytics,
    LanguageBreakdown,
    LanguageShare,
    RepoAnalysis,
    RepoHealthCheck,
    RepositoryItem,
    UserAnalysis,
    UserProfile,
)


def test_parse_datetime():
    assert parse_datetime(None) is None
    dt = parse_datetime("2026-09-14T06:30:00Z")
    assert dt is not None
    assert dt.year == 2026
    assert dt.month == 9
    assert dt.day == 14
    assert dt.tzinfo == timezone.utc


def test_parse_user_profile():
    raw = {
        "login": "octocat",
        "name": "The Octocat",
        "bio": "GitHub mascot",
        "public_repos": 8,
        "followers": 500,
        "following": 10,
        "created_at": "2011-01-25T18:44:36Z",
        "updated_at": "2026-01-01T00:00:00Z",
        "html_url": "https://github.com/octocat",
        "avatar_url": "https://avatars.githubusercontent.com/u/583231",
    }
    profile = parse_user_profile(raw)
    assert profile.login == "octocat"
    assert profile.name == "The Octocat"
    assert profile.public_repos == 8
    assert profile.followers == 500


def test_calculate_language_breakdown():
    empty = calculate_language_breakdown({})
    assert empty.total_bytes == 0
    assert empty.languages == []

    raw = {"Python": 75000, "TypeScript": 25000}
    breakdown = calculate_language_breakdown(raw)
    assert breakdown.total_bytes == 100000
    assert len(breakdown.languages) == 2
    assert breakdown.languages[0].name == "Python"
    assert breakdown.languages[0].percentage == 75.0
    assert breakdown.languages[1].name == "TypeScript"
    assert breakdown.languages[1].percentage == 25.0


def test_compute_health_score():
    repo = RepositoryItem(
        id=1,
        name="test-repo",
        full_name="org/test-repo",
        description="A comprehensive library for testing.",
        is_fork=False,
        is_private=False,
        is_archived=False,
        html_url="https://github.com/org/test-repo",
        stars=10,
        forks=2,
        watchers=10,
        open_issues=0,
        default_branch="main",
        language="Python",
        license_name="MIT",
        size_kb=256,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        pushed_at=datetime.now(timezone.utc),
        topics=["testing", "python"],
        has_issues=True,
    )
    health = compute_health_score(repo)
    assert health.has_license is True
    assert health.has_description is True
    assert health.has_topics is True
    assert health.health_score == 100


def test_analyze_user():
    mock_client = MagicMock(spec=GitHubClient)
    mock_client.get_user.return_value = {
        "login": "devperson",
        "name": "Developer Person",
        "public_repos": 2,
        "followers": 50,
        "following": 5,
        "created_at": "2020-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
    }
    mock_client.get_all_user_repos.return_value = [
        {
            "id": 101,
            "name": "cool-project",
            "full_name": "devperson/cool-project",
            "fork": False,
            "stargazers_count": 42,
            "forks_count": 5,
            "watchers_count": 42,
            "open_issues_count": 1,
            "language": "Python",
            "size": 100,
            "created_at": "2021-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
            "pushed_at": "2026-09-01T00:00:00Z",
        },
        {
            "id": 102,
            "name": "forked-repo",
            "full_name": "devperson/forked-repo",
            "fork": True,
            "stargazers_count": 100,
            "forks_count": 50,
            "watchers_count": 100,
            "open_issues_count": 0,
            "language": "JavaScript",
            "size": 200,
            "created_at": "2022-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
            "pushed_at": "2026-08-01T00:00:00Z",
        },
    ]

    analysis = analyze_user(mock_client, "devperson", include_forks=False)
    assert analysis.user.login == "devperson"
    assert analysis.total_repositories == 2
    assert analysis.source_repositories_count == 1
    assert analysis.forked_repositories_count == 1
    assert analysis.total_stars == 42
    assert len(analysis.languages.languages) == 1
    assert analysis.languages.languages[0].name == "Python"


def test_analyze_repo():
    mock_client = MagicMock(spec=GitHubClient)
    mock_client.get_repo.return_value = {
        "id": 201,
        "name": "awesome-lib",
        "full_name": "org/awesome-lib",
        "description": "An awesome library",
        "stargazers_count": 150,
        "forks_count": 25,
        "watchers_count": 150,
        "open_issues_count": 3,
        "default_branch": "main",
        "language": "Python",
        "size": 512,
        "created_at": "2022-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
        "pushed_at": "2026-09-10T12:00:00Z",
        "topics": ["python", "cli"],
        "has_issues": True,
    }
    mock_client.get_repo_languages.return_value = {"Python": 90000, "Shell": 10000}
    mock_client.get_repo_commits.return_value = [
        {
            "sha": "abcdef1234567890",
            "commit": {
                "message": "feat: initial commit",
                "author": {"name": "Alice", "date": "2026-09-10T14:30:00Z"},
            },
            "html_url": "https://github.com/org/awesome-lib/commit/abcdef",
        }
    ]
    mock_client.get_repo_contributors.return_value = [
        {"login": "alice", "contributions": 15, "avatar_url": "", "html_url": ""}
    ]

    analysis = analyze_repo(mock_client, "org", "awesome-lib")
    assert analysis.repository.name == "awesome-lib"
    assert analysis.languages.languages[0].name == "Python"
    assert analysis.languages.languages[0].percentage == 90.0
    assert analysis.commit_analytics.total_sampled_commits == 1
    assert analysis.commit_analytics.top_committers["Alice"] == 1
    assert len(analysis.contributors) == 1


def test_compare_repositories():
    now = datetime.now(timezone.utc)
    r1 = RepositoryItem(
        id=1,
        name="repo-a",
        full_name="user/repo-a",
        description="desc a",
        is_fork=False,
        is_private=False,
        is_archived=False,
        html_url="",
        stars=100,
        forks=20,
        watchers=100,
        open_issues=2,
        default_branch="main",
        language="Python",
        license_name="MIT",
        size_kb=500,
        created_at=now,
        updated_at=now,
        pushed_at=now,
    )
    r2 = RepositoryItem(
        id=2,
        name="repo-b",
        full_name="user/repo-b",
        description="desc b",
        is_fork=False,
        is_private=False,
        is_archived=False,
        html_url="",
        stars=50,
        forks=30,
        watchers=50,
        open_issues=10,
        default_branch="main",
        language="Go",
        license_name="Apache-2.0",
        size_kb=800,
        created_at=now,
        updated_at=now,
        pushed_at=now,
    )

    h1 = RepoHealthCheck(True, True, True, True, True, 90)
    h2 = RepoHealthCheck(True, True, True, True, True, 70)

    analysis1 = RepoAnalysis(r1, LanguageBreakdown(0, []), CommitAnalytics(0), h1, [])
    analysis2 = RepoAnalysis(r2, LanguageBreakdown(0, []), CommitAnalytics(0), h2, [])

    comp = compare_repositories(analysis1, analysis2)
    assert comp.item1_name == "user/repo-a"
    assert comp.item2_name == "user/repo-b"

    stars_metric = next(m for m in comp.metrics if m.name == "Stars")
    assert stars_metric.winner == 1

    forks_metric = next(m for m in comp.metrics if m.name == "Forks")
    assert forks_metric.winner == 2

    issues_metric = next(m for m in comp.metrics if m.name == "Open Issues")
    assert issues_metric.winner == 1


def test_compare_users():
    now = datetime.now(timezone.utc)
    u1 = UserProfile("alice", "Alice", None, None, None, None, None, 10, 0, 200, 10, now, now, "", "")
    u2 = UserProfile("bob", "Bob", None, None, None, None, None, 15, 0, 150, 20, now, now, "", "")

    lb1 = LanguageBreakdown(100, [LanguageShare("Python", 100, 100.0)])
    lb2 = LanguageBreakdown(100, [LanguageShare("Rust", 100, 100.0)])

    ua1 = UserAnalysis(u1, 10, 10, 0, 500, 50, 500, lb1)
    ua2 = UserAnalysis(u2, 15, 12, 3, 300, 80, 300, lb2)

    comp = compare_users(ua1, ua2)
    followers_m = next(m for m in comp.metrics if m.name == "Followers")
    assert followers_m.winner == 1

    stars_m = next(m for m in comp.metrics if m.name == "Total Stars Earned")
    assert stars_m.winner == 1

    forks_m = next(m for m in comp.metrics if m.name == "Total Forks Earned")
    assert forks_m.winner == 2
