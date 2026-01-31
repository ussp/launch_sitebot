# Launch DAM - Digital Asset Management

A searchable Digital Asset Management system for Launch Family Entertainment's 12K+ marketing assets.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Clients                                  │
├─────────────────┬───────────────────────────────────────────────┤
│   Claude Code   │              Webapp (future)                  │
│   (MCP Server)  │                                               │
└────────┬────────┴──────────────────┬────────────────────────────┘
         │                           │
         ▼                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI Service                               │
│  POST /api/search    GET /api/assets    GET /api/albums          │
│  POST /api/ingest    GET /api/sync/status                        │
└────────┬────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Neon PostgreSQL                               │
│  Extensions: pgvector, pg_trgm                                  │
│  Hybrid Search: Semantic (embeddings) + Keyword (trigram)       │
└─────────────────────────────────────────────────────────────────┘
```

## Features

- **Hybrid Search**: Combines semantic embeddings (OpenAI) with keyword matching
- **Smart Classification**: Automatically classifies assets as `template` (reusable) or `inspiration`
- **Vision Analysis**: GPT-4o extracts rich metadata from images/videos
- **MCP Integration**: Search assets directly from Claude Code
- **Ingestion Framework**: Standardized spec for multiple asset sources

## Quick Start

### 1. Set up environment

```bash
cd launch_dam
cp .env.example .env
# Edit .env with your credentials
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the API

```bash
uvicorn api.main:app --reload
```

### 4. Migrate existing data

```bash
# Set DATABASE_URL environment variable
python scripts/migrate_to_neon.py
```

### 5. Generate embeddings

```bash
# Set DATABASE_URL and OPENAI_API_KEY
python scripts/generate_embeddings.py
```

## API Endpoints

### Search

```bash
# Search for assets
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "birthday party social media", "limit": 10}'
```

### Assets

```bash
# Get asset details
curl http://localhost:8000/api/assets/{asset_id}

# List assets
curl http://localhost:8000/api/assets?album=Brand%20Kit&limit=50
```

### Albums

```bash
# List all albums
curl http://localhost:8000/api/albums
```

### Sync Status

```bash
# Get processing stats
curl http://localhost:8000/api/sync/status
curl http://localhost:8000/api/sync/stats
```

## MCP Server (Claude Code)

The MCP server provides these tools:

- `search_launch_assets` - Search marketing assets
- `get_asset_details` - Get full asset metadata
- `list_albums` - List available albums
- `get_dam_stats` - Get library statistics

### Configure MCP Server

Add to your Claude Code config:

```json
{
  "mcpServers": {
    "launch-dam": {
      "command": "python",
      "args": ["/path/to/launch_dam/mcp/server.py"],
      "env": {
        "LAUNCH_DAM_API_URL": "https://your-api-url.railway.app"
      }
    }
  }
}
```

## Processing Pipeline

Assets go through these stages:

1. **pending** - Registered, awaiting classification
2. **classified** - Asset type determined
3. **enriched** - Search text generated
4. **indexed** - Embedding generated, fully searchable

## Scripts

| Script | Purpose |
|--------|---------|
| `migrate_to_neon.py` | Migrate from canto_metadata.json to Neon |
| `generate_embeddings.py` | Generate OpenAI embeddings for search |
| `run_vision_analysis.py` | Run GPT-4o vision on assets |

## Environment Variables

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | Neon PostgreSQL connection string |
| `OPENAI_API_KEY` | OpenAI API key |
| `PORT` | API server port (default: 8000) |
| `LAUNCH_DAM_API_URL` | API URL for MCP server |

## Deployment

### Railway

```bash
# Link project
railway link

# Deploy
railway up
```

Set these environment variables in Railway:
- `DATABASE_URL`
- `OPENAI_API_KEY`

## Project Structure

```
launch_dam/
├── api/                    # FastAPI application
│   ├── routes/             # API endpoints
│   ├── services/           # Business logic
│   ├── models/             # Pydantic schemas
│   └── db/                 # Database connection
├── mcp/                    # MCP server for Claude Code
├── downloaders/            # Asset ingestion framework
├── scripts/                # Migration & processing scripts
├── ingestion_spec.json     # Ingestion contract
├── Dockerfile
├── railway.toml
└── requirements.txt
```
