from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List

from mcp_registry.client import introspect_mcp_server
from mcp_registry import store

router = APIRouter(prefix='/api/mcp', tags=['mcp_servers'])

class ServerCreate(BaseModel):
    name: str = Field(..., description="Server name e.g. github, slack, sqlite")
    transport: str = Field(default="http", description="http, sse, stdio")
    url: str = Field(..., description="Server endpoint URL or command")
    auth_type: str = Field(default="none", description="oauth, api_key, none")
    scope: str = Field(default="tenant", description="tenant (Just my workspace) or shared (Everyone in company)")
    description: Optional[str] = None

@router.post('/servers')
async def register_server(server_data: ServerCreate):
    """
    Step 1: Register an MCP server.
    Rule 1: Platform MUST connect to endpoint and read tools itself.
    Rule 2: '✕ If it does not answer, nothing is saved.'
    """
    # 1. Attempt connection & introspection
    introspection = await introspect_mcp_server(server_data.url, server_data.transport)
    
    if introspection.get('status') != 'ok':
        raise HTTPException(
            status_code=400,
            detail=f"✕ If it does not answer, nothing is saved. (Could not connect to '{server_data.url}')"
        )
    
    tools = introspection.get('tools', [])
    if not tools:
        raise HTTPException(
            status_code=400,
            detail=f"Connection succeeded but no tools were found at '{server_data.url}'. Nothing was saved."
        )
        
    # 2. Store server & classified tools
    new_server = store.add_server(
        name=server_data.name,
        url=server_data.url,
        transport=server_data.transport,
        auth_type=server_data.auth_type,
        scope=server_data.scope,
        description=server_data.description,
        status='ok',
        tools=tools
    )
    
    return new_server

@router.get('/servers')
async def list_servers(scope: Optional[str] = None):
    """List all registered MCP servers with tools."""
    return store.list_servers(scope=scope)

@router.get('/servers/{server_id}')
async def get_server(server_id: str):
    """Get details of a specific server."""
    server = store.get_server(server_id)
    if not server:
        raise HTTPException(status_code=404, detail='Server not found')
    return server

@router.post('/servers/{server_id}/refresh')
async def refresh_server(server_id: str):
    """Re-introspect an MCP server and update its status and tools."""
    server = store.get_server(server_id)
    if not server:
        raise HTTPException(status_code=404, detail='Server not found')
        
    introspection = await introspect_mcp_server(server['url'], server['transport'])
    new_status = 'ok' if introspection.get('status') == 'ok' else 'down'
    new_tools = introspection.get('tools') if new_status == 'ok' else None
    
    updated = store.update_server_health(server_id, status=new_status, new_tools=new_tools)
    return updated

@router.delete('/servers/{server_id}')
async def delete_server(server_id: str):
    """Delete a server from the registry."""
    if not store.delete_server(server_id):
        raise HTTPException(status_code=404, detail='Server not found')
    return {'status': 'deleted', 'id': server_id}

@router.post('/servers/{server_id}/toggle-connect')
async def toggle_connect(server_id: str):
    """Toggle connected state for credentials."""
    updated = store.toggle_connection(server_id)
    if not updated:
        raise HTTPException(status_code=404, detail='Server not found')
    return updated

@router.post('/health-check')
async def run_scheduled_health_check():
    """
    Requirement 4: Scheduled health check sweep.
    Re-checks every registered server and marks the dead ones.
    """
    servers = store.list_servers()
    results = []
    for s in servers:
        introspection = await introspect_mcp_server(s['url'], s['transport'])
        status = 'ok' if introspection.get('status') == 'ok' else 'down'
        new_tools = introspection.get('tools') if status == 'ok' else None
        store.update_server_health(s['id'], status=status, new_tools=new_tools)
        results.append({'id': s['id'], 'name': s['name'], 'status': status})
    return {'checked': len(results), 'servers': results}
