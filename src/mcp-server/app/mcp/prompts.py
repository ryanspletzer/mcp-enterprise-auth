"""
MCP Prompts Implementation.

Example prompts demonstrating MCP prompt capabilities:
- Greeting prompts
- Task-specific prompts
- Data analysis prompts
"""

from typing import Callable, Dict, List

import structlog

from .models import Prompt, PromptArgument, PromptGetResponse, PromptMessage

logger = structlog.get_logger()


# ============================================================================
# Prompt Registry
# ============================================================================


class PromptRegistry:
    """Registry of available MCP prompts."""

    def __init__(self) -> None:
        self._prompts: Dict[str, Prompt] = {}
        self._handlers: Dict[str, Callable[[Dict[str, str]], PromptGetResponse]] = {}
        self._register_builtin_prompts()

    def _register_builtin_prompts(self) -> None:
        """Register all built-in prompts."""

        # Greeting prompt
        self.register(
            Prompt(
                name="greeting",
                description="Generate a personalized greeting",
                arguments=[
                    PromptArgument(
                        name="name",
                        description="Name of the person to greet",
                        required=True,
                    ),
                    PromptArgument(
                        name="time_of_day",
                        description="Time of day (morning, afternoon, evening)",
                        required=False,
                    ),
                ],
            ),
            greeting_prompt,
        )

        # Weather query prompt
        self.register(
            Prompt(
                name="weather_query",
                description="Generate a weather query for a location",
                arguments=[
                    PromptArgument(
                        name="location",
                        description="Location to query weather for",
                        required=True,
                    ),
                    PromptArgument(
                        name="detail_level",
                        description="Level of detail (basic, detailed, forecast)",
                        required=False,
                    ),
                ],
            ),
            weather_query_prompt,
        )

        # Code review prompt
        self.register(
            Prompt(
                name="code_review",
                description="Generate a code review prompt",
                arguments=[
                    PromptArgument(
                        name="language",
                        description="Programming language",
                        required=True,
                    ),
                    PromptArgument(
                        name="focus_area",
                        description="Focus area (security, performance, style, all)",
                        required=False,
                    ),
                ],
            ),
            code_review_prompt,
        )

        # Data analysis prompt
        self.register(
            Prompt(
                name="data_analysis",
                description="Generate a data analysis prompt",
                arguments=[
                    PromptArgument(
                        name="dataset_type",
                        description="Type of dataset (csv, json, database)",
                        required=True,
                    ),
                    PromptArgument(
                        name="analysis_goal",
                        description="Goal of the analysis",
                        required=False,
                    ),
                ],
            ),
            data_analysis_prompt,
        )

        # Summarization prompt
        self.register(
            Prompt(
                name="summarize",
                description="Generate a summarization prompt",
                arguments=[
                    PromptArgument(
                        name="content_type",
                        description=(
                            "Type of content to summarize (article, document, conversation)"
                        ),
                        required=True,
                    ),
                    PromptArgument(
                        name="length",
                        description="Desired summary length (short, medium, long)",
                        required=False,
                    ),
                ],
            ),
            summarize_prompt,
        )

        # Troubleshooting prompt
        self.register(
            Prompt(
                name="troubleshoot",
                description="Generate a troubleshooting prompt",
                arguments=[
                    PromptArgument(
                        name="system",
                        description="System or technology being troubleshot",
                        required=True,
                    ),
                    PromptArgument(
                        name="error_type",
                        description="Type of error (connection, auth, config, other)",
                        required=False,
                    ),
                ],
            ),
            troubleshoot_prompt,
        )

    def register(
        self, prompt: Prompt, handler: Callable[[Dict[str, str]], PromptGetResponse]
    ) -> None:
        """Register a prompt with its handler."""
        self._prompts[prompt.name] = prompt
        self._handlers[prompt.name] = handler
        logger.info("prompt_registered", prompt_name=prompt.name)

    def list_prompts(self) -> List[Prompt]:
        """Get list of all available prompts."""
        return list(self._prompts.values())

    def get_prompt(self, name: str) -> Prompt:
        """Get a specific prompt by name."""
        if name not in self._prompts:
            raise ValueError(f"Prompt not found: {name}")
        return self._prompts[name]

    def generate_prompt(self, name: str, arguments: Dict[str, str]) -> PromptGetResponse:
        """Generate a prompt with the given arguments."""
        if name not in self._handlers:
            raise ValueError(f"Prompt not found: {name}")

        try:
            logger.info("prompt_generation_starting", prompt_name=name, arguments=arguments)
            result = self._handlers[name](arguments)
            logger.info("prompt_generation_completed", prompt_name=name)
            return result
        except Exception as e:
            logger.error("prompt_generation_failed", prompt_name=name, error=str(e), exc_info=True)
            raise


# ============================================================================
# Prompt Handlers
# ============================================================================


def greeting_prompt(arguments: Dict[str, str]) -> PromptGetResponse:
    """Generate a personalized greeting prompt."""
    name = arguments.get("name", "there")
    time_of_day = arguments.get("time_of_day", "")

    if time_of_day:
        greeting = f"Good {time_of_day}"
    else:
        greeting = "Hello"

    prompt_text = f"{greeting}, {name}! I'm the MCP server assistant. How can I help you today?"

    return PromptGetResponse(
        description=f"Personalized greeting for {name}",
        messages=[
            PromptMessage(
                role="user",
                content={
                    "type": "text",
                    "text": "Please greet me in a friendly and professional manner.",
                },
            ),
            PromptMessage(
                role="assistant",
                content={
                    "type": "text",
                    "text": prompt_text,
                },
            ),
        ],
    )


def weather_query_prompt(arguments: Dict[str, str]) -> PromptGetResponse:
    """Generate a weather query prompt."""
    location = arguments.get("location", "your location")
    detail_level = arguments.get("detail_level", "basic")

    if detail_level == "detailed":
        query = (
            f"Please provide detailed weather information for {location}, "
            "including temperature, conditions, humidity, wind speed, and any weather alerts."
        )
    elif detail_level == "forecast":
        query = (
            f"Please provide a weather forecast for {location} for the next 5 days, "
            "including daily highs, lows, and conditions."
        )
    else:
        query = f"What's the current weather in {location}?"

    return PromptGetResponse(
        description=f"Weather query for {location}",
        messages=[
            PromptMessage(
                role="user",
                content={
                    "type": "text",
                    "text": query,
                },
            ),
        ],
    )


def code_review_prompt(arguments: Dict[str, str]) -> PromptGetResponse:
    """Generate a code review prompt."""
    language = arguments.get("language", "")
    focus_area = arguments.get("focus_area", "all")

    focus_instructions = {
        "security": (
            "Focus particularly on security vulnerabilities, input validation, "
            "and potential attack vectors."
        ),
        "performance": (
            "Focus on performance optimizations, algorithmic efficiency, and resource usage."
        ),
        "style": "Focus on code style, readability, naming conventions, and best practices.",
        "all": "Review for security, performance, style, and overall code quality.",
    }

    instruction = focus_instructions.get(focus_area, focus_instructions["all"])

    prompt_text = f"""Please review the following {language} code.

{instruction}

Provide specific, actionable feedback with examples where appropriate."""

    return PromptGetResponse(
        description=f"Code review prompt for {language}",
        messages=[
            PromptMessage(
                role="user",
                content={
                    "type": "text",
                    "text": prompt_text,
                },
            ),
        ],
    )


def data_analysis_prompt(arguments: Dict[str, str]) -> PromptGetResponse:
    """Generate a data analysis prompt."""
    dataset_type = arguments.get("dataset_type", "")
    analysis_goal = arguments.get("analysis_goal", "general insights")

    prompt_text = f"""Please analyze the following {dataset_type} dataset.

Analysis Goal: {analysis_goal}

Please provide:
1. Summary statistics and key metrics
2. Notable patterns or trends
3. Potential insights and recommendations
4. Data quality observations (missing values, outliers, etc.)

Present your findings in a clear, structured format."""

    return PromptGetResponse(
        description=f"Data analysis prompt for {dataset_type}",
        messages=[
            PromptMessage(
                role="user",
                content={
                    "type": "text",
                    "text": prompt_text,
                },
            ),
        ],
    )


def summarize_prompt(arguments: Dict[str, str]) -> PromptGetResponse:
    """Generate a summarization prompt."""
    content_type = arguments.get("content_type", "text")
    length = arguments.get("length", "medium")

    length_instructions = {
        "short": "in 2-3 sentences",
        "medium": "in 1-2 paragraphs",
        "long": "in 3-4 paragraphs with detailed key points",
    }

    length_instruction = length_instructions.get(length, length_instructions["medium"])

    prompt_text = f"""Please summarize the following {content_type} {length_instruction}.

Focus on:
- Main ideas and key points
- Important conclusions or takeaways
- Critical details that shouldn't be omitted

Keep the summary clear, accurate, and well-organized."""

    return PromptGetResponse(
        description=f"Summarization prompt for {content_type}",
        messages=[
            PromptMessage(
                role="user",
                content={
                    "type": "text",
                    "text": prompt_text,
                },
            ),
        ],
    )


def troubleshoot_prompt(arguments: Dict[str, str]) -> PromptGetResponse:
    """Generate a troubleshooting prompt."""
    system = arguments.get("system", "the system")
    error_type = arguments.get("error_type", "")

    error_focus = ""
    if error_type == "connection":
        error_focus = "network connectivity, firewall rules, and endpoint availability"
    elif error_type == "auth":
        error_focus = "authentication credentials, permissions, and token validity"
    elif error_type == "config":
        error_focus = "configuration settings, environment variables, and file permissions"
    else:
        error_focus = "common issues and their solutions"

    prompt_text = f"""I'm experiencing issues with {system}.

Please help me troubleshoot by:
1. Asking relevant diagnostic questions
2. Suggesting specific checks to perform
3. Providing step-by-step troubleshooting steps

{f'Pay special attention to {error_focus}.' if error_focus else ''}

Let's work through this systematically to identify and resolve the issue."""

    return PromptGetResponse(
        description=f"Troubleshooting prompt for {system}",
        messages=[
            PromptMessage(
                role="user",
                content={
                    "type": "text",
                    "text": prompt_text,
                },
            ),
        ],
    )


# ============================================================================
# Global Prompt Registry Instance
# ============================================================================

prompt_registry = PromptRegistry()
