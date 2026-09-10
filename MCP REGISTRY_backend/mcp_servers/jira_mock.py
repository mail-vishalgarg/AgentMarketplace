from fastapi import FastAPI

app = FastAPI(title="Mock Jira MCP Server")

JIRA_TOOLS = [
    {'name': 'search_issues', 'description': 'Search Jira tickets via JQL query', 'inputSchema': {'type': 'object', 'properties': {'jql': {'type': 'string'}}}},
    {'name': 'create_issue', 'description': 'Create a new Jira issue ticket', 'inputSchema': {'type': 'object', 'properties': {'summary': {'type': 'string'}}}},
    {'name': 'transition', 'description': 'Transition ticket status workflow', 'inputSchema': {'type': 'object', 'properties': {'issue_key': {'type': 'string'}, 'status': {'type': 'string'}}}}
]

@app.get('/tools')
def list_tools():
    return {'tools': JIRA_TOOLS}
