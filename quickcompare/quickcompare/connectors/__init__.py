from .base import Connector, OrderResult
from .mock import MockConnector
from .manual import ManualConnector


def build_connector(name: str, platform_cfg: dict) -> Connector:
    kind = platform_cfg.get("connector", "mock")
    if kind == "mock":
        return MockConnector(name, platform_cfg)
    if kind == "manual":
        return ManualConnector(name, platform_cfg)
    if kind in ("swiggy_mcp", "zomato_mcp"):
        from .mcp_connector import MCPConnector
        return MCPConnector(name, platform_cfg, kind)
    raise ValueError(f"unknown connector {kind!r} for {name}")


__all__ = ["Connector", "OrderResult", "MockConnector", "ManualConnector", "build_connector"]
