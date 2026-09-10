from fastapi import FastAPI

app = FastAPI(title="Mock Git MCP Server")

GIT_TOOLS = [
    {'name': 'list_tree', 'description': 'List files in a git repository tree', 'inputSchema': {'type': 'object'}},
    {'name': 'log', 'description': 'View git commit history and authors', 'inputSchema': {'type': 'object'}}
]

@app.get('/tools')
def list_tools():
    return {'tools': GIT_TOOLS}
