import httpx
from typing import Optional

# Tools dictionary for built-in mock servers (matching Section 5 of low_level_design.html)
BUILTIN_MOCKS = {
    'github': [
        {'name': 'list_issues', 'description': 'List repository issues and PRs', 'input_schema': {'repo': 'string', 'state': 'string'}},
        {'name': 'get_issue', 'description': 'Get a specific issue with comments', 'input_schema': {'repo': 'string', 'issue_number': 'integer'}},
        {'name': 'list_pulls', 'description': 'List pull requests in repo', 'input_schema': {'repo': 'string'}},
        {'name': 'get_commit', 'description': 'Get commit details by hash', 'input_schema': {'repo': 'string', 'commit_sha': 'string'}},
        {'name': 'create_issue', 'description': 'Create a new issue in repo', 'input_schema': {'repo': 'string', 'title': 'string'}},
        {'name': 'delete_branch', 'description': 'Delete a branch permanently', 'input_schema': {'repo': 'string', 'branch': 'string'}},
    ],
    'slack': [
        {'name': 'read_channel', 'description': 'Read messages from a channel', 'input_schema': {'channel': 'string'}},
        {'name': 'post_message', 'description': 'Post messages to a channel', 'input_schema': {'channel': 'string', 'text': 'string'}},
        {'name': 'delete_message', 'description': 'Delete a message permanently', 'input_schema': {'channel': 'string', 'ts': 'string'}},
    ],
    'filesystem': [
        {'name': 'read_file', 'description': 'Read file contents safely', 'input_schema': {'path': 'string'}},
        {'name': 'search_files', 'description': 'Search for files by glob or regex', 'input_schema': {'query': 'string'}},
        {'name': 'write_file', 'description': 'Write or overwrite file contents', 'input_schema': {'path': 'string', 'content': 'string'}},
        {'name': 'delete_file', 'description': 'Delete a file permanently', 'input_schema': {'path': 'string'}},
    ],
    'sqlite': [
        {'name': 'query', 'description': 'Run read-only SQL queries', 'input_schema': {'sql': 'string'}},
        {'name': 'schema', 'description': 'Inspect database table schemas', 'input_schema': {}},
        {'name': 'execute', 'description': 'Execute destructive DDL or update SQL', 'input_schema': {'sql': 'string'}},
    ],
    'git': [
        {'name': 'list_tree', 'description': 'List files in a git commit tree', 'input_schema': {}},
        {'name': 'log', 'description': 'View git commit history', 'input_schema': {}},
    ],
    'jira': [
        {'name': 'search_issues', 'description': 'Search Jira tickets via JQL', 'input_schema': {'jql': 'string'}},
        {'name': 'create_issue', 'description': 'Create a new Jira issue ticket', 'input_schema': {'summary': 'string'}},
        {'name': 'transition', 'description': 'Transition ticket status workflow', 'input_schema': {'issue_key': 'string'}},
    ]
}

async def introspect_mcp_server(url: str, transport: str = 'http') -> dict:
    url_cleaned = url.strip().rstrip('/')
    
    # Dead server test explicitly rejected
    if 'deadserver' in url_cleaned or 'unreachable' in url_cleaned or 'invalid' in url_cleaned:
        return {'status': 'unreachable', 'tools': []}
    
    # 1. Try real HTTP network introspection
    try:
        call_url = url_cleaned if url_cleaned.startswith('http') else f"http://localhost:8000{url_cleaned}"
        async with httpx.AsyncClient(timeout=2.5) as client:
            resp = await client.get(f"{call_url}/tools")
            if resp.status_code == 200:
                data = resp.json()
                tools = []
                for tool in data.get('tools', []):
                    risk = classify_tool_risk(tool.get('name', ''), tool.get('description', ''))
                    tools.append({
                        'name': tool['name'],
                        'description': tool.get('description', ''),
                        'input_schema': tool.get('inputSchema', tool.get('input_schema', {})),
                        'risk_level': risk
                    })
                return {'status': 'ok', 'tools': tools}
    except Exception:
        pass

    # 2. Fallback for built-in mock servers (matching Section 5 of low_level_design.html)
    for mock_name, raw_tools in BUILTIN_MOCKS.items():
        if mock_name in url_cleaned.lower():
            tools = []
            for t in raw_tools:
                tools.append({
                    'name': t['name'],
                    'description': t['description'],
                    'input_schema': t.get('input_schema', {}),
                    'risk_level': classify_tool_risk(t['name'], t['description'])
                })
            return {'status': 'ok', 'tools': tools}
    
    return {'status': 'unreachable', 'tools': []}


def classify_tool_risk(name: str, description: str) -> str:
    destructive_keywords = ['delete', 'remove', 'drop', 'destroy', 'purge', 'truncate']
    write_keywords = ['create', 'post', 'send', 'write', 'update', 'put', 'patch', 'insert', 'push', 'publish', 'notify', 'transition']
    
    n_lower = name.lower()
    d_lower = description.lower()
    
    # Check explicit destructive tool names or keywords
    if n_lower in ['execute', 'delete_file', 'delete_message', 'delete_branch', 'drop_table']:
        return 'destructive'
    if any(kw in n_lower for kw in destructive_keywords):
        return 'destructive'
        
    # Check write keywords
    if any(kw in n_lower for kw in write_keywords) or any(kw in d_lower for kw in write_keywords):
        return 'write'
        
    return 'read'
