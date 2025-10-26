#!/bin/bash
# Test trade commands wrapper for Claude Code slash command

# Parse arguments
SUITE="core"
FAST_FLAG=""
SYMBOL="BYND"

# Parse command line args
for arg in "$@"; do
    case $arg in
        core|ai|all)
            SUITE="$arg"
            ;;
        --fast)
            FAST_FLAG="--fast"
            ;;
        --symbol)
            shift
            SYMBOL="$1"
            ;;
    esac
done

# Run the test suite
cd /Users/franckjones/Desktop/trade_app
source venv/bin/activate
python3 test_trade_commands.py "$SUITE" $FAST_FLAG --symbol "$SYMBOL"
