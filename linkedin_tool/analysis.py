from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from statistics import mean
from typing import Dict, Iterable, List, Optional, Sequence

from .categorizer import CategorizedPost, PostCategorizer
from .models import LinkedInPost


@dataclass
class AnalysisResult:
    since: datetime
    until: datetime
    total_posts_fetched: int
    total_posts_analyzed: int
    categorized_posts: List[CategorizedPost]
    top_posts: List[LinkedInPost]
    top_categories: Counter
    trait_summary: Dict[str, Dict[str, float]]


def analyze_posts(
    posts: Sequence[LinkedInPost],
    *,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
    top_n: int = 5,
    category_rules: Optional[Dict[str, Sequence[str]]] = None,
) -> AnalysisResult:
    """Filter and summarize LinkedIn post performance."""

    if since is None:
        since = datetime.now(tz=timezone.utc) - timedelta(days=365)
    if until is None:
        until = datetime.now(tz=timezone.utc)

    filtered = [post for post in posts if since <= post.created_at <= until]
    categorizer = PostCategorizer(category_rules=category_rules)
    categorized = categorizer.categorize_many(filtered)
    top_categories = categorizer.category_counts(categorized)

    top_posts = sorted(
        filtered,
        key=lambda post: (post.stats.engagement_rate, post.stats.total_interactions),
        reverse=True,
    )[:top_n]

    trait_summary = summarize_common_traits(top_posts, categorizer)

    return AnalysisResult(
        since=since,
        until=until,
        total_posts_fetched=len(posts),
        total_posts_analyzed=len(filtered),
        categorized_posts=categorized,
        top_posts=top_posts,
        top_categories=top_categories,
        trait_summary=trait_summary,
    )


def summarize_common_traits(
    posts: Iterable[LinkedInPost], categorizer: PostCategorizer
) -> Dict[str, Dict[str, float]]:
    """Return aggregated characteristics for the supplied posts."""

    if not posts:
        return {}

    categorized_top = categorizer.categorize_many(posts)
    category_counts = categorizer.category_counts(categorized_top)

    media_counter = Counter(post.media_type or "unspecified" for post in posts)
    day_counter = Counter(post.created_day for post in posts)
    hashtag_counter = Counter(tag for post in posts for tag in post.hashtags)

    total = len(posts)
    avg_word_count = mean(post.word_count for post in posts) if posts else 0
    avg_hashtags = (
        mean(len(post.hashtags) for post in posts) if posts else 0
    )

    link_rate = sum(1 for post in posts if post.contains_link) / total
    mention_rate = sum(1 for post in posts if post.contains_mention) / total
    media_rate = {key: round(value / total, 2) for key, value in media_counter.items()}

    return {
        "categories": _normalize_counter(category_counts, total),
        "media_types": media_rate,
        "days": _normalize_counter(day_counter, total),
        "hashtags": dict(hashtag_counter.most_common(5)),
        "averages": {
            "word_count": round(avg_word_count, 1),
            "hashtags_per_post": round(avg_hashtags, 2),
            "link_rate": round(link_rate, 2),
            "mention_rate": round(mention_rate, 2),
        },
    }


def _normalize_counter(counter: Counter, total: int) -> Dict[str, float]:
    if total == 0:
        return {}
    return {key: round(value / total, 2) for key, value in counter.most_common()}
