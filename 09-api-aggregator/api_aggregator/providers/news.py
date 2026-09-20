import asyncio
from datetime import datetime, timezone
from typing import Any
from api_aggregator.client import ResilientHttpClient
from api_aggregator.models import UnifiedNewsItem
from api_aggregator.providers.base import BaseProvider


class HackerNewsProvider(BaseProvider):
    def __init__(self) -> None:
        super().__init__(name="hackernews", domain="news")
        self.base_url = "https://hacker-news.firebaseio.com/v0"

    async def fetch(
        self, client: ResilientHttpClient, limit: int = 5, **kwargs: Any
    ) -> list[UnifiedNewsItem]:
        url = f"{self.base_url}/topstories.json"
        response = await client.get(url, provider_name=self.name, timeout=4.0)
        story_ids = response.json()[:limit]

        async def fetch_item(item_id: int) -> dict[str, Any]:
            item_url = f"{self.base_url}/item/{item_id}.json"
            res = await client.get(item_url, provider_name=self.name, timeout=3.0)
            return res.json()

        stories = await asyncio.gather(
            *(fetch_item(sid) for sid in story_ids), return_exceptions=True
        )

        items: list[UnifiedNewsItem] = []
        for story in stories:
            if isinstance(story, dict) and "title" in story:
                items.append(
                    UnifiedNewsItem(
                        id=f"hn-{story.get('id')}",
                        title=story.get("title", "Untitled"),
                        url=story.get(
                            "url", f"https://news.ycombinator.com/item?id={story.get('id')}"
                        ),
                        author=story.get("by", "unknown"),
                        score=story.get("score", 0),
                        comments_count=story.get("descendants", 0),
                        source="HackerNews",
                        published_at=datetime.fromtimestamp(
                            story.get("time", 0), tz=timezone.utc
                        ).isoformat(),
                        tags=["tech", "community"],
                    )
                )
        return items

    def fallback(self, limit: int = 5, **kwargs: Any) -> list[UnifiedNewsItem]:
        mock_data = [
            UnifiedNewsItem(
                id="hn-mock-1",
                title="Show HN: Modern Asynchronous Python API Aggregator",
                url="https://news.ycombinator.com",
                author="pydev",
                score=342,
                comments_count=87,
                source="HackerNews",
                published_at=datetime.now(timezone.utc).isoformat(),
                tags=["python", "async", "api"],
            ),
            UnifiedNewsItem(
                id="hn-mock-2",
                title="Building Resilient Distributed Services with Circuit Breakers",
                url="https://news.ycombinator.com",
                author="distrib_expert",
                score=289,
                comments_count=54,
                source="HackerNews",
                published_at=datetime.now(timezone.utc).isoformat(),
                tags=["distributed-systems", "architecture"],
            ),
            UnifiedNewsItem(
                id="hn-mock-3",
                title="Python 3.13 JIT Compiler Deep Dive and Benchmarks",
                url="https://news.ycombinator.com",
                author="guido_fan",
                score=512,
                comments_count=143,
                source="HackerNews",
                published_at=datetime.now(timezone.utc).isoformat(),
                tags=["python", "performance", "jit"],
            ),
        ]
        return mock_data[:limit]


class GitHubEventsProvider(BaseProvider):
    def __init__(self) -> None:
        super().__init__(name="github", domain="news")
        self.url = "https://api.github.com/search/repositories"

    async def fetch(
        self, client: ResilientHttpClient, limit: int = 5, **kwargs: Any
    ) -> list[UnifiedNewsItem]:
        params = {
            "q": "stars:>5000",
            "sort": "updated",
            "order": "desc",
            "per_page": limit,
        }
        response = await client.get(
            self.url,
            provider_name=self.name,
            params=params,
            headers={"Accept": "application/vnd.github.v3+json"},
            timeout=4.0,
        )
        data = response.json()
        items: list[UnifiedNewsItem] = []
        for repo in data.get("items", [])[:limit]:
            items.append(
                UnifiedNewsItem(
                    id=f"gh-{repo.get('id')}",
                    title=f"{repo.get('full_name')}: {repo.get('description') or 'Open source project'}",
                    url=repo.get("html_url", ""),
                    author=repo.get("owner", {}).get("login", "unknown"),
                    score=repo.get("stargazers_count", 0),
                    comments_count=repo.get("open_issues_count", 0),
                    source="GitHub",
                    published_at=repo.get(
                        "updated_at", datetime.now(timezone.utc).isoformat()
                    ),
                    tags=[repo.get("language") or "general", "repository"],
                )
            )
        return items

    def fallback(self, limit: int = 5, **kwargs: Any) -> list[UnifiedNewsItem]:
        mock_data = [
            UnifiedNewsItem(
                id="gh-mock-1",
                title="python/cpython: The Python programming language",
                url="https://github.com/python/cpython",
                author="python",
                score=62400,
                comments_count=712,
                source="GitHub",
                published_at=datetime.now(timezone.utc).isoformat(),
                tags=["python", "core"],
            ),
            UnifiedNewsItem(
                id="gh-mock-2",
                title="fastapi/fastapi: FastAPI framework, high performance, easy to learn",
                url="https://github.com/fastapi/fastapi",
                author="tiangolo",
                score=78300,
                comments_count=320,
                source="GitHub",
                published_at=datetime.now(timezone.utc).isoformat(),
                tags=["python", "fastapi", "web"],
            ),
        ]
        return mock_data[:limit]


class DevToProvider(BaseProvider):
    def __init__(self) -> None:
        super().__init__(name="devto", domain="news")
        self.url = "https://dev.to/api/articles"

    async def fetch(
        self, client: ResilientHttpClient, limit: int = 5, **kwargs: Any
    ) -> list[UnifiedNewsItem]:
        params = {"per_page": limit, "top": 1}
        response = await client.get(
            self.url, provider_name=self.name, params=params, timeout=4.0
        )
        data = response.json()
        items: list[UnifiedNewsItem] = []
        for article in data[:limit]:
            items.append(
                UnifiedNewsItem(
                    id=f"devto-{article.get('id')}",
                    title=article.get("title", "Untitled"),
                    url=article.get("url", ""),
                    author=article.get("user", {}).get("name", "Unknown"),
                    score=article.get("public_reactions_count", 0),
                    comments_count=article.get("comments_count", 0),
                    source="Dev.to",
                    published_at=article.get(
                        "published_at", datetime.now(timezone.utc).isoformat()
                    ),
                    tags=article.get("tag_list", []) or ["dev"],
                )
            )
        return items

    def fallback(self, limit: int = 5, **kwargs: Any) -> list[UnifiedNewsItem]:
        mock_data = [
            UnifiedNewsItem(
                id="devto-mock-1",
                title="Mastering Asynchronous Systems with Python and AsyncIO",
                url="https://dev.to/mastering-async-python",
                author="Alex Dev",
                score=185,
                comments_count=23,
                source="Dev.to",
                published_at=datetime.now(timezone.utc).isoformat(),
                tags=["python", "async", "tutorial"],
            ),
            UnifiedNewsItem(
                id="devto-mock-2",
                title="Why API Aggregation Architectures Scale Enterprise Applications",
                url="https://dev.to/api-aggregation-architecture",
                author="Elena Code",
                score=142,
                comments_count=19,
                source="Dev.to",
                published_at=datetime.now(timezone.utc).isoformat(),
                tags=["architecture", "microservices"],
            ),
        ]
        return mock_data[:limit]
