"""
MCP Protocol Models

Pydantic models for the Model Context Protocol (MCP) JSON-RPC interface.
"""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class MCPToolParam(BaseModel):
    """A single parameter definition for an MCP tool."""
    name: str
    description: str
    type: str
    required: bool = True
    default: Optional[Any] = None

    class Config:
        use_enum_values = True


class MCPTool(BaseModel):
    """An MCP tool definition exposed by the server."""
    name: str
    description: str
    parameters: List[MCPToolParam]

    class Config:
        use_enum_values = True


class MCPRequest(BaseModel):
    """An incoming MCP JSON-RPC request."""
    jsonrpc: str = "2.0"
    id: Optional[Union[str, int]] = None
    method: str
    params: Optional[Dict[str, Any]] = None

    class Config:
        use_enum_values = True


class MCPResponse(BaseModel):
    """An outgoing MCP JSON-RPC response."""
    jsonrpc: str = "2.0"
    id: Optional[Union[str, int]] = None
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None

    class Config:
        use_enum_values = True


class MCPServerConfig(BaseModel):
    """Configuration for the Asgard MCP server."""
    host: str = "localhost"
    port: int = 8765
    project_path: str = "."
    enable_quality: bool = True
    enable_security: bool = True
    enable_sbom: bool = True
    enable_gate: bool = True
    enable_ratings: bool = True
    auth_token: Optional[str] = Field(default=None, description="Required bearer token for HTTP access")
    expose: bool = Field(default=False, description="Allow binding 0.0.0.0 / ::")
    max_body_bytes: int = Field(default=1_048_576, description="Max JSON-RPC request body")

    class Config:
        use_enum_values = True
