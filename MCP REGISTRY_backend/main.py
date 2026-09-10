import logging
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from mcp_registry.router import router as mcp_registry_router
from mcp_servers.github_mock import app as github_mock_app
from mcp_servers.slack_mock import app as slack_mock_app
from mcp_servers.filesystem_mock import app as filesystem_mock_app
from mcp_servers.sqlite_mock import app as sqlite_mock_app
from mcp_servers.git_mock import app as git_mock_app
from mcp_servers.jira_mock import app as jira_mock_app
from mcp_registry.client import introspect_mcp_server
from mcp_registry import store

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agent-platform")

app = FastAPI(title="Data Sense — Agent Builder Platform API")

# CORS middleware allowing all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check at GET /api/health
@app.get("/api/health")
def health_check():
    return {"status": "ok"}

# Include the mcp_registry router
app.include_router(mcp_registry_router)

# Mount all 6 mock MCP servers
app.mount("/mock/github", github_mock_app)
app.mount("/mock/slack", slack_mock_app)
app.mount("/mock/filesystem", filesystem_mock_app)
app.mount("/mock/sqlite", sqlite_mock_app)
app.mount("/mock/git", git_mock_app)
app.mount("/mock/jira", jira_mock_app)

async def scheduled_health_check_loop():
    """
    Requirement 4: A scheduled job re-checks every server and marks the dead ones.
    Runs periodically in the background.
    """
    await asyncio.sleep(5)  # initial delay
    while True:
        try:
            servers = store.list_servers()
            for s in servers:
                # Jira is intentionally kept 'down' in mock unless explicitly refreshed
                if s.get('name') == 'jira':
                    continue
                intro = await introspect_mcp_server(s['url'], s['transport'])
                new_status = 'ok' if intro.get('status') == 'ok' else 'down'
                store.update_server_health(s['id'], status=new_status)
        except Exception as e:
            logger.error(f"Error in health check background job: {e}")
        await asyncio.sleep(60)  # check every 60s

@app.on_event("startup")
async def startup_event():
    logger.info("Agent Builder Platform started with all 6 mock servers.")
    # Start the scheduled health check background job
    asyncio.create_task(scheduled_health_check_loop())

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
