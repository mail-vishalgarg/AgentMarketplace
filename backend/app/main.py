from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from mcp_registry.router import router as mcp_router
from mcp_servers.github_mock import app as github_mock_app
from mcp_servers.slack_mock import app as slack_mock_app
from mcp_servers.filesystem_mock import app as filesystem_mock_app
from mcp_servers.sqlite_mock import app as sqlite_mock_app
from mcp_servers.git_mock import app as git_mock_app
from mcp_servers.jira_mock import app as jira_mock_app

app = FastAPI(title="AgentMarketplace API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MCP Registry API routes
app.include_router(mcp_router)

# Mount Mock MCP Servers
app.mount("/mock/github", github_mock_app)
app.mount("/mock/slack", slack_mock_app)
app.mount("/mock/filesystem", filesystem_mock_app)
app.mount("/mock/sqlite", sqlite_mock_app)
app.mount("/mock/git", git_mock_app)
app.mount("/mock/jira", jira_mock_app)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}

