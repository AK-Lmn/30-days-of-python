from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class UserProfile:
    login: str
    name: Optional[str]
    bio: Optional[str]
    company: Optional[str]
    location: Optional[str]
    blog: Optional[str]
    email: Optional[str]
    public_repos: int
    public_gists: int
    followers: int
    following: int
    created_at: datetime
    updated_at: datetime
    html_url: str
    avatar_url: str
    is_hireable: bool = False


@dataclass
class RepositoryItem:
    id: int
    name: str
    full_name: str
    description: Optional[str]
    is_fork: bool
    is_private: bool
    is_archived: bool
    html_url: str
    stars: int
    forks: int
    watchers: int
    open_issues: int
    default_branch: str
    language: Optional[str]
    license_name: Optional[str]
    size_kb: int
    created_at: datetime
    updated_at: datetime
    pushed_at: Optional[datetime]
    topics: list[str] = field(default_factory=list)
    has_issues: bool = True
    has_wiki: bool = True
    has_pages: bool = False


@dataclass
class LanguageShare:
    name: str
    bytes_count: int
    percentage: float


@dataclass
class LanguageBreakdown:
    total_bytes: int
    languages: list[LanguageShare] = field(default_factory=list)


@dataclass
class CommitItem:
    sha: str
    message: str
    author_name: str
    author_date: datetime
    url: str


@dataclass
class CommitAnalytics:
    total_sampled_commits: int
    commits_by_weekday: dict[str, int] = field(default_factory=dict)
    commits_by_hour: dict[int, int] = field(default_factory=dict)
    top_committers: dict[str, int] = field(default_factory=dict)
    latest_commit_date: Optional[datetime] = None


@dataclass
class ContributorItem:
    login: str
    contributions: int
    avatar_url: str
    html_url: str


@dataclass
class RepoHealthCheck:
    has_readme: bool
    has_license: bool
    has_description: bool
    has_topics: bool
    has_issues_enabled: bool
    health_score: int


@dataclass
class UserAnalysis:
    user: UserProfile
    total_repositories: int
    source_repositories_count: int
    forked_repositories_count: int
    total_stars: int
    total_forks: int
    total_watchers: int
    languages: LanguageBreakdown
    top_starred_repos: list[RepositoryItem] = field(default_factory=list)
    top_forked_repos: list[RepositoryItem] = field(default_factory=list)
    recently_pushed_repos: list[RepositoryItem] = field(default_factory=list)


@dataclass
class RepoAnalysis:
    repository: RepositoryItem
    languages: LanguageBreakdown
    commit_analytics: CommitAnalytics
    health: RepoHealthCheck
    contributors: list[ContributorItem] = field(default_factory=list)


@dataclass
class ComparisonMetric:
    name: str
    value1: str
    value2: str
    winner: Optional[int] = None


@dataclass
class ComparisonResult:
    title: str
    item1_name: str
    item2_name: str
    metrics: list[ComparisonMetric] = field(default_factory=list)


@dataclass
class RateLimitStatus:
    limit: int
    remaining: int
    reset_time: datetime
    used: int
