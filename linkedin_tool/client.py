from __future__ import annotations

import logging
import time
from typing import Dict, Iterable, List, Optional
from urllib.parse import quote_plus

import requests

from .models import InteractionStats, LinkedInPost

LOGGER = logging.getLogger(__name__)


class LinkedInAPIError(RuntimeError):
    """Raised when the LinkedIn API responds with an error payload."""

    def __init__(self, status_code: int, message: str, details: Optional[Dict] = None):
        super().__init__(f"LinkedIn API error {status_code}: {message}")
        self.status_code = status_code
        self.details = details or {}


class LinkedInClient:
    """Thin wrapper around the LinkedIn REST API."""

    BASE_URL = "https://api.linkedin.com"
    API_ROOT = "rest"

    def __init__(
        self,
        access_token: str,
        api_version: str = "202401",
        request_timeout: int = 10,
        max_retries: int = 3,
        sleep_between_calls: float = 0.2,
    ) -> None:
        self.access_token = access_token
        self.api_version = api_version
        self.timeout = request_timeout
        self.max_retries = max_retries
        self.sleep_between_calls = sleep_between_calls
        self.session = requests.Session()

    # --------------------------------------------------------------------- #
    # Public methods
    # --------------------------------------------------------------------- #
    def fetch_posts(
        self,
        organization_urn: str,
        limit: int = 500,
        lifecycle_state: str = "PUBLISHED",
    ) -> List[LinkedInPost]:
        """Return up to `limit` posts authored by the organization."""

        collected: List[LinkedInPost] = []
        start = 0

        while len(collected) < limit:
            batch_size = min(100, limit - len(collected))
            payload = self._request(
                "GET",
                "posts",
                params={
                    "q": "author",
                    "author": organization_urn,
                    "start": start,
                    "count": batch_size,
                    "lifecycleState": lifecycle_state,
                    "sortBy": "LAST_MODIFIED",
                },
            )

            elements = payload.get("elements", [])
            LOGGER.debug("Fetched %s posts", len(elements))
            for element in elements:
                collected.append(LinkedInPost.from_raw(element))

            if not _has_next_page(payload):
                break

            start += len(elements)
            time.sleep(self.sleep_between_calls)

        return collected

    def hydrate_engagement(self, posts: Iterable[LinkedInPost]) -> List[LinkedInPost]:
        """Populate interaction metrics for each post using socialActions."""

        hydrated: List[LinkedInPost] = []
        for post in posts:
            urn = post.urn or post.raw.get("urn")
            if not urn:
                hydrated.append(post)
                continue

            stats_payload = self._request(
                "GET", f"socialActions/{quote_plus(urn)}"
            )
            post.stats = _parse_interaction_stats(stats_payload)
            hydrated.append(post)
            time.sleep(self.sleep_between_calls)

        return hydrated

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _request(self, method: str, path: str, params: Optional[Dict] = None, json: Optional[Dict] = None) -> Dict:
        url = f"{self.BASE_URL}/{self.API_ROOT}/{path.lstrip('/')}"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "LinkedIn-Version": self.api_version,
            "X-Restli-Protocol-Version": "2.0.0",
        }

        for attempt in range(1, self.max_retries + 1):
            response = self.session.request(
                method=method.upper(),
                url=url,
                params=params,
                json=json,
                headers=headers,
                timeout=self.timeout,
            )

            if response.status_code < 400:
                return response.json()

            if response.status_code in {429, 500, 502, 503, 504} and attempt < self.max_retries:
                LOGGER.warning(
                    "LinkedIn API error %s. Retrying (%s/%s)...",
                    response.status_code,
                    attempt,
                    self.max_retries,
                )
                time.sleep(self.sleep_between_calls * attempt)
                continue

            raise LinkedInAPIError(
                response.status_code,
                response.text,
                details=_safe_json(response),
            )

        raise LinkedInAPIError(500, "Exceeded retry budget")


# ---------------------------------------------------------------------- #
# Helpers
# ---------------------------------------------------------------------- #
def _has_next_page(payload: Dict) -> bool:
    paging = payload.get("paging") or {}
    links = paging.get("links") or []
    return any(link.get("rel") == "next" for link in links if isinstance(link, dict))


def _safe_json(response: requests.Response) -> Optional[Dict]:
    try:
        return response.json()
    except ValueError:
        return None


def _parse_interaction_stats(payload: Dict) -> InteractionStats:
    reactions = payload.get("reactionsSummary", {}).get("aggregatedTotal", 0)
    likes = payload.get("likesSummary", {}).get("aggregatedTotal", reactions)
    comments = payload.get("commentsSummary", {}).get("totalFirstLevelComments", 0)
    shares = payload.get("sharesSummary", {}).get("shareCount", 0)
    clicks = (
        payload.get("clicksSummary", {})
        .get("organicClicks", {})
        .get("clicks", 0)
    )
    impressions = (
        payload.get("impressionsSummary", {})
        .get("organicImpressions", {})
        .get("impressionsCount", 0)
    )
    video_views = (
        payload.get("videoAnalyticsSummary", {})
        .get("viewCounts", {})
        .get("atLeast2SecondsViews", 0)
    )

    return InteractionStats(
        likes=int(likes or 0),
        comments=int(comments or 0),
        shares=int(shares or 0),
        clicks=int(clicks or 0),
        impressions=int(impressions or 0),
        video_views=int(video_views or 0),
    )
