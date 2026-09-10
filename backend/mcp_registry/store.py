import uuid
from datetime import datetime, timezone

# In-memory storage for MCP servers and tools
_servers = {}  # id -> server dict
_tools = {}    # id -> tool dict

def _seed_default_servers():
    """Seed initial servers matching the exact Forge capstone specification and mockup."""
    if _servers:
        return
        
    now = datetime.now(timezone.utc).isoformat()
    
    seeds = [
        {
            "id": "srv-github",
            "name": "github",
            "transport": "http",
            "url": "http://localhost:8000/mock/github",
            "auth_type": "api_key",
            "scope": "shared",
            "status": "ok",
            "connected": True,
            "description": "Issues, pull requests, commits and repository trees.",
            "last_checked_at": "12m ago",
            "tools": [
                {"name": "list_issues", "description": "List repository issues and PRs", "risk_level": "read"},
                {"name": "get_issue", "description": "Get a specific issue with comments", "risk_level": "read"},
                {"name": "list_pulls", "description": "List pull requests in repo", "risk_level": "read"},
                {"name": "get_commit", "description": "Get commit details by hash", "risk_level": "read"},
                {"name": "create_issue", "description": "Create a new issue in repo", "risk_level": "write"},
                {"name": "delete_branch", "description": "Delete a branch permanently", "risk_level": "destructive"},
            ]
        },
        {
            "id": "srv-slack",
            "name": "slack",
            "transport": "http",
            "url": "http://localhost:8000/mock/slack",
            "auth_type": "oauth",
            "scope": "shared",
            "status": "ok",
            "connected": False,  # Shows "Connect" button in mockup!
            "description": "Read channels and post messages to a workspace.",
            "last_checked_at": "12m ago",
            "tools": [
                {"name": "read_channel", "description": "Read messages from a channel", "risk_level": "read"},
                {"name": "post_message", "description": "Post messages to a channel", "risk_level": "write"},
                {"name": "delete_message", "description": "Delete a message permanently", "risk_level": "destructive"},
            ]
        },
        {
            "id": "srv-filesystem",
            "name": "filesystem",
            "transport": "stdio",
            "url": "http://localhost:8000/mock/filesystem",
            "auth_type": "none",
            "scope": "shared",
            "status": "ok",
            "connected": True,
            "description": "Read and search files in a mounted directory.",
            "last_checked_at": "12m ago",
            "tools": [
                {"name": "read_file", "description": "Read file contents safely", "risk_level": "read"},
                {"name": "search_files", "description": "Search for files by glob or regex", "risk_level": "read"},
                {"name": "write_file", "description": "Write or overwrite file contents", "risk_level": "write"},
                {"name": "delete_file", "description": "Delete a file permanently", "risk_level": "destructive"},
            ]
        },
        {
            "id": "srv-sqlite",
            "name": "sqlite",
            "transport": "stdio",
            "url": "http://localhost:8000/mock/sqlite",
            "auth_type": "none",
            "scope": "shared",
            "status": "ok",
            "connected": True,
            "description": "Query a local SQLite database.",
            "last_checked_at": "12m ago",
            "tools": [
                {"name": "query", "description": "Execute read-only SQL queries", "risk_level": "read"},
                {"name": "schema", "description": "Inspect database table schemas", "risk_level": "read"},
                {"name": "execute", "description": "Execute destructive DDL or update SQL", "risk_level": "destructive"},
            ]
        },
        {
            "id": "srv-git",
            "name": "git",
            "transport": "stdio",
            "url": "http://localhost:8000/mock/git",
            "auth_type": "none",
            "scope": "shared",
            "status": "ok",
            "connected": True,
            "description": "Inspect a local git repository.",
            "last_checked_at": "12m ago",
            "tools": [
                {"name": "list_tree", "description": "List files in a git commit tree", "risk_level": "read"},
                {"name": "log", "description": "View git commit history", "risk_level": "read"},
            ]
        },
        {
            "id": "srv-jira",
            "name": "jira",
            "transport": "http",
            "url": "http://localhost:8000/mock/jira",
            "auth_type": "api_key",
            "scope": "tenant",  # Private to Northwind Labs
            "status": "down",   # Down status for scheduled check & failure demo!
            "connected": True,
            "description": "Internal Jira. Registered by Northwind Labs — private to this workspace.",
            "last_checked_at": "9m ago",
            "tools": [
                {"name": "search_issues", "description": "Search Jira tickets via JQL", "risk_level": "read"},
                {"name": "create_issue", "description": "Create a new Jira issue ticket", "risk_level": "write"},
                {"name": "transition", "description": "Transition ticket status workflow", "risk_level": "write"},
            ]
        }
    ]
    
    for s in seeds:
        srv_id = s["id"]
        server_record = {
            "id": srv_id,
            "name": s["name"],
            "transport": s["transport"],
            "url": s["url"],
            "auth_type": s["auth_type"],
            "scope": s["scope"],
            "status": s["status"],
            "connected": s["connected"],
            "description": s["description"],
            "last_checked_at": s["last_checked_at"],
            "created_at": now,
            "updated_at": now,
            "tools": []
        }
        for t in s["tools"]:
            tool_id = str(uuid.uuid4())
            tool_record = {
                "id": tool_id,
                "server_id": srv_id,
                "name": t["name"],
                "description": t.get("description", ""),
                "risk_level": t.get("risk_level", "read"),
                "created_at": now
            }
            _tools[tool_id] = tool_record
            server_record["tools"].append(tool_record)
            
        _servers[srv_id] = server_record

# Seed on load
_seed_default_servers()

def add_server(name: str, url: str, transport: str, auth_type: str, scope: str, description: str, status: str, tools: list) -> dict:
    server_id = f"srv-{name.lower()}-{uuid.uuid4().hex[:4]}"
    now = datetime.now(timezone.utc).isoformat()
    
    server = {
        'id': server_id,
        'name': name.lower(),
        'url': url,
        'transport': transport,
        'auth_type': auth_type,
        'scope': scope,
        'description': description or f"{name.capitalize()} MCP tool server.",
        'status': status,
        'connected': True,
        'created_at': now,
        'updated_at': now,
        'last_checked_at': 'just now',
        'tools': []
    }
    
    for t in tools:
        tool_id = str(uuid.uuid4())
        tool_record = {
            'id': tool_id,
            'server_id': server_id,
            'name': t['name'],
            'description': t.get('description', ''),
            'input_schema': t.get('input_schema', {}),
            'risk_level': t.get('risk_level', 'read'),
            'created_at': now
        }
        _tools[tool_id] = tool_record
        server['tools'].append(tool_record)
    
    _servers[server_id] = server
    return server

def list_servers(scope: str = None) -> list:
    result = []
    for s in _servers.values():
        if scope and s.get('scope') != scope:
            continue
        s_copy = dict(s)
        s_copy['tools'] = [t for t in _tools.values() if t['server_id'] == s['id']]
        result.append(s_copy)
    return result

def get_server(server_id: str) -> dict | None:
    server = _servers.get(server_id)
    if not server:
        return None
    s_copy = dict(server)
    s_copy['tools'] = [t for t in _tools.values() if t['server_id'] == server_id]
    return s_copy

def delete_server(server_id: str) -> bool:
    if server_id not in _servers:
        return False
    tool_ids = [tid for tid, t in _tools.items() if t['server_id'] == server_id]
    for tid in tool_ids:
        del _tools[tid]
    del _servers[server_id]
    return True

def toggle_connection(server_id: str, connected: bool = None) -> dict | None:
    server = _servers.get(server_id)
    if not server:
        return None
    if connected is not None:
        server['connected'] = connected
    else:
        server['connected'] = not server.get('connected', False)
    return server

def update_server_health(server_id: str, status: str, new_tools: list = None) -> dict | None:
    server = _servers.get(server_id)
    if not server:
        return None
    server['status'] = status
    server['last_checked_at'] = 'just now'
    if new_tools is not None:
        tool_ids = [tid for tid, t in _tools.items() if t['server_id'] == server_id]
        for tid in tool_ids:
            del _tools[tid]
        server['tools'] = []
        now = datetime.now(timezone.utc).isoformat()
        for t in new_tools:
            tool_id = str(uuid.uuid4())
            tool_record = {
                'id': tool_id,
                'server_id': server_id,
                'name': t['name'],
                'description': t.get('description', ''),
                'input_schema': t.get('input_schema', {}),
                'risk_level': t.get('risk_level', 'read'),
                'created_at': now
            }
            _tools[tool_id] = tool_record
            server['tools'].append(tool_record)
    return server
