from fastapi import FastAPI

app = FastAPI(title="Mock Filesystem MCP Server")

FS_TOOLS = [
    {'name': 'read_file', 'description': 'Read file contents safely from disk', 'inputSchema': {'type': 'object', 'properties': {'path': {'type': 'string'}}}},
    {'name': 'search_files', 'description': 'Search for files by pattern or text', 'inputSchema': {'type': 'object', 'properties': {'query': {'type': 'string'}}}},
    {'name': 'write_file', 'description': 'Write data or update file on disk', 'inputSchema': {'type': 'object', 'properties': {'path': {'type': 'string'}, 'content': {'type': 'string'}}}},
    {'name': 'delete_file', 'description': 'Delete a file permanently from disk', 'inputSchema': {'type': 'object', 'properties': {'path': {'type': 'string'}}}}
]

@app.get('/tools')
def list_tools():
    return {'tools': FS_TOOLS}
