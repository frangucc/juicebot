#!/bin/bash
# Convenience script to run different components

set -e

case "$1" in
  screener)
    echo "Starting screener..."
    source venv/bin/activate
    python -m screener.main "${@:2}"
    ;;

  api)
    echo "Starting API server..."
    source venv/bin/activate
    uvicorn api.main:app --reload --port 8000
    ;;

  dashboard)
    echo "Starting dashboard..."
    cd dashboard
    npm run dev
    ;;

  ai-service)
    echo "Starting AI service..."
    source venv/bin/activate
    cd ai-service
    uvicorn main:app --reload --host 0.0.0.0 --port 8002
    ;;

  test)
    echo "Running test screener with replay..."
    source venv/bin/activate
    python -m screener.main --replay --threshold 0.03
    ;;

  setup)
    echo "Setting up Python environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    echo "✓ Python setup complete"
    echo ""
    echo "Setting up dashboard..."
    cd dashboard
    npm install
    echo "✓ Dashboard setup complete"
    echo ""
    echo "Next steps:"
    echo "1. Run the SQL migration in Supabase (see sql/001_init_schema.sql)"
    echo "2. Create dashboard/.env.local (see dashboard/.env.local.example)"
    echo "3. Run: ./run.sh test"
    ;;

  *)
    echo "Usage: ./run.sh [command]"
    echo ""
    echo "Commands:"
    echo "  setup      - Install all dependencies"
    echo "  test       - Test screener with replay"
    echo "  screener   - Run screener (add args like --threshold 0.05)"
    echo "  api        - Run API server"
    echo "  ai-service - Run AI service (JuiceBot)"
    echo "  dashboard  - Run dashboard"
    echo ""
    echo "Examples:"
    echo "  ./run.sh setup"
    echo "  ./run.sh test"
    echo "  ./run.sh screener --threshold 0.05"
    echo "  ./run.sh api"
    echo "  ./run.sh ai-service"
    echo "  ./run.sh dashboard"
    ;;
esac
