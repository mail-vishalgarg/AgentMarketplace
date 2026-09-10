import unittest
from fastapi.testclient import TestClient
from main import app
from mcp_registry.client import classify_tool_risk
from mcp_registry import store

client = TestClient(app)

class TestMCPRegistry(unittest.TestCase):

    def test_classify_tool_risk(self):
        """Test keyword classification for read, write, and destructive tools."""
        self.assertEqual(classify_tool_risk("list_issues", "List open issues"), "read")
        self.assertEqual(classify_tool_risk("get_issue", "Fetch issue details"), "read")
        self.assertEqual(classify_tool_risk("create_issue", "Create a new issue"), "write")
        self.assertEqual(classify_tool_risk("post_message", "Post to Slack channel"), "write")
        self.assertEqual(classify_tool_risk("transition", "Transition ticket"), "write")
        self.assertEqual(classify_tool_risk("delete_file", "Delete a file permanently"), "destructive")
        self.assertEqual(classify_tool_risk("execute", "Execute drop table query"), "destructive")
        self.assertEqual(classify_tool_risk("delete_branch", "Delete git branch"), "destructive")

    def test_dead_server_aborts_and_saves_nothing(self):
        """
        Step 1 Rule:
        The server does not answer -> Registration aborted. Nothing was saved.
        """
        initial_servers = len(store.list_servers())
        
        res = client.post("/api/mcp/servers", json={
            "name": "dead-server",
            "transport": "http",
            "url": "http://localhost:8000/mock/deadserver",
            "auth_type": "api_key",
            "scope": "tenant"
        })
        
        # Must return HTTP 400
        self.assertEqual(res.status_code, 400)
        self.assertIn("Connection failed: The server at 'http://localhost:8000/mock/deadserver' did not answer", res.json()["detail"])
        self.assertIn("Registration aborted. Nothing was saved.", res.json()["detail"])
        
        # Check nothing was saved
        final_servers = len(store.list_servers())
        self.assertEqual(initial_servers, final_servers)

    def test_valid_server_introspection_and_save(self):
        """
        Step 1 Success:
        Platform connects to server, reads tools, classifies, and saves.
        """
        res = client.post("/api/mcp/servers", json={
            "name": "sqlite-custom",
            "transport": "stdio",
            "url": "http://localhost:8000/mock/sqlite",
            "auth_type": "none",
            "scope": "shared",
            "description": "Custom SQLite database"
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["name"], "sqlite-custom")
        self.assertEqual(len(data["tools"]), 3)
        
        # Verify tool risk classifications
        tool_risks = {t["name"]: t["risk_level"] for t in data["tools"]}
        self.assertEqual(tool_risks.get("query"), "read")
        self.assertEqual(tool_risks.get("schema"), "read")
        self.assertEqual(tool_risks.get("execute"), "destructive")

    def test_list_servers(self):
        """Test listing servers with tool counts and statuses."""
        res = client.get("/api/mcp/servers")
        self.assertEqual(res.status_code, 200)
        servers = res.json()
        names = [s["name"] for s in servers]
        self.assertIn("github", names)
        self.assertIn("slack", names)
        self.assertIn("jira", names)

if __name__ == "__main__":
    unittest.main()
