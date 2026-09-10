from fastapi import FastAPI

app = FastAPI(title="Mock SQLite MCP Server")

SQLITE_TOOLS = [
    {'name': 'query', 'description': 'Execute read-only SQL query against database', 'inputSchema': {'type': 'object', 'properties': {'sql': {'type': 'string'}}}},
    {'name': 'schema', 'description': 'Inspect database tables and schema', 'inputSchema': {'type': 'object'}},
    {'name': 'execute', 'description': 'Execute destructive or mutating SQL command', 'inputSchema': {'type': 'object', 'properties': {'sql': {'type': 'string'}}}}
]

@app.get('/tools')
def list_tools():
    return {'tools': SQLITE_TOOLS}
