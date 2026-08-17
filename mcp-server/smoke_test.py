"""End-to-end smoke test: drive the server over stdio the way a client will.

Run against a live FlowTrack:

    FLOWTRACK_API_URL=http://api:8000 FLOWTRACK_API_KEY=... python smoke_test.py
"""

import asyncio
import json
import os
import sys

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


def _text(result) -> str:
    parts = []
    for block in getattr(result, "content", []) or []:
        parts.append(getattr(block, "text", ""))
    return "\n".join(parts)


async def main() -> int:
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "flowtrack_mcp"],
        env={
            **os.environ,
            "FLOWTRACK_API_URL": os.environ["FLOWTRACK_API_URL"],
            "FLOWTRACK_API_KEY": os.environ["FLOWTRACK_API_KEY"],
        },
    )

    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        init = await session.initialize()
        print(f"  connected to {init.server_info.name} v{init.server_info.version}")

        tools = (await session.list_tools()).tools
        print(f"\n  tools ({len(tools)}):")
        for t in sorted(tools, key=lambda x: x.name):
            print(f"    - {t.name}")

        prompts = (await session.list_prompts()).prompts
        print(f"\n  prompts ({len(prompts)}):")
        for p in prompts:
            print(f"    - {p.name}")

        resources = (await session.list_resources()).resources
        templates = (await session.list_resource_templates()).resource_templates
        print(f"\n  resources: {[str(r.uri) for r in resources]}")
        print(f"  resource templates: {[t.uri_template for t in templates]}")

        print("\n  portfolio_digest:")
        digest = json.loads(_text(await session.call_tool("portfolio_digest", {})))
        print(f"    totals: {digest['totals']}")
        print(f"    wip: {digest['wip']}")
        print(f"    stale: {len(digest['stale'])} projects over {digest['stale_threshold_days']} days")
        for row in digest["stale"][:3]:
            print(f"      {row['days_since_touched']:>4}d  {row['name'][:44]}")
        print(f"    overdue: {len(digest['overdue'])}")
        if digest["widest_completion_gaps"]:
            g = digest["widest_completion_gaps"][0]
            print(f"    widest gap: {g['name'][:40]} ({g['gap']:+d} points)")

        print("\n  list_projects(min_stars=5):")
        top = json.loads(_text(await session.call_tool("list_projects", {"min_stars": 5})))
        for row in top["projects"]:
            print(f"    {'*' * (row['stars'] or 0):<5} {row['name'][:46]}")

        print("\n  resource flowtrack://portfolio:")
        content = await session.read_resource("flowtrack://portfolio")
        body = content.contents[0].text
        print(f"    {len(body)} chars, {body.count(chr(10)) + 1} lines")
        print("    " + body.splitlines()[0])

        print("\n  prompt 'reckoning':")
        got = await session.get_prompt("reckoning", {"stale_days": "45"})
        first = got.messages[0].content
        print(f"    {len(getattr(first, 'text', ''))} chars")

        print("\n  OK")
        return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
