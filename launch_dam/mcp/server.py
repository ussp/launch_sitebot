#!/usr/bin/env python3
"""
MCP Server for Launch DAM.

Provides tools for searching and retrieving Launch Family Entertainment
marketing assets directly from Claude Code.
"""

import json
import os
from typing import Any

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool


def get_api_base_url() -> str:
    """Get the API base URL from environment."""
    return os.getenv("LAUNCH_DAM_API_URL", "http://localhost:8000")


def get_api_key() -> str | None:
    """Get the API key from environment."""
    return os.getenv("LAUNCH_DAM_API_KEY")


def create_server() -> Server:
    """Create and configure the MCP server."""
    server = Server("launch-dam")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        """List available tools."""
        return [
            Tool(
                name="search_launch_assets",
                description="""Search Launch Family Entertainment marketing assets.

Use this to find images, videos, and design assets for:
- Social media posts
- Marketing materials
- Party/event promotions
- Brand assets and logos
- Templates and reusable graphics

The search supports natural language queries like:
- "birthday party promotional images"
- "trampoline action shots with kids"
- "Brand Kit logos"
- "social media templates without dates"
""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Natural language search query describing what you're looking for",
                        },
                        "asset_type": {
                            "type": "string",
                            "enum": ["template", "inspiration", "all"],
                            "description": "Filter by asset type: 'template' for reusable assets, 'inspiration' for reference only, 'all' for both",
                            "default": "all",
                        },
                        "album": {
                            "type": "string",
                            "description": "Filter by album name (e.g., 'Brand Kit')",
                        },
                        "media_type": {
                            "type": "string",
                            "enum": ["image", "video", "document"],
                            "description": "Filter by media type",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results (default 10, max 50)",
                            "default": 10,
                            "minimum": 1,
                            "maximum": 50,
                        },
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="get_asset_details",
                description="""Get full details for a specific Launch DAM asset.

Returns complete metadata including:
- File information (dimensions, format)
- Visual analysis (scene, people, objects, colors)
- Brand compliance scores
- Editorial suggestions
- Download URLs
""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "asset_id": {
                            "type": "string",
                            "description": "The UUID of the asset to retrieve",
                        },
                    },
                    "required": ["asset_id"],
                },
            ),
            Tool(
                name="list_albums",
                description="""List all available asset albums/collections.

Returns album names with asset counts, useful for:
- Discovering available asset categories
- Finding location-specific assets
- Browsing the Brand Kit
""",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
            Tool(
                name="get_dam_stats",
                description="""Get statistics about the Launch DAM asset library.

Returns counts by:
- Processing status
- Asset type (template vs inspiration)
- Media type (image, video, document)
- Top albums
- Embedding coverage
""",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
            Tool(
                name="browse_album",
                description="""Browse all assets in a specific album.

Use this to see all assets in an album without searching.
First use list_albums to see available albums, then browse a specific one.

Example albums:
- "Brand Kit" - Official brand assets and templates
- "_New Submissions" - Recently added content
- "Additional Collateral" - Marketing materials
""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "album_name": {
                            "type": "string",
                            "description": "Exact name of the album to browse",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of assets to return (default 20, max 100)",
                            "default": 20,
                            "minimum": 1,
                            "maximum": 100,
                        },
                        "offset": {
                            "type": "integer",
                            "description": "Number of assets to skip for pagination",
                            "default": 0,
                        },
                    },
                    "required": ["album_name"],
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        """Handle tool calls."""
        api_url = get_api_base_url()

        headers = {}
        api_key = get_api_key()
        if api_key:
            headers["X-API-Key"] = api_key

        async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
            try:
                if name == "search_launch_assets":
                    return await _search_assets(client, api_url, arguments)
                elif name == "get_asset_details":
                    return await _get_asset_details(client, api_url, arguments)
                elif name == "list_albums":
                    return await _list_albums(client, api_url)
                elif name == "get_dam_stats":
                    return await _get_stats(client, api_url)
                elif name == "browse_album":
                    return await _browse_album(client, api_url, arguments)
                else:
                    return [TextContent(type="text", text=f"Unknown tool: {name}")]
            except httpx.HTTPError as e:
                return [TextContent(type="text", text=f"API error: {e}")]
            except Exception as e:
                return [TextContent(type="text", text=f"Error: {e}")]

    return server


async def _search_assets(
    client: httpx.AsyncClient, api_url: str, arguments: dict
) -> list[TextContent]:
    """Execute asset search."""
    query = arguments.get("query", "")
    asset_type = arguments.get("asset_type", "all")
    album = arguments.get("album")
    media_type = arguments.get("media_type")
    limit = min(arguments.get("limit", 10), 50)

    # Build request
    filters = {}
    if asset_type and asset_type != "all":
        filters["asset_type"] = asset_type
    if album:
        filters["album"] = album
    if media_type:
        filters["media_type"] = media_type

    payload = {
        "query": query,
        "limit": limit,
        "include_reasoning": True,
    }
    if filters:
        payload["filters"] = filters

    response = await client.post(f"{api_url}/api/search", json=payload)
    response.raise_for_status()
    data = response.json()

    # Format results
    results = data.get("results", [])
    if not results:
        return [TextContent(type="text", text=f"No assets found matching: {query}")]

    lines = [f"Found {len(results)} assets matching '{query}':\n"]
    for i, asset in enumerate(results, 1):
        lines.append(f"{i}. **{asset['filename']}**")
        lines.append(f"   - ID: `{asset['id']}`")
        lines.append(f"   - Type: {asset.get('asset_type', 'unknown')}")
        if asset.get("album_name"):
            lines.append(f"   - Album: {asset['album_name']}")
        if asset.get("media_type"):
            lines.append(f"   - Media: {asset['media_type']}")
        if asset.get("width") and asset.get("height"):
            lines.append(f"   - Dimensions: {asset['width']}x{asset['height']}")
        lines.append(f"   - Score: {asset.get('score', 0):.2f}")
        if asset.get("reasoning"):
            lines.append(f"   - Match: {asset['reasoning']}")
        if asset.get("semantic_description"):
            desc = asset["semantic_description"][:200]
            if len(asset["semantic_description"]) > 200:
                desc += "..."
            lines.append(f"   - Description: {desc}")
        lines.append("")

    return [TextContent(type="text", text="\n".join(lines))]


async def _get_asset_details(
    client: httpx.AsyncClient, api_url: str, arguments: dict
) -> list[TextContent]:
    """Get full asset details."""
    asset_id = arguments.get("asset_id", "")
    if not asset_id:
        return [TextContent(type="text", text="Error: asset_id is required")]

    response = await client.get(f"{api_url}/api/assets/{asset_id}")
    response.raise_for_status()
    asset = response.json()

    # Format detailed output
    lines = [f"# Asset: {asset['filename']}\n"]

    # Basic info
    lines.append("## File Information")
    lines.append(f"- **ID**: `{asset['id']}`")
    lines.append(f"- **Type**: {asset.get('asset_type', 'unknown')}")
    lines.append(f"- **Media Type**: {asset.get('media_type', 'unknown')}")
    lines.append(f"- **Content Type**: {asset.get('content_type', 'unknown')}")
    if asset.get("width") and asset.get("height"):
        lines.append(f"- **Dimensions**: {asset['width']}x{asset['height']}")
    if asset.get("file_size"):
        size_mb = asset["file_size"] / (1024 * 1024)
        lines.append(f"- **File Size**: {size_mb:.2f} MB")
    lines.append("")

    # Organization
    lines.append("## Organization")
    if asset.get("album_name"):
        lines.append(f"- **Album**: {asset['album_name']}")
    if asset.get("album_path"):
        lines.append(f"- **Path**: {asset['album_path']}")
    if asset.get("approval_status"):
        lines.append(f"- **Approval**: {asset['approval_status']}")
    lines.append("")

    # Vision analysis (if available)
    if asset.get("semantic_description"):
        lines.append("## Description")
        lines.append(asset["semantic_description"])
        lines.append("")

    if asset.get("auto_tags"):
        lines.append("## Tags")
        lines.append(", ".join(asset["auto_tags"]))
        lines.append("")

    if asset.get("mood"):
        mood = asset["mood"]
        lines.append("## Mood & Tone")
        if mood.get("primary"):
            lines.append(f"- **Primary Mood**: {mood['primary']}")
        if mood.get("energy_level"):
            lines.append(f"- **Energy Level**: {mood['energy_level']}/10")
        if mood.get("suitable_for"):
            lines.append(f"- **Suitable For**: {', '.join(mood['suitable_for'])}")
        lines.append("")

    if asset.get("brand"):
        brand = asset["brand"]
        lines.append("## Brand Compliance")
        if brand.get("brand_compliance_score"):
            lines.append(f"- **Score**: {brand['brand_compliance_score']}/5")
        if brand.get("logo_present"):
            lines.append(f"- **Logo Present**: Yes ({brand.get('logo_version', 'unknown')})")
        if brand.get("compliance_notes"):
            lines.append(f"- **Notes**: {brand['compliance_notes']}")
        lines.append("")

    if asset.get("editorial"):
        editorial = asset["editorial"]
        lines.append("## Editorial Suggestions")
        if editorial.get("suggested_use"):
            lines.append(f"- **Suggested Use**: {', '.join(editorial['suggested_use'])}")
        if editorial.get("story_position"):
            lines.append(f"- **Story Position**: {editorial['story_position']}")
        lines.append("")

    # URLs
    lines.append("## URLs")
    if asset.get("thumbnail_url"):
        lines.append(f"- **Thumbnail**: {asset['thumbnail_url']}")
    if asset.get("canto_preview_240"):
        lines.append(f"- **Preview**: {asset['canto_preview_240']}")
    lines.append("")

    return [TextContent(type="text", text="\n".join(lines))]


async def _list_albums(client: httpx.AsyncClient, api_url: str) -> list[TextContent]:
    """List all albums."""
    response = await client.get(f"{api_url}/api/albums")
    response.raise_for_status()
    albums = response.json()

    if not albums:
        return [TextContent(type="text", text="No albums found")]

    lines = ["# Launch DAM Albums\n"]
    for album in albums:
        template_marker = " 📁" if album.get("has_templates") else ""
        lines.append(f"- **{album['name']}**: {album['asset_count']} assets{template_marker}")

    lines.append("\n📁 = Contains reusable templates")

    return [TextContent(type="text", text="\n".join(lines))]


async def _get_stats(client: httpx.AsyncClient, api_url: str) -> list[TextContent]:
    """Get DAM statistics."""
    response = await client.get(f"{api_url}/api/sync/stats")
    response.raise_for_status()
    stats = response.json()

    lines = ["# Launch DAM Statistics\n"]

    lines.append(f"**Total Assets**: {stats.get('total_assets', 0):,}")
    lines.append("")

    if stats.get("processing_status"):
        lines.append("## Processing Status")
        for status, count in stats["processing_status"].items():
            lines.append(f"- {status}: {count:,}")
        lines.append("")

    if stats.get("by_asset_type"):
        lines.append("## By Asset Type")
        for asset_type, count in stats["by_asset_type"].items():
            lines.append(f"- {asset_type}: {count:,}")
        lines.append("")

    if stats.get("by_media_type"):
        lines.append("## By Media Type")
        for media_type, count in stats["by_media_type"].items():
            lines.append(f"- {media_type}: {count:,}")
        lines.append("")

    if stats.get("embedding_coverage"):
        coverage = stats["embedding_coverage"]
        lines.append("## Semantic Search Coverage")
        lines.append(f"- With embeddings: {coverage.get('with_embedding', 0):,}")
        lines.append(f"- Total: {coverage.get('total', 0):,}")
        lines.append(f"- Coverage: {coverage.get('percentage', 0):.1f}%")
        lines.append("")

    return [TextContent(type="text", text="\n".join(lines))]


async def _browse_album(
    client: httpx.AsyncClient, api_url: str, arguments: dict
) -> list[TextContent]:
    """Browse assets in a specific album."""
    album_name = arguments.get("album_name", "")
    if not album_name:
        return [TextContent(type="text", text="Error: album_name is required")]

    limit = min(arguments.get("limit", 20), 100)
    offset = arguments.get("offset", 0)

    response = await client.get(
        f"{api_url}/api/albums/{album_name}/assets",
        params={"limit": limit, "offset": offset},
    )
    response.raise_for_status()
    data = response.json()

    assets = data.get("assets", [])
    if not assets:
        return [TextContent(type="text", text=f"No assets found in album: {album_name}")]

    lines = [f"# Album: {album_name}\n"]
    lines.append(f"Showing {len(assets)} assets (offset: {offset})\n")

    for i, asset in enumerate(assets, 1):
        lines.append(f"{i + offset}. **{asset['filename']}**")
        lines.append(f"   - ID: `{asset['id']}`")
        lines.append(f"   - Type: {asset.get('asset_type', 'unknown')}")
        lines.append(f"   - Media: {asset.get('media_type', 'unknown')}")
        if asset.get("thumbnail_url"):
            lines.append(f"   - Thumbnail: {asset['thumbnail_url']}")
        lines.append("")

    if len(assets) == limit:
        lines.append(f"\n*More assets available. Use offset={offset + limit} to see next page.*")

    return [TextContent(type="text", text="\n".join(lines))]


async def main():
    """Run the MCP server."""
    server = create_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
