# Credora - AI-Powered CFO for E-Commerce

Credora is an AI-driven virtual CFO platform designed for e-commerce businesses. It provides intelligent financial analysis, actionable recommendations, and seamless integration with advertising and e-commerce platforms through a multi-agent architecture.

## Table of Contents

- [Features](#features)
- [Architecture Overview](#architecture-overview)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Application](#running-the-application)
- [System Components](#system-components)
- [API Integrations](#api-integrations)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)

## Features

- **Multi-Agent Architecture**: Specialized agents for different tasks (onboarding, data fetching, analytics, competitor analysis, insights)
- **Platform Integrations**: Connect to Shopify, Meta Ads, and Google Ads via OAuth
- **MCP Protocol**: Model Context Protocol servers for secure, standardized API communication
- **Encrypted Token Storage**: OAuth tokens stored with AES encryption
- **Read-Only Operations**: All data access is read-only - no modifications to your store data
- **Interactive CLI**: Command-line interface for conversational interaction

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Interface                          │
│                      (CLI / main.py)                            │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                        CFO Agent                                │
│              (Orchestrator - Routes Queries)                    │
└─────────────────────────────────────────────────────────────────┘
                                │
        ┌───────────┬───────────┼───────────┬───────────┐
        ▼           ▼           ▼           ▼           ▼
┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐
│ Onboarding│ │   Data    │ │ Analytics │ │Competitor │ │  Insight  │
│   Agent   │ │  Fetcher  │ │   Agent   │ │   Agent   │ │   Agent   │
└───────────┘ └───────────┘ └───────────┘ └───────────┘ └───────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                       MCP Router                                │
└─────────────────────────────────────────────────────────────────┘
        │                   │                   │
        ▼                   ▼                   ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│  Meta Ads     │   │  Google Ads   │   │   Shopify     │
│  MCP Server   │   │  MCP Server   │   │  MCP Server   │
└───────────────┘   └───────────────┘   └───────────────┘
        │                   │                   │
        ▼                   ▼                   ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│ Meta Marketing│   │  Google Ads   │   │ Shopify Admin │
│     API       │   │     API       │   │     API       │
└───────────────┘   └───────────────┘   └───────────────┘
```

## Project Structure

```
Credora/
├── main.py                     # Application entry point (CLI)
├── pyproject.toml              # Project dependencies and metadata
├── uv.lock                     # Dependency lock file
├── .env                        # Environment variables (API keys)
├── .env.example                # Example environment file
├── README.md                   # This file
│
├── credora/                    # Main application package
│   ├── __init__.py
│   ├── config.py               # LLM and API configuration
│   ├── errors.py               # Custom error classes
│   ├── examples.py             # Example queries for demo
│   ├── logging.py              # Logging utilities
│   ├── security.py             # Encryption utilities for tokens
│   │
│   ├── agents/                 # AI Agent implementations
│   │   ├── __init__.py
│   │   ├── base.py             # Base agent utilities, model creation
│   │   ├── cfo.py              # CFO Orchestrator Agent
│   │   ├── onboarding.py       # User onboarding agent
│   │   ├── data_fetcher.py     # Data retrieval agent
│   │   ├── analytics.py        # Analytics and trends agent
│   │   ├── competitor.py       # Competitor analysis agent
│   │   └── insight.py          # Recommendations agent
│   │
│   ├── tools/                  # Agent tools (functions agents can call)
│   │   ├── __init__.py
│   │   ├── cfo.py              # Session state management tools
│   │   ├── onboarding.py       # Platform connection tools
│   │   ├── data_fetcher.py     # Data fetching tools
│   │   ├── analytics.py        # Analytics calculation tools
│   │   ├── competitor.py       # Competitor research tools
│   │   ├── insight.py          # Recommendation generation tools
│   │   ├── connection.py       # Platform connection management
│   │   └── mcp_router.py       # Routes requests to MCP servers
│   │
│   ├── mcp_servers/            # MCP Protocol server implementations
│   │   ├── __init__.py
│   │   ├── base.py             # Base MCP server class
│   │   ├── meta_ads.py         # Meta (Facebook/Instagram) Ads server
│   │   ├── meta_ads_client.py  # Meta API client
│   │   ├── google_ads.py       # Google Ads server
│   │   ├── google_ads_client.py# Google Ads API client
│   │   ├── shopify.py          # Shopify server
│   │   ├── shopify_client.py   # Shopify API client
│   │   ├── connection_manager.py # OAuth flow management
│   │   ├── token_store.py      # Encrypted token storage
│   │   ├── oauth.py            # OAuth utilities
│   │   ├── errors.py           # MCP error types
│   │   ├── logging.py          # MCP logging with sanitization
│   │   └── models/             # Data models for each platform
│   │       ├── __init__.py
│   │       ├── oauth.py        # OAuth data models
│   │       ├── meta_ads.py     # Meta Ads data models
│   │       ├── google_ads.py   # Google Ads data models
│   │       └── shopify.py      # Shopify data models
│   │
│   ├── models/                 # Core data models
│   │   └── __init__.py
│   │
│   └── state/                  # Session state management
│       └── __init__.py
│
└── tests/                      # Test suite
    ├── __init__.py
    ├── property/               # Property-based tests (Hypothesis)
    ├── unit/                   # Unit tests
    └── integration/            # Integration tests
```

## Prerequisites

- **Python 3.12+** - Required for the application
- **uv** - Python package manager (recommended) or pip
- **OpenRouter API Key** - For LLM access

### Installing uv (Package Manager)

```bash
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Installation

1. **Extract the project** (if received as zip):
   ```bash
   unzip Credora.zip
   cd Credora
   ```

2. **Install dependencies**:
   ```bash
   uv sync
   ```
   This creates a virtual environment and installs all dependencies.

3. **Set up environment variables**:
   ```bash
   # Copy the example file
   cp .env.example .env
   
   # Edit .env and add your API key
   # Windows: notepad .env
   # macOS/Linux: nano .env
   ```

## Configuration

### Environment Variables (.env)

Create a `.env` file in the project root with:

```env
# Required: OpenRouter API Key for LLM access
OPENROUTER_API_KEY=your_openrouter_api_key_here
```

### Getting an OpenRouter API Key

1. Go to [OpenRouter.ai](https://openrouter.ai/)
2. Sign up or log in
3. Navigate to API Keys section
4. Create a new API key
5. Copy and paste it into your `.env` file

### Model Configuration (credora/config.py)

The LLM model is configured in `credora/config.py`:

```python
@dataclass
class ModelConfig:
    model_name: str = "nex-agi/deepseek-v3.1-nex-n1:free"  # Default model
    base_url: str = "https://openrouter.ai/api/v1"         # OpenRouter endpoint
    temperature: float = 0.7                                # Response creativity
    max_tokens: int = 4096                                  # Max response length
```

You can change the model by modifying `model_name`. OpenRouter supports many models including:
- `openai/gpt-4o`
- `anthropic/claude-3.5-sonnet`
- `google/gemini-pro`
- And many more (see OpenRouter docs)

## Running the Application

### Interactive CLI Mode (Default)

Start an interactive conversation with the CFO Agent:

```bash
uv run main.py
```

You'll see:
```
============================================================
  Credora CFO Agent - Interactive Session
============================================================

Welcome! I'm your AI-powered CFO assistant.
Type 'quit' or 'exit' to end the session.
Type 'help' to see example queries.
------------------------------------------------------------

You: 
```

### CLI Commands

| Command | Description |
|---------|-------------|
| `help` | Show example queries and commands |
| `examples` | Display all example queries by category |
| `quit` / `exit` / `q` | End the session |

### Single Query Mode

Run a single query without interactive mode:

```bash
uv run main.py --query "What can you help me with?"
```

### Demo Mode

Run example queries demonstrating each agent:

```bash
uv run main.py --demo
```

## System Components

### Agents

| Agent | Purpose | Triggers |
|-------|---------|----------|
| **CFO Agent** | Main orchestrator, routes queries | All queries start here |
| **Onboarding Agent** | User setup, platform connections | "connect my store", "get started" |
| **Data Fetcher Agent** | Retrieves data from platforms | "show me sales", "get orders" |
| **Analytics Agent** | Trend analysis, pattern detection | "analyze", "why did revenue drop" |
| **Competitor Agent** | Market and competitor research | "competitor pricing", "market trends" |
| **Insight Agent** | Actionable recommendations | "what should I do", "recommendations" |

### MCP Servers

Model Context Protocol servers handle secure communication with external APIs:

| Server | Platform | API Version |
|--------|----------|-------------|
| Meta Ads MCP | Facebook/Instagram Ads | Marketing API v21.0 |
| Google Ads MCP | Google Ads | API v18 |
| Shopify MCP | Shopify Stores | Admin API 2024-10 |

### Security Features

- **Token Encryption**: OAuth tokens encrypted with AES-256 at rest
- **HTTPS Only**: All API requests use HTTPS
- **Log Sanitization**: Sensitive data masked in logs
- **User Isolation**: Each user's data is isolated
- **Read-Only**: No write operations on connected platforms

## API Integrations

### Connecting Platforms

When you ask to connect a platform, the system will:
1. Generate an OAuth authorization URL
2. You visit the URL and authorize access
3. Tokens are securely stored (encrypted)
4. You can now fetch data from that platform

### Supported Platforms

| Platform | Data Available |
|----------|----------------|
| **Shopify** | Orders, Products, Customers, Sales Analytics |
| **Meta Ads** | Ad Accounts, Campaigns, Ad Sets, Audience Insights |
| **Google Ads** | Customer Accounts, Campaigns, Keywords, Ad Groups |

## Testing

### Run All Tests

```bash
uv run pytest
```

### Run Property-Based Tests Only

```bash
uv run pytest tests/property/ -v
```

### Run with Coverage

```bash
uv run pytest --cov=credora
```

## Troubleshooting

### "OPENROUTER_API_KEY environment variable is not set"

Make sure you have:
1. Created a `.env` file in the project root
2. Added `OPENROUTER_API_KEY=your_key_here`
3. The key is valid (check on OpenRouter dashboard)

### "No module named 'agents'"

Run `uv sync` to install dependencies.

### Connection/OAuth Errors

- Ensure you have valid OAuth credentials for the platform
- Check that redirect URIs are correctly configured
- Verify the platform API is accessible

### Slow Responses

- The default model is free tier - consider upgrading for faster responses
- Check your internet connection
- OpenRouter may have rate limits on free tier

## Example Conversation

```
You: Hi, I'm new here. What can you do?

CFO Agent: Welcome to Credora! I'm your AI-powered virtual CFO. I can help you:
- Connect your e-commerce store (Shopify) and ad accounts (Meta, Google)
- Analyze your sales, revenue, and operational metrics
- Identify growth opportunities and bottlenecks
- Compare your performance to industry benchmarks
- Provide actionable recommendations to improve profitability

Would you like to get started by connecting your first platform?

You: Yes, let's connect my Shopify store

CFO Agent: Great! To connect your Shopify store, I'll need to initiate an OAuth 
authorization flow. This will allow Credora to securely access your store data 
in read-only mode.

[Provides OAuth URL for authorization]

You: Done! Now show me my sales from last month

CFO Agent: Here's your sales summary for the last 30 days:
- Total Revenue: $45,230.50
- Total Orders: 342
- Average Order Value: $132.25
- Conversion Rate: 3.2%
...
```

## License

Proprietary - Credora Team

## Support

For issues or questions, contact the development team.
