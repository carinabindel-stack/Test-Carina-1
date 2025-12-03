from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Optional, Sequence

from .analysis import analyze_posts
from .client import LinkedInClient
from .categorizer import DEFAULT_CATEGORY_RULES

LOGGER = logging.getLogger("linkedin_tool")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Analyze LinkedIn post performance for a company page.",
    )
    parser.add_argument("--organization-urn", help="Full organization URN (e.g. urn:li:organization:123456)")
    parser.add_argument("--organization-id", help="Organization numeric ID (auto-converted to a URN)")
    parser.add_argument("--access-token", help="LinkedIn Marketing API OAuth token. Defaults to env LINKEDIN_ACCESS_TOKEN.")
    parser.add_argument("--token-file", help="Path to a file containing the access token.")
    parser.add_argument("--limit", type=int, default=300, help="Maximum number of posts to inspect (default: 300)")
    parser.add_argument("--top-n", type=int, default=5, help="How many top-performing posts to highlight.")
    parser.add_argument("--since-days", type=int, default=365, help="Lookback window in days (default: 365).")
    parser.add_argument("--category-config", type=Path, help="Optional JSON file with category -> keywords mapping.")
    parser.add_argument("--json", action="store_true", help="Emit raw JSON instead of a human-readable report.")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging.")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    configure_logging(debug=args.verbose)

    access_token = resolve_access_token(args.access_token, args.token_file)
    if not access_token:
        parser.error("An access token is required (pass --access-token, --token-file, or export LINKEDIN_ACCESS_TOKEN).")

    organization_urn = resolve_organization_urn(args.organization_urn, args.organization_id)
    if not organization_urn:
        parser.error("Provide either --organization-urn or --organization-id.")

    category_rules = load_category_rules(args.category_config)

    client = LinkedInClient(access_token=access_token)
    LOGGER.info("Fetching up to %s posts for %s", args.limit, organization_urn)
    posts = client.fetch_posts(organization_urn=organization_urn, limit=args.limit)
    posts = client.hydrate_engagement(posts)

    since = datetime.now(tz=timezone.utc) - timedelta(days=args.since_days)
    analysis = analyze_posts(
        posts,
        since=since,
        until=datetime.now(tz=timezone.utc),
        top_n=args.top_n,
        category_rules=category_rules,
    )

    if args.json:
        print(json.dumps(serialize_result(analysis), indent=2, default=str))
    else:
        print(render_text_report(analysis))

    return 0


def configure_logging(debug: bool = False) -> None:
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s - %(message)s")


def resolve_access_token(cli_token: Optional[str], token_file: Optional[str]) -> Optional[str]:
    if cli_token:
        return cli_token.strip()
    if token_file:
        return Path(token_file).read_text(encoding="utf-8").strip()
    from os import getenv

    env_token = getenv("LINKEDIN_ACCESS_TOKEN")
    if env_token:
        return env_token.strip()
    return None


def resolve_organization_urn(organization_urn: Optional[str], organization_id: Optional[str]) -> Optional[str]:
    if organization_urn:
        return organization_urn.strip()
    if organization_id:
        organization_id = organization_id.strip()
        if organization_id.startswith("urn:li:organization:"):
            return organization_id
        return f"urn:li:organization:{organization_id}"
    return None


def load_category_rules(path: Optional[Path]) -> Dict[str, Sequence[str]]:
    if not path:
        return DEFAULT_CATEGORY_RULES

    if not path.exists():
        raise FileNotFoundError(f"Category config not found: {path}")

    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    if not isinstance(data, dict):
        raise ValueError("Category config must be a JSON object.")

    return {key: tuple(value) if isinstance(value, list) else (value,) for key, value in data.items()}


def render_text_report(result) -> str:
    category_lookup = {
        entry.post.urn: entry.categories for entry in result.categorized_posts
    }
    lines = [
        f"Analyzed {result.total_posts_analyzed} posts out of {result.total_posts_fetched} fetched.",
        f"Timeframe: {result.since.date()} ➜ {result.until.date()}",
        "",
        "Top categories (share of analyzed posts):",
    ]
    for category, share in list(result.top_categories.most_common(5)):
        portion = share / max(result.total_posts_analyzed, 1)
        lines.append(f"  - {category}: {portion:.0%} of posts")

    lines.append("")
    lines.append("Most successful posts (ranked by engagement rate):")
    for idx, post in enumerate(result.top_posts, start=1):
        categories = ", ".join(category_lookup.get(post.urn, ["general"]))
        lines.append(
            f"{idx}. {post.created_at.date()} | Engagement {post.stats.engagement_rate:.2f}% | "
            f"{post.stats.total_interactions} interactions | {categories}"
        )
        if post.permalink:
            lines.append(f"   {post.permalink}")

    lines.append("")
    lines.append("Traits shared by top posts:")
    traits = result.trait_summary
    if not traits:
        lines.append("  (Insufficient data to derive traits.)")
    else:
        for category, distribution in traits.items():
            lines.append(f"  {category}:")
            if isinstance(distribution, dict):
                for key, value in distribution.items():
                    if isinstance(value, float) and value <= 1:
                        lines.append(f"    - {key}: {value:.0%}")
                    else:
                        lines.append(f"    - {key}: {value}")
            else:
                lines.append(f"    - {distribution}")

    return "\n".join(lines)


def serialize_result(result) -> Dict:
    def serialize_post(post):
        return {
            "urn": post.urn,
            "created_at": post.created_at.isoformat(),
            "engagement_rate": post.stats.engagement_rate,
            "total_interactions": post.stats.total_interactions,
            "likes": post.stats.likes,
            "comments": post.stats.comments,
            "shares": post.stats.shares,
            "clicks": post.stats.clicks,
            "impressions": post.stats.impressions,
            "media_type": post.media_type,
            "lifecycle_state": post.lifecycle_state,
            "permalink": post.permalink,
        }

    return {
        "since": result.since.isoformat(),
        "until": result.until.isoformat(),
        "total_posts_fetched": result.total_posts_fetched,
        "total_posts_analyzed": result.total_posts_analyzed,
        "top_categories": result.top_categories.most_common(),
        "trait_summary": result.trait_summary,
        "top_posts": [serialize_post(post) for post in result.top_posts],
    }


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
