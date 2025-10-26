-- Migration: Create trade_predictions table for reinforcement learning
-- Purpose: Track all LLM predictions and their outcomes for continuous improvement
-- Created: 2025-10-26

CREATE TABLE IF NOT EXISTS trade_predictions (
    id BIGSERIAL PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    user_id TEXT,
    symbol TEXT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- LLM Prediction
    prediction_type TEXT NOT NULL,  -- 'entry_suggestion', 'exit_suggestion', 'analysis'
    direction TEXT,  -- 'long', 'short', 'neutral'
    entry_price DECIMAL(10, 4),
    stop_loss DECIMAL(10, 4),
    take_profit DECIMAL(10, 4),
    risk_reward_ratio DECIMAL(5, 2),

    -- Pattern Data (JSON)
    patterns_detected JSONB,  -- FVG, BoS, CHoCH details with confidence scores

    -- Confidence Scores (1-10 scale)
    pattern_confidence DECIMAL(3, 1),  -- Best pattern confidence
    data_quality_score DECIMAL(3, 1),  -- Data quality at time of prediction
    overall_confidence DECIMAL(3, 1),  -- Combined confidence score

    -- Market Context at Time of Prediction
    price_at_prediction DECIMAL(10, 4),
    volume_at_prediction BIGINT,
    bars_available INTEGER,

    -- Outcome Tracking (filled later by automated evaluation)
    outcome_evaluated BOOLEAN DEFAULT FALSE,
    outcome_timestamp TIMESTAMP WITH TIME ZONE,
    price_movement_24h DECIMAL(5, 2),  -- % move in 24 bars
    max_favorable_excursion DECIMAL(5, 2),  -- MFE %
    max_adverse_excursion DECIMAL(5, 2),  -- MAE %
    hit_take_profit BOOLEAN,
    hit_stop_loss BOOLEAN,
    actual_outcome TEXT,  -- 'win', 'loss', 'breakeven', 'not_triggered'

    -- Reinforcement Learning Metrics
    prediction_accuracy_score DECIMAL(5, 2),  -- How accurate was this prediction?

    -- Indexes for efficient querying
    CONSTRAINT valid_confidence_scores CHECK (
        pattern_confidence >= 1.0 AND pattern_confidence <= 10.0 AND
        data_quality_score >= 1.0 AND data_quality_score <= 10.0 AND
        overall_confidence >= 1.0 AND overall_confidence <= 10.0
    )
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_predictions_symbol ON trade_predictions(symbol);
CREATE INDEX IF NOT EXISTS idx_predictions_timestamp ON trade_predictions(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_predictions_outcome ON trade_predictions(outcome_evaluated, symbol);
CREATE INDEX IF NOT EXISTS idx_predictions_conversation ON trade_predictions(conversation_id);
CREATE INDEX IF NOT EXISTS idx_predictions_confidence ON trade_predictions(overall_confidence DESC);

-- Comments for documentation
COMMENT ON TABLE trade_predictions IS 'Stores all LLM trading predictions and their outcomes for reinforcement learning';
COMMENT ON COLUMN trade_predictions.patterns_detected IS 'JSON containing detected patterns (FVG, BoS, CHoCH) with their confidence scores';
COMMENT ON COLUMN trade_predictions.overall_confidence IS 'Combined confidence score (1-10) accounting for pattern quality and data quality';
COMMENT ON COLUMN trade_predictions.prediction_accuracy_score IS 'Post-evaluation metric (0-10) measuring how accurate the prediction was';
