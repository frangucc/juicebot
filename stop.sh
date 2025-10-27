#!/bin/bash
# Stop all services for Trading SMS Assistant

echo "🛑 Stopping Trading SMS Assistant..."
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

# Function to stop a service
stop_service() {
    local name=$1
    local pidfile=".pids/${name}.pid"

    if [ -f "$pidfile" ]; then
        pid=$(cat "$pidfile")
        if ps -p "$pid" > /dev/null 2>&1; then
            echo "${RED}Stopping ${name} (PID: $pid)...${NC}"
            kill "$pid" 2>/dev/null || true

            # Wait up to 5 seconds for graceful shutdown
            for i in {1..5}; do
                if ! ps -p "$pid" > /dev/null 2>&1; then
                    break
                fi
                sleep 1
            done

            # Force kill if still running
            if ps -p "$pid" > /dev/null 2>&1; then
                echo "  Force killing..."
                kill -9 "$pid" 2>/dev/null || true
            fi

            rm "$pidfile"
            echo "${GREEN}✓ ${name} stopped${NC}"
        else
            echo "  ${name} not running (stale PID file)"
            rm "$pidfile"
        fi
    else
        echo "  ${name} PID file not found"
    fi
}

# Stop all services
if [ -d .pids ]; then
    stop_service "dashboard"
    stop_service "api"
    stop_service "ai-service"
    stop_service "historical-ws"
    stop_service "screener"

    # Clean up any remaining processes on ports
    echo ""
    echo "Cleaning up ports..."

    # Kill any process on port 3000 (Dashboard)
    lsof -ti:3000 | xargs kill -9 2>/dev/null || true

    # Kill any process on port 8000 (API)
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true

    # Kill any process on port 8001 (Historical WebSocket)
    lsof -ti:8001 | xargs kill -9 2>/dev/null || true

    # Kill any process on port 8002 (AI Service)
    lsof -ti:8002 | xargs kill -9 2>/dev/null || true

    echo "${GREEN}✓ Ports cleaned (3000, 8000, 8001, 8002)${NC}"

    # Clear Next.js build cache to force recompile
    if [ -d dashboard/.next ]; then
        echo "Clearing Next.js build cache..."
        rm -rf dashboard/.next
        echo "${GREEN}✓ Next.js cache cleared${NC}"
    fi
else
    echo "No PID directory found. Services may not be running."

    # Try to kill by port anyway
    echo "Attempting to clean up ports..."
    lsof -ti:3000 | xargs kill -9 2>/dev/null || true
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true
    lsof -ti:8001 | xargs kill -9 2>/dev/null || true
    lsof -ti:8002 | xargs kill -9 2>/dev/null || true
fi

echo ""
echo "${GREEN}✅ All services stopped!${NC}"
echo ""
