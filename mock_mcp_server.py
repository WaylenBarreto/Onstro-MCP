import sys
import json
import asyncio
import os
from pm_mcp.repositories.mock_repository import MockRepository
from pm_mcp.tools.insights import InsightsTools

os.environ["MOCK_MODE"] = "true"

async def handle_request(req, tools):
    method = req.get("method")
    params = req.get("params", {})
    req_id = req.get("id")

    if method == "tools/call":
        name = params.get("name")
        args = params.get("arguments", {})
        
        try:
            if name == "get_member_insights":
                result = await tools.get_member_insights(member_id=args.get("member_id"))
            elif name == "get_project_insights":
                result = await tools.get_project_insights(project_id=args.get("project_id"))
            else:
                return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": "Method not found"}}
            
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(result)}]
                }
            }
        except Exception as e:
            return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32000, "message": str(e)}}
    
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": "Method not found"}}

async def main():
    repo = MockRepository()
    tools = InsightsTools(repo)
    
    # Read from stdin continuously
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        
        try:
            req = json.loads(line)
            res = await handle_request(req, tools)
            sys.stdout.write(json.dumps(res) + "\n")
            sys.stdout.flush()
        except json.JSONDecodeError:
            err = {"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error"}}
            sys.stdout.write(json.dumps(err) + "\n")
            sys.stdout.flush()

if __name__ == "__main__":
    asyncio.run(main())
