"""
MCP Tools Implementation.

Example tools demonstrating MCP tool capabilities:
- get_weather: Get weather for a location
- calculate: Perform mathematical calculations
- get_current_time: Get current time
- echo: Echo back input
- generate_uuid: Generate a UUID
"""

import math
import random
import uuid
from datetime import datetime
from typing import Any, Dict, List

import structlog

from .models import Tool, ToolCallResponse, ToolContent, ToolInputSchema

logger = structlog.get_logger()


# ============================================================================
# Tool Registry
# ============================================================================


class ToolRegistry:
    """Registry of available MCP tools."""

    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        self._handlers: Dict[str, callable] = {}
        self._register_builtin_tools()

    def _register_builtin_tools(self):
        """Register all built-in tools."""
        self.register(
            Tool(
                name="get_weather",
                description="Get the current weather for a location",
                inputSchema=ToolInputSchema(
                    type="object",
                    properties={
                        "location": {
                            "type": "string",
                            "description": "City name or zip code",
                        },
                        "units": {
                            "type": "string",
                            "description": "Temperature units (celsius or fahrenheit)",
                            "enum": ["celsius", "fahrenheit"],
                        },
                    },
                    required=["location"],
                ),
            ),
            get_weather,
        )

        self.register(
            Tool(
                name="calculate",
                description="Perform a mathematical calculation",
                inputSchema=ToolInputSchema(
                    type="object",
                    properties={
                        "expression": {
                            "type": "string",
                            "description": "Mathematical expression to evaluate (e.g., '2 + 2', 'sqrt(16)')",
                        }
                    },
                    required=["expression"],
                ),
            ),
            calculate,
        )

        self.register(
            Tool(
                name="get_current_time",
                description="Get the current date and time",
                inputSchema=ToolInputSchema(
                    type="object",
                    properties={
                        "timezone": {
                            "type": "string",
                            "description": "Timezone name (e.g., 'UTC', 'America/New_York')",
                        },
                        "format": {
                            "type": "string",
                            "description": "Output format ('iso', 'unix', or 'human')",
                            "enum": ["iso", "unix", "human"],
                        },
                    },
                    required=[],
                ),
            ),
            get_current_time,
        )

        self.register(
            Tool(
                name="echo",
                description="Echo back the provided message",
                inputSchema=ToolInputSchema(
                    type="object",
                    properties={
                        "message": {
                            "type": "string",
                            "description": "Message to echo back",
                        },
                        "repeat": {
                            "type": "integer",
                            "description": "Number of times to repeat (1-10)",
                            "minimum": 1,
                            "maximum": 10,
                        },
                    },
                    required=["message"],
                ),
            ),
            echo,
        )

        self.register(
            Tool(
                name="generate_uuid",
                description="Generate a new UUID (Universally Unique Identifier)",
                inputSchema=ToolInputSchema(
                    type="object",
                    properties={
                        "version": {
                            "type": "integer",
                            "description": "UUID version (1 or 4)",
                            "enum": [1, 4],
                        }
                    },
                    required=[],
                ),
            ),
            generate_uuid_tool,
        )

        self.register(
            Tool(
                name="random_number",
                description="Generate a random number",
                inputSchema=ToolInputSchema(
                    type="object",
                    properties={
                        "min": {
                            "type": "number",
                            "description": "Minimum value (inclusive)",
                        },
                        "max": {
                            "type": "number",
                            "description": "Maximum value (inclusive)",
                        },
                        "integer": {
                            "type": "boolean",
                            "description": "Return an integer (true) or float (false)",
                        },
                    },
                    required=["min", "max"],
                ),
            ),
            random_number,
        )

    def register(self, tool: Tool, handler: callable):
        """Register a tool with its handler."""
        self._tools[tool.name] = tool
        self._handlers[tool.name] = handler
        logger.info("tool_registered", tool_name=tool.name)

    def list_tools(self) -> List[Tool]:
        """Get list of all available tools."""
        return list(self._tools.values())

    def get_tool(self, name: str) -> Tool:
        """Get a specific tool by name."""
        if name not in self._tools:
            raise ValueError(f"Tool not found: {name}")
        return self._tools[name]

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> ToolCallResponse:
        """Call a tool with the given arguments."""
        if name not in self._handlers:
            return ToolCallResponse(
                content=[
                    ToolContent(
                        type="text",
                        text=f"Error: Tool '{name}' not found",
                    )
                ],
                isError=True,
            )

        try:
            logger.info("tool_call_starting", tool_name=name, arguments=arguments)
            result = self._handlers[name](arguments)
            logger.info("tool_call_completed", tool_name=name)
            return result
        except Exception as e:
            logger.error("tool_call_failed", tool_name=name, error=str(e), exc_info=True)
            return ToolCallResponse(
                content=[
                    ToolContent(
                        type="text",
                        text=f"Error executing tool '{name}': {str(e)}",
                    )
                ],
                isError=True,
            )


# ============================================================================
# Tool Handlers
# ============================================================================


def get_weather(arguments: Dict[str, Any]) -> ToolCallResponse:
    """
    Get weather for a location (fake implementation).

    Returns simulated weather data.
    """
    location = arguments.get("location", "Unknown")
    units = arguments.get("units", "fahrenheit")

    # Simulate weather data
    conditions = ["Sunny", "Partly Cloudy", "Cloudy", "Rainy", "Snowy"]
    condition = random.choice(conditions)

    if units == "celsius":
        temp = random.randint(-10, 35)
        unit_symbol = "°C"
    else:
        temp = random.randint(14, 95)
        unit_symbol = "°F"

    humidity = random.randint(30, 90)
    wind_speed = random.randint(0, 30)

    weather_text = f"""Weather for {location}:
Temperature: {temp}{unit_symbol}
Condition: {condition}
Humidity: {humidity}%
Wind Speed: {wind_speed} mph

Note: This is simulated weather data for demonstration purposes."""

    return ToolCallResponse(
        content=[
            ToolContent(
                type="text",
                text=weather_text,
            )
        ],
        isError=False,
    )


def calculate(arguments: Dict[str, Any]) -> ToolCallResponse:
    """
    Perform a mathematical calculation.

    Supports basic arithmetic and common math functions.
    """
    expression = arguments.get("expression", "")

    if not expression:
        return ToolCallResponse(
            content=[ToolContent(type="text", text="Error: No expression provided")],
            isError=True,
        )

    try:
        # Safe eval with limited scope
        allowed_names = {
            "abs": abs,
            "round": round,
            "min": min,
            "max": max,
            "sum": sum,
            "pow": pow,
            "sqrt": math.sqrt,
            "sin": math.sin,
            "cos": math.cos,
            "tan": math.tan,
            "log": math.log,
            "log10": math.log10,
            "exp": math.exp,
            "pi": math.pi,
            "e": math.e,
        }

        # Evaluate expression
        result = eval(expression, {"__builtins__": {}}, allowed_names)

        return ToolCallResponse(
            content=[
                ToolContent(
                    type="text",
                    text=f"Result: {result}\n\nExpression: {expression}",
                )
            ],
            isError=False,
        )

    except Exception as e:
        return ToolCallResponse(
            content=[
                ToolContent(
                    type="text",
                    text=f"Error evaluating expression: {str(e)}",
                )
            ],
            isError=True,
        )


def get_current_time(arguments: Dict[str, Any]) -> ToolCallResponse:
    """Get the current date and time."""
    format_type = arguments.get("format", "iso")
    timezone = arguments.get("timezone", "UTC")

    now = datetime.utcnow()

    if format_type == "unix":
        result = f"Unix timestamp: {int(now.timestamp())}"
    elif format_type == "human":
        result = f"Current time: {now.strftime('%A, %B %d, %Y at %I:%M:%S %p')} {timezone}"
    else:  # iso
        result = f"ISO 8601: {now.isoformat()}Z (timezone: {timezone})"

    return ToolCallResponse(
        content=[ToolContent(type="text", text=result)],
        isError=False,
    )


def echo(arguments: Dict[str, Any]) -> ToolCallResponse:
    """Echo back the provided message."""
    message = arguments.get("message", "")
    repeat = arguments.get("repeat", 1)

    # Validate repeat count
    if not isinstance(repeat, int) or repeat < 1 or repeat > 10:
        repeat = 1

    result = "\n".join([message] * repeat)

    return ToolCallResponse(
        content=[ToolContent(type="text", text=result)],
        isError=False,
    )


def generate_uuid_tool(arguments: Dict[str, Any]) -> ToolCallResponse:
    """Generate a new UUID."""
    version = arguments.get("version", 4)

    if version == 1:
        new_uuid = uuid.uuid1()
        uuid_type = "UUID v1 (time-based)"
    else:
        new_uuid = uuid.uuid4()
        uuid_type = "UUID v4 (random)"

    result = f"{uuid_type}: {str(new_uuid)}"

    return ToolCallResponse(
        content=[ToolContent(type="text", text=result)],
        isError=False,
    )


def random_number(arguments: Dict[str, Any]) -> ToolCallResponse:
    """Generate a random number."""
    min_val = arguments.get("min", 0)
    max_val = arguments.get("max", 100)
    is_integer = arguments.get("integer", True)

    if min_val > max_val:
        return ToolCallResponse(
            content=[
                ToolContent(
                    type="text",
                    text="Error: min value cannot be greater than max value",
                )
            ],
            isError=True,
        )

    if is_integer:
        number = random.randint(int(min_val), int(max_val))
    else:
        number = random.uniform(min_val, max_val)

    result = f"Random number between {min_val} and {max_val}: {number}"

    return ToolCallResponse(
        content=[ToolContent(type="text", text=result)],
        isError=False,
    )


# ============================================================================
# Global Tool Registry Instance
# ============================================================================

tool_registry = ToolRegistry()
