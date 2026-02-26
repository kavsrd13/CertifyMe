"""
mcp_tools/mslearn_mcp.py — Microsoft Learn MCP integration
Uses the hosted MCP tool via AzureAIAgentClient (agent-framework SDK).
"""

import os
import asyncio
from dotenv import load_dotenv
from agents.client import agent_client

load_dotenv()

MCP_URL = os.getenv("MSLEARN_MCP_URL", "https://learn.microsoft.com/api/mcp")

_MOCK_SEARCH = [
    {
        "title": "Microsoft Learn — Official Documentation",
        "url": "https://learn.microsoft.com/en-us/",
        "description": "Explore Microsoft's official learning platform.",
    },
    {
        "title": "Microsoft Certification Overview",
        "url": "https://learn.microsoft.com/en-us/certifications/",
        "description": "Browse all Microsoft certifications.",
    },
]


learn_mcp = None
mslearn_search_agent = None

if agent_client:
    learn_mcp = agent_client.get_mcp_tool(
        name="Microsoft Learn MCP",
        url=MCP_URL,
    )

    mslearn_search_agent = agent_client.as_agent(
        name="MSLearnSearchAgent",
        instructions="Search Microsoft Learn and return relevant documentation links and summaries.",
        tools=[learn_mcp],
    )

async def _query_mslearn(query: str) -> str:
    """Ask the MS Learn MCP-powered agent a question and return its text response."""
    if not mslearn_search_agent:
        raise ValueError("MSLearnSearchAgent is not configured.")
    return await mslearn_search_agent.run(query)


def search_mslearn(query: str) -> list[dict]:
    """
    Search MS Learn via hosted MCP tool.
    Returns mock results on failure (keeps pipeline running in dev/offline).
    """
    try:
        answer = asyncio.run(_query_mslearn(query))
        # The agent returns a natural-language answer; wrap it as a single result
        return [{"title": "MS Learn MCP Result", "url": MCP_URL, "description": answer}]
    except Exception:
        return _MOCK_SEARCH
