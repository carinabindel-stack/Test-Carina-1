from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Dict, Iterable, List, MutableMapping, Optional, Sequence

from .models import LinkedInPost

DEFAULT_CATEGORY_RULES: Dict[str, Sequence[str]] = {
    "sustainability": ("sustain", "circular", "climate", "recycl", "eco"),
    "innovation": ("innovation", "launch", "product", "solution", "ai", "prototype"),
    "events": ("event", "conference", "expo", "webinar", "booth", "panel"),
    "awards": ("award", "recognition", "won", "shortlist", "honor", "prize"),
    "partnerships": ("partner", "collaborat", "together", "alliance"),
    "hiring": ("hiring", "career", "role", "join our team", "apply"),
    "thought_leadership": ("insight", "report", "whitepaper", "guide", "blog"),
    "packaging": ("packag", "design", "material", "bottle", "reusable"),
}


@dataclass
class CategorizedPost:
    post: LinkedInPost
    categories: List[str]


class PostCategorizer:
    """Keyword-based classifier for high-level LinkedIn themes."""

    def __init__(self, category_rules: Optional[Dict[str, Sequence[str]]] = None, minimum_keyword_length: int = 3) -> None:
        self.rules = category_rules or DEFAULT_CATEGORY_RULES
        self.minimum_keyword_length = minimum_keyword_length

    def categorize(self, post: LinkedInPost) -> CategorizedPost:
        text = post.text.lower()
        matches: List[str] = []

        for category, keywords in self.rules.items():
            for keyword in keywords:
                cleaned = keyword.strip().lower()
                if len(cleaned) < self.minimum_keyword_length:
                    continue
                if cleaned in text or any(cleaned in hashtag for hashtag in post.hashtags):
                    matches.append(category)
                    break

        if not matches:
            matches.append("general")

        return CategorizedPost(post=post, categories=matches)

    def categorize_many(self, posts: Iterable[LinkedInPost]) -> List[CategorizedPost]:
        return [self.categorize(post) for post in posts]

    def build_category_matrix(self, categorized_posts: Iterable[CategorizedPost]) -> MutableMapping[str, List[LinkedInPost]]:
        matrix: MutableMapping[str, List[LinkedInPost]] = defaultdict(list)

        for entry in categorized_posts:
            for category in entry.categories:
                matrix[category].append(entry.post)

        return matrix

    def category_counts(self, categorized_posts: Iterable[CategorizedPost]) -> Counter:
        counts: Counter = Counter()
        for entry in categorized_posts:
            counts.update(entry.categories)
        return counts
