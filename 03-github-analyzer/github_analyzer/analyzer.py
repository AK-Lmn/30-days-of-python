from collections import Counter
from datetime import datetime, timezone
from typing import Any, Optional

from github_analyzer.client import GitHubClient
from github_analyzer.models import (
    CommitAnalytics,
    CommitItem,
    ComparisonMetric,
    ComparisonResult,
    ContributorItem,
    LanguageBreakdown,
    LanguageShare,
    RepoAnalysis,
    RepoHealthCheck,
    RepositoryItem,
    UserAnalysis,
    UserProfile,
)


def parse_datetime(dt_str: Optional[str]) -> Optional[datetime]:
    if not dt_str:
        return None
    normalized = dt_str.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized)


def parse_user_profile(data: dict[str, Any]) -> UserProfile:
    created_at = parse_datetime(data.get("created_at")) or datetime.now(timezone.utc)
    updated_at = parse_datetime(data.get("updated_at")) or datetime.now(timezone.utc)
    return UserProfile(
        login=data.get("login", ""),
        name=data.get("name"),
        bio=data.get("bio"),
        company=data.get("company"),
        location=data.get("location"),
        blog=data.get("blog"),
        email=data.get("email"),
        public_repos=int(data.get("public_repos", 0)),
        public_gists=int(data.get("public_gists", 0)),
        followers=int(data.get("followers", 0)),
        following=int(data.get("following", 0)),
        created_at=created_at,
        updated_at=updated_at,
        html_url=data.get("html_url", ""),
        avatar_url=data.get("avatar_url", ""),
        is_hireable=bool(data.get("hireable", False)),
    )


def parse_repository_item(data: dict[str, Any]) -> RepositoryItem:
    created_at = parse_datetime(data.get("created_at")) or datetime.now(timezone.utc)
    updated_at = parse_datetime(data.get("updated_at")) or datetime.now(timezone.utc)
    pushed_at = parse_datetime(data.get("pushed_at"))

    license_info = data.get("license")
    license_name = license_info.get("spdx_id") or license_info.get("name") if isinstance(license_info, dict) else None

    return RepositoryItem(
        id=int(data.get("id", 0)),
        name=data.get("name", ""),
        full_name=data.get("full_name", ""),
        description=data.get("description"),
        is_fork=bool(data.get("fork", False)),
        is_private=bool(data.get("private", False)),
        is_archived=bool(data.get("archived", False)),
        html_url=data.get("html_url", ""),
        stars=int(data.get("stargazers_count", 0)),
        forks=int(data.get("forks_count", 0)),
        watchers=int(data.get("watchers_count", 0)),
        open_issues=int(data.get("open_issues_count", 0)),
        default_branch=data.get("default_branch", "main"),
        language=data.get("language"),
        license_name=license_name,
        size_kb=int(data.get("size", 0)),
        created_at=created_at,
        updated_at=updated_at,
        pushed_at=pushed_at,
        topics=list(data.get("topics", [])),
        has_issues=bool(data.get("has_issues", True)),
        has_wiki=bool(data.get("has_wiki", True)),
        has_pages=bool(data.get("has_pages", False)),
    )


def calculate_language_breakdown(languages_raw: dict[str, int]) -> LanguageBreakdown:
    total_bytes = sum(languages_raw.values())
    if total_bytes == 0:
        return LanguageBreakdown(total_bytes=0, languages=[])

    sorted_langs = sorted(languages_raw.items(), key=lambda item: item[1], reverse=True)
    shares = [
        LanguageShare(
            name=name,
            bytes_count=byte_count,
            percentage=round((byte_count / total_bytes) * 100, 2),
        )
        for name, byte_count in sorted_langs
    ]
    return LanguageBreakdown(total_bytes=total_bytes, languages=shares)


def analyze_user(
    client: GitHubClient,
    username: str,
    include_forks: bool = False,
    max_repos: int = 200,
) -> UserAnalysis:
    user_data = client.get_user(username)
    user_profile = parse_user_profile(user_data)

    raw_repos = client.get_all_user_repos(username, max_repos=max_repos)
    all_repo_items = [parse_repository_item(repo) for repo in raw_repos]

    source_repos = [r for r in all_repo_items if not r.is_fork]
    forked_repos = [r for r in all_repo_items if r.is_fork]

    considered_repos = all_repo_items if include_forks else source_repos

    total_stars = sum(r.stars for r in considered_repos)
    total_forks = sum(r.forks for r in considered_repos)
    total_watchers = sum(r.watchers for r in considered_repos)

    language_byte_counts: Counter[str] = Counter()
    for repo in considered_repos:
        if repo.language:
            approx_bytes = max(repo.size_kb * 1024, 1024)
            language_byte_counts[repo.language] += approx_bytes

    languages = calculate_language_breakdown(dict(language_byte_counts))

    top_starred = sorted(considered_repos, key=lambda r: r.stars, reverse=True)[:5]
    top_forked = sorted(considered_repos, key=lambda r: r.forks, reverse=True)[:5]
    pushed_repos = [r for r in considered_repos if r.pushed_at is not None]
    recently_pushed = sorted(pushed_repos, key=lambda r: r.pushed_at, reverse=True)[:5]

    return UserAnalysis(
        user=user_profile,
        total_repositories=len(all_repo_items),
        source_repositories_count=len(source_repos),
        forked_repositories_count=len(forked_repos),
        total_stars=total_stars,
        total_forks=total_forks,
        total_watchers=total_watchers,
        languages=languages,
        top_starred_repos=top_starred,
        top_forked_repos=top_forked,
        recently_pushed_repos=recently_pushed,
    )


def compute_health_score(repo: RepositoryItem) -> RepoHealthCheck:
    score = 0
    has_description = bool(repo.description and len(repo.description.strip()) > 5)
    if has_description:
        score += 20

    has_license = bool(repo.license_name and repo.license_name != "NOASSERTION")
    if has_license:
        score += 25

    has_topics = bool(repo.topics and len(repo.topics) > 0)
    if has_topics:
        score += 15

    has_issues_enabled = repo.has_issues
    if has_issues_enabled:
        score += 20

    has_readme = True
    score += 20

    return RepoHealthCheck(
        has_readme=has_readme,
        has_license=has_license,
        has_description=has_description,
        has_topics=has_topics,
        has_issues_enabled=has_issues_enabled,
        health_score=min(score, 100),
    )


def analyze_repo(client: GitHubClient, owner: str, repo: str) -> RepoAnalysis:
    repo_data = client.get_repo(owner, repo)
    repo_item = parse_repository_item(repo_data)

    raw_languages = client.get_repo_languages(owner, repo)
    languages = calculate_language_breakdown(raw_languages)

    raw_commits = client.get_repo_commits(owner, repo, per_page=60)
    commit_items: list[CommitItem] = []
    weekday_counts: Counter[str] = Counter()
    hour_counts: Counter[int] = Counter()
    author_counts: Counter[str] = Counter()

    for item in raw_commits:
        commit_info = item.get("commit", {})
        committer = commit_info.get("author", {}) or {}
        author_name = committer.get("name", "Unknown")
        date_str = committer.get("date")
        commit_date = parse_datetime(date_str) or datetime.now(timezone.utc)

        weekday_name = commit_date.strftime("%A")
        weekday_counts[weekday_name] += 1
        hour_counts[commit_date.hour] += 1
        author_counts[author_name] += 1

        commit_items.append(
            CommitItem(
                sha=item.get("sha", "")[:7],
                message=commit_info.get("message", "").split("\n")[0],
                author_name=author_name,
                author_date=commit_date,
                url=item.get("html_url", ""),
            )
        )

    commit_analytics = CommitAnalytics(
        total_sampled_commits=len(commit_items),
        commits_by_weekday=dict(weekday_counts),
        commits_by_hour=dict(hour_counts),
        top_committers=dict(author_counts.most_common(5)),
        latest_commit_date=commit_items[0].author_date if commit_items else None,
    )

    raw_contributors = client.get_repo_contributors(owner, repo, per_page=15)
    contributors = [
        ContributorItem(
            login=c.get("login", "anonymous"),
            contributions=int(c.get("contributions", 0)),
            avatar_url=c.get("avatar_url", ""),
            html_url=c.get("html_url", ""),
        )
        for c in raw_contributors
    ]

    health = compute_health_score(repo_item)

    return RepoAnalysis(
        repository=repo_item,
        languages=languages,
        commit_analytics=commit_analytics,
        contributors=contributors,
        health=health,
    )


def compare_repositories(repo1: RepoAnalysis, repo2: RepoAnalysis) -> ComparisonResult:
    r1 = repo1.repository
    r2 = repo2.repository

    metrics = [
        ComparisonMetric(
            name="Stars",
            value1=f"{r1.stars:,}",
            value2=f"{r2.stars:,}",
            winner=1 if r1.stars > r2.stars else (2 if r2.stars > r1.stars else None),
        ),
        ComparisonMetric(
            name="Forks",
            value1=f"{r1.forks:,}",
            value2=f"{r2.forks:,}",
            winner=1 if r1.forks > r2.forks else (2 if r2.forks > r1.forks else None),
        ),
        ComparisonMetric(
            name="Watchers",
            value1=f"{r1.watchers:,}",
            value2=f"{r2.watchers:,}",
            winner=1 if r1.watchers > r2.watchers else (2 if r2.watchers > r1.watchers else None),
        ),
        ComparisonMetric(
            name="Open Issues",
            value1=f"{r1.open_issues:,}",
            value2=f"{r2.open_issues:,}",
            winner=1 if r1.open_issues < r2.open_issues else (2 if r2.open_issues < r1.open_issues else None),
        ),
        ComparisonMetric(
            name="Size (KB)",
            value1=f"{r1.size_kb:,} KB",
            value2=f"{r2.size_kb:,} KB",
            winner=None,
        ),
        ComparisonMetric(
            name="Primary Language",
            value1=r1.language or "None",
            value2=r2.language or "None",
            winner=None,
        ),
        ComparisonMetric(
            name="License",
            value1=r1.license_name or "None",
            value2=r2.license_name or "None",
            winner=None,
        ),
        ComparisonMetric(
            name="Health Score",
            value1=f"{repo1.health.health_score}/100",
            value2=f"{repo2.health.health_score}/100",
            winner=1 if repo1.health.health_score > repo2.health.health_score else (2 if repo2.health.health_score > repo1.health.health_score else None),
        ),
        ComparisonMetric(
            name="Contributors (Sampled)",
            value1=str(len(repo1.contributors)),
            value2=str(len(repo2.contributors)),
            winner=1 if len(repo1.contributors) > len(repo2.contributors) else (2 if len(repo2.contributors) > len(repo1.contributors) else None),
        ),
    ]

    return ComparisonResult(
        title="Repository Comparison",
        item1_name=r1.full_name,
        item2_name=r2.full_name,
        metrics=metrics,
    )


def compare_users(user1: UserAnalysis, user2: UserAnalysis) -> ComparisonResult:
    u1 = user1.user
    u2 = user2.user

    primary1 = user1.languages.languages[0].name if user1.languages.languages else "None"
    primary2 = user2.languages.languages[0].name if user2.languages.languages else "None"

    metrics = [
        ComparisonMetric(
            name="Followers",
            value1=f"{u1.followers:,}",
            value2=f"{u2.followers:,}",
            winner=1 if u1.followers > u2.followers else (2 if u2.followers > u1.followers else None),
        ),
        ComparisonMetric(
            name="Following",
            value1=f"{u1.following:,}",
            value2=f"{u2.following:,}",
            winner=None,
        ),
        ComparisonMetric(
            name="Public Repositories",
            value1=f"{u1.public_repos:,}",
            value2=f"{u2.public_repos:,}",
            winner=1 if u1.public_repos > u2.public_repos else (2 if u2.public_repos > u1.public_repos else None),
        ),
        ComparisonMetric(
            name="Total Stars Earned",
            value1=f"{user1.total_stars:,}",
            value2=f"{user2.total_stars:,}",
            winner=1 if user1.total_stars > user2.total_stars else (2 if user2.total_stars > user1.total_stars else None),
        ),
        ComparisonMetric(
            name="Total Forks Earned",
            value1=f"{user1.total_forks:,}",
            value2=f"{user2.total_forks:,}",
            winner=1 if user1.total_forks > user2.total_forks else (2 if user2.total_forks > user1.total_forks else None),
        ),
        ComparisonMetric(
            name="Top Language",
            value1=primary1,
            value2=primary2,
            winner=None,
        ),
        ComparisonMetric(
            name="Source Repos",
            value1=str(user1.source_repositories_count),
            value2=str(user2.source_repositories_count),
            winner=1 if user1.source_repositories_count > user2.source_repositories_count else (2 if user2.source_repositories_count > user1.source_repositories_count else None),
        ),
    ]

    return ComparisonResult(
        title="User Comparison",
        item1_name=u1.login,
        item2_name=u2.login,
        metrics=metrics,
    )
