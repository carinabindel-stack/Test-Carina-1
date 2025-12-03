from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class InteractionStats:
    """Normalized engagement metrics for a single LinkedIn post."""

    likes: int = 0
    comments: int = 0
    shares: int = 0
    clicks: int = 0
    impressions: int = 0
    video_views: int = 0

    @property
    def total_interactions(self) -> int:
        return self.likes + self.comments + self.shares + self.clicks

    @property
    def engagement_rate(self) -> float:
        if self.impressions <= 0:
            return 0.0
        return round((self.total_interactions / self.impressions) * 100, 3)


@dataclass
class LinkedInPost:
    """Structured representation of the LinkedIn /rest/posts payload."""

    urn: str
    author: str
    text: str
    created_at: datetime
    lifecycle_state: str
    media_type: Optional[str]
    visibility: Optional[str]
    hashtags: List[str] = field(default_factory=list)
    stats: InteractionStats = field(default_factory=InteractionStats)
    raw: Dict[str, Any] = field(default_factory=dict)

    @property
    def permalink(self) -> Optional[str]:
        return self.raw.get("permalink")

    @property
    def word_count(self) -> int:
        return len(self.text.split())

    @property
    def contains_mention(self) -> bool:
        return "@" in self.text

    @property
    def contains_link(self) -> bool:
        return "http://" in self.text or "https://" in self.text

    @property
    def created_day(self) -> str:
        return self.created_at.strftime("%A")

    @classmethod
    def from_raw(cls, payload: Dict[str, Any]) -> "LinkedInPost":
        text = extract_text(payload)
        hashtags = extract_hashtags(payload)
        media_type = (
            payload.get("content", {})
            .get("media", [{}])[0]
            .get("mediaType")
        )
        timestamp = payload.get("createdAt", {}).get("time")
        dt = datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc) if timestamp else datetime.now(tz=timezone.utc)

        return cls(
            urn=payload.get("id") or payload.get("urn") or "",
            author=payload.get("author", ""),
            text=text,
            created_at=dt,
            lifecycle_state=payload.get("lifecycleState", ""),
            media_type=media_type,
            visibility=payload.get("visibility", {}).get("com.linkedin.ugc.MemberNetworkVisibility", ""),
            hashtags=hashtags,
            raw=payload,
        )


def extract_text(payload: Dict[str, Any]) -> str:
    """Best-effort extraction of the text body from various payload shapes."""

    # /rest/posts
    if "text" in payload and isinstance(payload["text"], dict):
        return payload["text"].get("text", "").strip()

    # legacy /ugcPosts
    body = (
        payload.get("specificContent", {})
        .get("com.linkedin.ugc.ShareContent", {})
        .get("shareCommentary", {})
        .get("text")
    )
    if isinstance(body, str):
        return body.strip()

    return ""


def extract_hashtags(payload: Dict[str, Any]) -> List[str]:
    hashtags = []
    if "content" in payload:
        for hashtag in payload.get("content", {}).get("hashtags", []):
            if isinstance(hashtag, str):
                hashtags.append(hashtag.lower())

    content_entities = (
        payload.get("specificContent", {})
        .get("com.linkedin.ugc.ShareContent", {})
        .get("media", [])
    )
    for entity in content_entities:
        if isinstance(entity, dict):
            for insight in entity.get("thumbnails", []):
                if isinstance(insight, dict) and "imageSpecificContent" in insight:
                    tag = insight["imageSpecificContent"].get("shareHashtag")
                    if isinstance(tag, str):
                        hashtags.append(tag.lower())

    return hashtags
