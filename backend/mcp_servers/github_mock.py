from fastapi import FastAPI

app = FastAPI(title="Mock GitHub MCP Server")

GITHUB_TOOLS = [
    {
        'name': 'list_issues',
        'description': 'List all open issues and pull requests in a repository',
        'inputSchema': {
            'type': 'object',
            'properties': {
                'repo': {'type': 'string', 'description': 'Repository name (owner/repo)'},
                'state': {'type': 'string', 'enum': ['open', 'closed', 'all'], 'default': 'open'}
            },
            'required': ['repo']
        }
    },
    {
        'name': 'get_issue',
        'description': 'Get details of a specific issue including comments',
        'inputSchema': {
            'type': 'object',
            'properties': {
                'repo': {'type': 'string'},
                'issue_number': {'type': 'integer'}
            },
            'required': ['repo', 'issue_number']
        }
    },
    {
        'name': 'list_pulls',
        'description': 'List pull requests in repository',
        'inputSchema': {
            'type': 'object',
            'properties': {'repo': {'type': 'string'}}
        }
    },
    {
        'name': 'get_commit',
        'description': 'Get commit details by hash',
        'inputSchema': {
            'type': 'object',
            'properties': {'repo': {'type': 'string'}, 'commit_sha': {'type': 'string'}}
        }
    },
    {
        'name': 'create_issue',
        'description': 'Create a new issue in a GitHub repository',
        'inputSchema': {
            'type': 'object',
            'properties': {
                'repo': {'type': 'string'},
                'title': {'type': 'string'},
                'body': {'type': 'string'}
            },
            'required': ['repo', 'title']
        }
    },
    {
        'name': 'delete_branch',
        'description': 'Delete a branch from the repository permanently',
        'inputSchema': {
            'type': 'object',
            'properties': {'repo': {'type': 'string'}, 'branch': {'type': 'string'}},
            'required': ['repo', 'branch']
        }
    }
]

@app.get('/tools')
def list_tools():
    return {'tools': GITHUB_TOOLS}

@app.post('/call/{tool_name}')
def call_tool(tool_name: str):
    if tool_name == 'list_issues':
        return {
            'result': [
                {'number': 1, 'title': 'Fix login timeout', 'state': 'open', 'labels': ['bug', 'critical']},
                {'number': 2, 'title': 'Add dark mode support', 'state': 'open', 'labels': ['enhancement']},
                {'number': 3, 'title': 'API rate limit errors', 'state': 'open', 'labels': ['bug']}
            ]
        }
    elif tool_name == 'get_issue':
        return {'result': {'number': 1, 'title': 'Fix login timeout', 'state': 'open', 'body': 'Users report timeout after 30s'}}
    elif tool_name == 'create_issue':
        return {'result': {'number': 4, 'title': 'New Issue', 'state': 'open', 'created': True}}
    elif tool_name == 'delete_branch':
        return {'result': {'branch': 'feature-old', 'deleted': True}}
    return {'error': f'Unknown tool: {tool_name}'}
