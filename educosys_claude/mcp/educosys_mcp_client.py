import shutil
from langchain_mcp_adapters.client import MultiServerMCPClient
from educosys_claude.mcp.educosys_mcp_config import load_educosys_mcp_configs
from educosys_claude.observability.logger import get_logger

logger = get_logger(__name__)


async def get_educosys_mcp_tools() -> list:
    """Connect to all configured MCP servers and return their tools."""
    configs = load_educosys_mcp_configs()
    if not configs:
        logger.info("No MCP servers configured.")
        return []

    active_configs = {}
    for name, srv_config in configs.items():
        if name == "github":
            token = srv_config.get("env", {}).get("GITHUB_PERSONAL_ACCESS_TOKEN", "")
            if not token:
                logger.warning("GITHUB_TOKEN is not set. Skipping GitHub MCP server.")
                continue

        cmd = srv_config.get("command")
        if cmd:
            resolved_cmd = shutil.which(cmd)
            if resolved_cmd:
                srv_config = dict(srv_config)
                srv_config["command"] = resolved_cmd

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
