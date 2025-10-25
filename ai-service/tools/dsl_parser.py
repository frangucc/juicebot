"""
DSL Parser for Tool Invocation

Parses DSL syntax [tool_name(params)] in instruction files and prompts.
This keeps AI instructions readable and modular.

Examples:
    "[volume_last(5)]" → get_volume_stats(symbol, "5bars")
    "[price_high(today)]" → get_price_range(symbol, "today")
    "[detect_fvg(20)]" → detect_fvg(symbol, 20)
"""

import re
from typing import List, Dict, Any, Tuple


class DSLTool:
    """Represents a parsed tool invocation from DSL syntax."""

    def __init__(self, name: str, params: List[str], raw: str):
        self.name = name
        self.params = params
        self.raw = raw  # Original DSL string

    def __repr__(self):
        return f"DSLTool(name='{self.name}', params={self.params})"


class DSLParser:
    """Parse DSL tool invocations from text."""

    # Pattern: [tool_name(param1, param2, ...)]
    PATTERN = r'\[(\w+)\((.*?)\)\]'

    # Shorthand mappings: DSL name → actual tool function name
    TOOL_ALIASES = {
        "current_price": "get_current_price",
        "volume_last": "get_volume_stats",
        "volume_stats": "get_volume_stats",
        "price_high": "get_price_range",
        "price_low": "get_price_range",
        "price_range": "get_price_range",
        "get_bars": "get_historical_bars",
        "detect_fvg": "detect_fvg",
        "detect_bos": "detect_bos",
        "detect_choch": "detect_choch",
    }

    def __init__(self):
        self.tools: List[DSLTool] = []

    def parse(self, text: str) -> 'DSLParser':
        """
        Parse DSL tool invocations from text.

        Args:
            text: Text containing DSL syntax like [tool_name(params)]

        Returns:
            self (for chaining)
        """
        matches = re.findall(self.PATTERN, text)

        for match in matches:
            tool_name, params_str = match
            params = [p.strip() for p in params_str.split(',') if p.strip()] if params_str else []

            # Resolve alias
            resolved_name = self.TOOL_ALIASES.get(tool_name, tool_name)

            raw = f"[{tool_name}({params_str})]"
            self.tools.append(DSLTool(resolved_name, params, raw))

        return self

    def replace_with_results(self, text: str, results: Dict[str, Any]) -> str:
        """
        Replace DSL invocations with their results.

        Args:
            text: Original text with DSL syntax
            results: Dict mapping tool.raw → result string

        Returns:
            Text with DSL replaced by results
        """
        output = text

        for tool in self.tools:
            if tool.raw in results:
                output = output.replace(tool.raw, str(results[tool.raw]))

        return output

    async def execute_all(self, symbol: str, tool_functions: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute all parsed tools and return results.

        Args:
            symbol: Stock symbol for context
            tool_functions: Dict mapping tool name → async function

        Returns:
            Dict mapping tool.raw → result
        """
        results = {}

        for tool in self.tools:
            if tool.name not in tool_functions:
                results[tool.raw] = f"[ERROR: Unknown tool '{tool.name}']"
                continue

            func = tool_functions[tool.name]

            try:
                # Call tool function with symbol and params
                if tool.name in ["get_current_price"]:
                    result = await func(symbol)
                elif tool.name in ["get_volume_stats", "get_price_range"]:
                    period = tool.params[0] if tool.params else "today"
                    result = await func(symbol, period)
                elif tool.name in ["get_historical_bars", "detect_fvg", "detect_bos", "detect_choch"]:
                    limit = int(tool.params[0]) if tool.params else 50
                    result = await func(symbol, limit)
                else:
                    result = await func(symbol, *tool.params)

                # Format result for display
                if isinstance(result, dict):
                    # For single value results (like current_price)
                    if "price" in result:
                        results[tool.raw] = f"${result['price']:.2f}"
                    elif "relative_volume" in result:
                        results[tool.raw] = f"{result['relative_volume']}x avg"
                    elif "high" in result and "low" in result:
                        results[tool.raw] = f"${result['low']:.2f} - ${result['high']:.2f}"
                    else:
                        results[tool.raw] = str(result)
                elif isinstance(result, list):
                    # For list results (like FVGs, BoS)
                    results[tool.raw] = f"{len(result)} found"
                else:
                    results[tool.raw] = str(result)

            except Exception as e:
                results[tool.raw] = f"[ERROR: {str(e)}]"

        return results


def parse_dsl(text: str) -> DSLParser:
    """
    Convenience function to parse DSL from text.

    Usage:
        parser = parse_dsl("Check [volume_last(5)] and [price_high(today)]")
        print(parser.tools)  # [DSLTool(...), DSLTool(...)]
    """
    return DSLParser().parse(text)


# Example usage for testing
if __name__ == "__main__":
    # Test DSL parsing
    test_text = """
    Current setup:
    - Price: [current_price(BYND)]
    - Volume: [volume_last(5)]
    - Range: [price_range(today)]
    - FVGs found: [detect_fvg(50)]
    """

    parser = parse_dsl(test_text)
    print(f"Found {len(parser.tools)} tools:")
    for tool in parser.tools:
        print(f"  - {tool}")
