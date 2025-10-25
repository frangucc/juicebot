#!/bin/bash
# Start all services for Trading SMS Assistant

set -e

echo "🚀 Starting Trading SMS Assistant..."
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found!"
    exit 1
fi

# Check if venv exists
if [ ! -d venv ]; then
    echo "${YELLOW}⚠️  Virtual environment not found. Creating...${NC}"
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Check if node_modules exists in dashboard
if [ ! -d dashboard/node_modules ]; then
    echo "${YELLOW}⚠️  Dashboard dependencies not found. Installing...${NC}"
    cd dashboard
    npm install
    cd ..
fi

# Create PID directory
mkdir -p .pids

# Function to start a service
start_service() {
    local name=$1
    local command=$2
    local pidfile=".pids/${name}.pid"
    local logfile=".pids/${name}.log"

    echo "${BLUE}Starting ${name}...${NC}"

    # Kill existing process if running
    if [ -f "$pidfile" ]; then
        old_pid=$(cat "$pidfile")
        if ps -p "$old_pid" > /dev/null 2>&1; then
            echo "  Killing old process (PID: $old_pid)"
            kill "$old_pid" 2>/dev/null || true
            sleep 1
        fi
    fi

    # Start new process
    eval "$command" > "$logfile" 2>&1 &
    echo $! > "$pidfile"

    echo "${GREEN}✓ ${name} started (PID: $(cat $pidfile))${NC}"
    echo "  Log: $logfile"
    echo ""
}

# Start API server
start_service "api" "uvicorn api.main:app --host 0.0.0.0 --port 8000"

# Start Historical WebSocket Server (separate thread for historical data replay)
start_service "historical-ws" "python -u historical_websocket_server.py --port 8001"

# Give servers time to start
sleep 2

# Start Screener (unbuffered for real-time logging)
start_service "screener" "python -u -m screener.main --threshold 0.03"

# Start Dashboard
start_service "dashboard" "cd dashboard && npm run dev"

echo ""
echo "${GREEN}✅ All services started!${NC}"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Dashboard:          http://localhost:3000"
echo "🔧 API:                http://localhost:8000"
echo "📖 API Docs:           http://localhost:8000/docs"
echo "📡 Historical WebSocket: ws://localhost:8001"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Services & Ports:"
echo "  • API Server          → Port 8000  (REST endpoints)"
echo "  • Historical WS       → Port 8001  (Bar-by-bar replay)"
echo "  • Dashboard           → Port 3000  (Next.js UI)"
echo "  • Screener            → Background (Databento live feed)"
echo ""
echo "PIDs:"
echo "  • API:         $(cat .pids/api.pid 2>/dev/null || echo 'N/A')"
echo "  • Historical:  $(cat .pids/historical-ws.pid 2>/dev/null || echo 'N/A')"
echo "  • Screener:    $(cat .pids/screener.pid 2>/dev/null || echo 'N/A')"
echo "  • Dashboard:   $(cat .pids/dashboard.pid 2>/dev/null || echo 'N/A')"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "To view logs:"
echo "  ${BLUE}tail -f .pids/screener.log${NC}       # Screener output"
echo "  ${BLUE}tail -f .pids/api.log${NC}            # API output"
echo "  ${BLUE}tail -f .pids/historical-ws.log${NC}  # Historical WebSocket output"
echo "  ${BLUE}tail -f .pids/dashboard.log${NC}      # Dashboard output"
echo ""
echo "To stop all services:"
echo "  ${BLUE}./stop.sh${NC}"
echo ""
echo "Press Ctrl+C to stop (will leave services running)"
echo "Use ./stop.sh to properly shutdown all services"
echo ""

# Keep script running and tail logs
tail -f .pids/*.log
