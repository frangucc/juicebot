#!/bin/bash
# Check status of all services

echo "📊 Trading SMS Assistant - Service Status"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

check_service() {
    local name=$1
    local port=$2
    local pidfile=".pids/${name}.pid"

    printf "%-15s" "$name:"

    if [ -f "$pidfile" ]; then
        pid=$(cat "$pidfile")
        if ps -p "$pid" > /dev/null 2>&1; then
            echo -e "${GREEN}✓ Running${NC} (PID: $pid)"
            if [ ! -z "$port" ]; then
                if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
                    echo "                  Port $port: ${GREEN}Listening${NC}"
                else
                    echo "                  Port $port: ${RED}Not listening${NC}"
                fi
            fi
        else
            echo -e "${RED}✗ Stopped${NC} (stale PID)"
        fi
    else
        echo -e "${YELLOW}○ Not started${NC}"
    fi
}

# Check if services directory exists
if [ ! -d .pids ]; then
    echo -e "${YELLOW}No services running (no PID directory found)${NC}"
    echo ""
    echo "Start services with: ./start.sh"
    exit 0
fi

# Check each service
check_service "API" "8000"
check_service "Screener" ""
check_service "Dashboard" "3000"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check if all running
if [ -f .pids/api.pid ] && [ -f .pids/screener.pid ] && [ -f .pids/dashboard.pid ]; then
    api_pid=$(cat .pids/api.pid)
    screener_pid=$(cat .pids/screener.pid)
    dashboard_pid=$(cat .pids/dashboard.pid)

    if ps -p "$api_pid" > /dev/null 2>&1 && \
       ps -p "$screener_pid" > /dev/null 2>&1 && \
       ps -p "$dashboard_pid" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ All services running!${NC}"
        echo ""
        echo "📊 Dashboard:  http://localhost:3000"
        echo "🔧 API:        http://localhost:8000"
        echo "📖 API Docs:   http://localhost:8000/docs"
        echo ""
        echo "View logs:"
        echo "  tail -f .pids/screener.log"
        echo "  tail -f .pids/api.log"
        echo "  tail -f .pids/dashboard.log"
    else
        echo -e "${YELLOW}⚠️  Some services not running${NC}"
        echo "Start with: ./start.sh"
    fi
else
    echo -e "${YELLOW}⚠️  Services not fully started${NC}"
    echo "Start with: ./start.sh"
fi

echo ""
