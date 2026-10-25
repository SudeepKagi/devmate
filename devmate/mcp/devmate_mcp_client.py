from langchain_mcp_adapters.client import MultiServerMCPClient
from devmate.mcp.devmate_mcp_config import load_devmate_mcp_configs
from devmate.observability.logger import get_logger

logger = get_logger(__name__)


async def get_devmate_mcp_tools() -> list:
    """Connect to all configured MCP servers and return their tools."""
    configs = load_devmate_mcp_configs()
    if not configs:
        logger.info("No MCP servers configured.")
        return []

    # Filter out github server if GITHUB_TOKEN is not configured to avoid hangs/failures
    active_configs = {}
    for name, srv_config in configs.items():
        if name == "github":
            token = srv_config.get("env", {}).get("GITHUB_PERSONAL_ACCESS_TOKEN", "")
            if not token:
                logger.warning("GITHUB_TOKEN is not set. Skipping GitHub MCP server.")
                continue
        active_configs[name] = srv_config

    if not active_configs:
        logger.info("No active MCP servers to connect to.")
        return []

    logger.info(f"Connecting to MCP servers: {list(active_configs.keys())}")
    try:
        client = MultiServerMCPClient(active_configs)
        tools = await client.get_tools()
        logger.info(f"Loaded {len(tools)} tools from MCP servers")
        return tools
    except Exception as e:
        logger.error(f"Error connecting to MCP servers: {e}")
        return []
