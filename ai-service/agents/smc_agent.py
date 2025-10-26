"""
Smart Money Concepts (SMC) Agent

Expert trading assistant specialized in SMC patterns: FVG, BoS, CHoCH
"""

import os
from typing import List, Dict, Any
import anthropic
from pathlib import Path

from agents.base_agent import BaseAgent
from tools import (
    get_current_price,
    get_volume_stats,
    get_price_range,
    get_historical_bars,
    detect_fvg,
    detect_bos,
    detect_choch,
    detect_pattern_confluence
)
from tools.volume_analysis import (
    get_volume_profile,
    get_relative_volume,
    get_vwap,
    get_volume_trend
)


class SMCAgent(BaseAgent):
    """Smart Money Concepts trading agent."""

    def __init__(self):
        super().__init__(name="SMC Agent", strategy="smart_money_concepts")
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.model = "claude-sonnet-4-20250514"  # Claude Sonnet 4.5

        # Load instructions
        instructions_dir = Path(__file__).parent.parent / "instructions"
        with open(instructions_dir / "smc_strategy.md", "r") as f:
            self.smc_instructions = f.read()
        with open(instructions_dir / "position_clerk.md", "r") as f:
            self.clerk_instructions = f.read()

        # Tool definitions for Claude
        self.tools = [
            {
                "name": "get_current_price",
                "description": "Get the current price and latest bar data for the symbol",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "symbol": {
                            "type": "string",
                            "description": "Stock symbol (e.g., 'BYND')"
                        }
                    },
                    "required": ["symbol"]
                }
            },
            {
                "name": "get_volume_stats",
                "description": "Get volume statistics including average volume and relative volume",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "symbol": {"type": "string"},
                        "period": {
                            "type": "string",
                            "description": "Time period: 'today', '1h', '20bars'",
                            "default": "today"
                        }
                    },
                    "required": ["symbol"]
                }
            },
            {
                "name": "get_price_range",
                "description": "Get price range (high/low) for a period",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "symbol": {"type": "string"},
                        "period": {
                            "type": "string",
                            "description": "Time period: 'today', '1h', '20bars'",
                            "default": "today"
                        }
                    },
                    "required": ["symbol"]
                }
            },
            {
                "name": "detect_fvg",
                "description": "Detect Fair Value Gaps (FVG) - bullish or bearish gaps in price action",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "symbol": {"type": "string"},
                        "lookback": {
                            "type": "integer",
                            "description": "Number of bars to analyze",
                            "default": 50
                        }
                    },
                    "required": ["symbol"]
                }
            },
            {
                "name": "detect_bos",
                "description": "Detect Break of Structure (BoS) - trend continuation signals",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "symbol": {"type": "string"},
                        "lookback": {
                            "type": "integer",
                            "description": "Number of bars to analyze",
                            "default": 50
                        }
                    },
                    "required": ["symbol"]
                }
            },
            {
                "name": "detect_choch",
                "description": "Detect Change of Character (CHoCH) - potential trend reversal signals",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "symbol": {"type": "string"},
                        "lookback": {
                            "type": "integer",
                            "description": "Number of bars to analyze",
                            "default": 50
                        }
                    },
                    "required": ["symbol"]
                }
            },
            {
                "name": "detect_pattern_confluence",
                "description": "Detect confluence zones where multiple SMC patterns align (FVG + BoS, FVG + CHoCH). High confluence zones have stronger predictive power.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "symbol": {"type": "string"},
                        "lookback": {
                            "type": "integer",
                            "description": "Number of bars to analyze",
                            "default": 50
                        }
                    },
                    "required": ["symbol"]
                }
            },
            {
                "name": "get_volume_profile",
                "description": "Get Volume Profile (VP) - shows price levels with highest volume concentration, Point of Control (POC), and Value Area",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "symbol": {"type": "string"},
                        "lookback": {
                            "type": "integer",
                            "description": "Number of bars to analyze",
                            "default": 100
                        }
                    },
                    "required": ["symbol"]
                }
            },
            {
                "name": "get_relative_volume",
                "description": "Get Relative Volume (RVOL) - compares recent volume to earlier session. Shows if volume is cold/normal/hot/explosive",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "symbol": {"type": "string"},
                        "period": {
                            "type": "integer",
                            "description": "Number of bars to compare (compares last N vs previous N)",
                            "default": 20
                        }
                    },
                    "required": ["symbol"]
                }
            },
            {
                "name": "get_vwap",
                "description": "Get Volume-Weighted Average Price (VWAP) - shows average price weighted by volume. Key level for institutional traders",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "symbol": {"type": "string"},
                        "lookback": {
                            "type": "integer",
                            "description": "Number of bars to analyze (390 = full day)",
                            "default": 390
                        }
                    },
                    "required": ["symbol"]
                }
            },
            {
                "name": "get_volume_trend",
                "description": "Analyze volume trend - shows if volume is increasing/decreasing and if there's a recent spike. Helps identify momentum",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "symbol": {"type": "string"},
                        "lookback": {
                            "type": "integer",
                            "description": "Number of bars to analyze",
                            "default": 50
                        }
                    },
                    "required": ["symbol"]
                }
            }
        ]

    def get_system_prompt(self, symbol: str) -> str:
        """Generate system prompt with symbol context."""
        return f"""{self.smc_instructions}

{self.clerk_instructions}

---

## Current Context
Symbol: {symbol}
Strategy: Smart Money Concepts (SMC)

Remember:
- Focus ONLY on {symbol}
- Use tools to analyze the chart
- Be concise and actionable
- Track positions when user enters trades
"""

    async def analyze(self, symbol: str, user_message: str, bar_history: list = None) -> tuple[str, str]:
        """
        Analyze market data and respond to user message using Claude.

        Args:
            symbol: Stock symbol being analyzed
            user_message: User's question or request
            bar_history: List of bar data from WebSocket feed

        Returns:
            Tuple of (agent's response, system prompt used)
        """
        # Store bar_history for tool execution
        self.bar_history = bar_history or []

        # Add user message to history
        self.add_message("user", user_message)

        # Build messages for Claude API
        messages = self.get_conversation_messages()

        # Get system prompt (we'll return this)
        system_prompt = self.get_system_prompt(symbol)

        # Call Claude with tool use
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system_prompt,
            tools=self.tools,
            messages=messages
        )

        # Process tool calls
        while response.stop_reason == "tool_use":
            # Extract tool calls and execute them
            tool_results = []

            for content_block in response.content:
                if content_block.type == "tool_use":
                    tool_name = content_block.name
                    tool_input = content_block.input
                    tool_use_id = content_block.id

                    # Execute the tool
                    result = await self._execute_tool(tool_name, tool_input)

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,
                        "content": str(result)
                    })

            # Add assistant's tool use to history
            assistant_message = {
                "role": "assistant",
                "content": response.content
            }

            # Continue conversation with tool results
            messages.append(assistant_message)
            messages.append({
                "role": "user",
                "content": tool_results
            })

            # Get next response
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=self.get_system_prompt(symbol),
                tools=self.tools,
                messages=messages
            )

        # Extract final text response
        final_response = ""
        for content_block in response.content:
            if hasattr(content_block, "text"):
                final_response += content_block.text

        # Add to history
        self.add_message("assistant", final_response)

        return final_response, system_prompt

    async def _execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> Any:
        """Execute a tool function by name."""
        tool_functions = {
            "get_current_price": get_current_price,
            "get_volume_stats": get_volume_stats,
            "get_price_range": get_price_range,
            "detect_fvg": detect_fvg,
            "detect_bos": detect_bos,
            "detect_choch": detect_choch,
            "detect_pattern_confluence": detect_pattern_confluence,
            "get_volume_profile": get_volume_profile,
            "get_relative_volume": get_relative_volume,
            "get_vwap": get_vwap,
            "get_volume_trend": get_volume_trend
        }

        if tool_name not in tool_functions:
            return {"error": f"Unknown tool: {tool_name}"}

        func = tool_functions[tool_name]

        try:
            # All tools now need bar_history parameter
            bar_history = getattr(self, 'bar_history', [])

            # Call with appropriate parameters including bar_history
            if tool_name in ["get_current_price"]:
                result = await func(tool_input["symbol"], bar_history)
            elif tool_name in ["get_volume_stats", "get_price_range"]:
                result = await func(
                    tool_input["symbol"],
                    bar_history,
                    tool_input.get("period", "today")
                )
            elif tool_name in ["detect_fvg", "detect_bos", "detect_choch", "detect_pattern_confluence"]:
                result = await func(
                    tool_input["symbol"],
                    bar_history,
                    tool_input.get("lookback", 50)
                )
            elif tool_name in ["get_volume_profile", "get_vwap", "get_volume_trend"]:
                # Volume profile, VWAP, and volume trend with lookback parameter
                result = await func(
                    tool_input["symbol"],
                    bar_history,
                    tool_input.get("lookback", 100 if tool_name == "get_volume_profile" else (390 if tool_name == "get_vwap" else 50))
                )
            elif tool_name == "get_relative_volume":
                # Relative volume with period parameter
                result = await func(
                    tool_input["symbol"],
                    bar_history,
                    tool_input.get("period", 20)
                )
            else:
                result = await func(**tool_input)

            return result

        except Exception as e:
            return {"error": str(e)}
