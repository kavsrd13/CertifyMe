"""
agents/client.py — Shared Client Configuration

Provides initialized AzureChatClient and AzureAIAgentClient
instances to be shared across all modular agents.
"""

import os
from dotenv import load_dotenv
from azure.identity import AzureCliCredential
from azure.identity.aio import AzureCliCredential as AioAzureCliCredential
from agent_framework.azure import AzureOpenAIChatClient, AzureAIAgentClient

load_dotenv()


def _bootstrap_env():
    """Map common environment variables to what the framework expects."""
    if not os.getenv("AZURE_OPENAI_API_KEY") and os.getenv("AZURE_OPENAI_KEY"):
        os.environ["AZURE_OPENAI_API_KEY"] = os.environ["AZURE_OPENAI_KEY"]
    if not os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME") and os.getenv("AZURE_OPENAI_DEPLOYMENT"):
        os.environ["AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"] = os.environ["AZURE_OPENAI_DEPLOYMENT"]


# Run environment bootstrapping once on module import
_bootstrap_env()

# Sync Chat Client for normal agent orchestration
chat_client = AzureOpenAIChatClient(credential=AzureCliCredential())

# Async AIAgentClient for MCP tools (Requires Azure AI Project Endpoint)
agent_client = None
if os.getenv("AZURE_AI_PROJECT_ENDPOINT") or os.getenv("AZURE_AI_PROJECT_CONNECTION_STRING"):
    try:
        agent_client = AzureAIAgentClient(credential=AioAzureCliCredential())
    except Exception as e:
        print(f"Warning: Could not initialize AzureAIAgentClient: {e}")
