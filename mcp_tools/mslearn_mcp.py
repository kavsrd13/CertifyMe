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

def _fallback_openai_search(query: str) -> list[dict]:
    import re
    import json
    import urllib.parse
    from openai import AzureOpenAI
    
    try:
        client = AzureOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("AZURE_OPENAI_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
        )
        deployment = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME") or os.getenv("AZURE_OPENAI_DEPLOYMENT")
        
        response = client.chat.completions.create(
            model=deployment,
            messages=[
                {
                    "role": "system", 
                    "content": 'You are a Microsoft Learn search API simulator. Return exactly a JSON array containing 3 highly relevant and specific Microsoft Learn learning paths or titles for the EXACT query provided. Since you cannot guess exact URLs, you MUST construct the URL as a Microsoft Learn search link matching the title. Format: https://learn.microsoft.com/en-us/search/?terms=<url-encoded-keywords>. OUTPUT ONLY VALID JSON, NO MARKDOWN FENCES.'
                },
                {"role": "user", "content": f"Search Microsoft Learn specifically for: {query}"}
            ],
            temperature=0.7
        )
        
        text = response.choices[0].message.content
        text = re.sub(r"```(?:json)?\s*", "", text).strip()
        text = re.sub(r"```\s*$", "", text).strip()
        
        results = json.loads(text)
        
        # Ensure all URLs are actually search URLs based on the title to avoid 404s
        for r in results:
            if "search/?terms=" not in r.get("url", ""):
                 terms = urllib.parse.quote_plus(r.get("title", query))
                 r["url"] = f"https://learn.microsoft.com/en-us/search/?terms={terms}"
                 
        return results
    except Exception as e:
        print(f"Fallback OpenAI search failed: {e}")
        return _MOCK_SEARCH


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
    Returns simulated results on failure (keeps pipeline running in dev/offline).
    """
    try:
        answer = asyncio.run(_query_mslearn(query))
        # The agent returns a natural-language answer; wrap it as a single result
        return [{"title": "MS Learn MCP Result", "url": MCP_URL, "description": answer}]
    except Exception:
        return _fallback_openai_search(query)
