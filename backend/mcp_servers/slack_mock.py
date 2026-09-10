from fastapi import FastAPI

app = FastAPI(title="Mock Slack MCP Server")

SLACK_TOOLS = [
    {
        'name': 'read_channel',
        'description': 'Read messages and conversation history from a Slack channel',
        'inputSchema': {
            'type': 'object',
            'properties': {'channel': {'type': 'string'}, 'limit': {'type': 'integer', 'default': 20}},
            'required': ['channel']
        }
    },
    {
        'name': 'post_message',
        'description': 'Post a message to a Slack channel',
        'inputSchema': {
            'type': 'object',
            'properties': {'channel': {'type': 'string'}, 'text': {'type': 'string'}},
            'required': ['channel', 'text']
        }
    },
    {
        'name': 'delete_message',
        'description': 'Delete a message permanently from a Slack channel',
        'inputSchema': {
            'type': 'object',
            'properties': {'channel': {'type': 'string'}, 'ts': {'type': 'string'}},
            'required': ['channel', 'ts']
        }
    }
]

@app.get('/tools')
def list_tools():
    return {'tools': SLACK_TOOLS}

@app.post('/call/{tool_name}')
def call_tool(tool_name: str):
    if tool_name == 'read_channel':
        return {'result': [{'user': 'alice', 'text': 'Meeting at 3pm'}, {'user': 'bob', 'text': 'PR #4 approved'}]}
    elif tool_name == 'post_message':
        return {'result': {'status': 'posted', 'channel': 'engineering', 'ts': '1725983401.002100'}}
    elif tool_name == 'delete_message':
        return {'result': {'deleted': True}}
    return {'error': f'Unknown tool: {tool_name}'}
