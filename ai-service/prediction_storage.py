"""
Prediction Storage
==================
Store and retrieve trade predictions for reinforcement learning.
Tracks LLM suggestions and their outcomes to improve future predictions.
"""

import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from supabase import create_client, Client


class PredictionStorage:
    """Handles storage and retrieval of trade predictions."""

    def __init__(self):
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")

        self.supabase: Client = create_client(supabase_url, supabase_key)

    async def store_prediction(self, prediction: Dict[str, Any]) -> Optional[int]:
        """
        Store a trade prediction.

        Args:
            prediction: Dict containing:
                - conversation_id: str
                - user_id: str (optional)
                - symbol: str
                - prediction_type: str ('entry_suggestion', 'exit_suggestion', 'analysis')
                - direction: str ('long', 'short', 'neutral')
                - entry_price: float (optional)
                - stop_loss: float (optional)
                - take_profit: float (optional)
                - risk_reward_ratio: float (optional)
                - patterns_detected: dict (JSON with FVG, BoS, CHoCH)
                - pattern_confidence: float (1-10)
                - data_quality_score: float (1-10)
                - overall_confidence: float (1-10)
                - price_at_prediction: float
                - volume_at_prediction: int (optional)
                - bars_available: int

        Returns:
            Prediction ID if successful, None otherwise
        """
        try:
            result = self.supabase.table("trade_predictions").insert({
                "conversation_id": prediction["conversation_id"],
                "user_id": prediction.get("user_id"),
                "symbol": prediction["symbol"],
                "prediction_type": prediction["prediction_type"],
                "direction": prediction.get("direction"),
                "entry_price": prediction.get("entry_price"),
                "stop_loss": prediction.get("stop_loss"),
                "take_profit": prediction.get("take_profit"),
                "risk_reward_ratio": prediction.get("risk_reward_ratio"),
                "patterns_detected": prediction.get("patterns_detected"),
                "pattern_confidence": prediction.get("pattern_confidence"),
                "data_quality_score": prediction.get("data_quality_score"),
                "overall_confidence": prediction.get("overall_confidence"),
                "price_at_prediction": prediction.get("price_at_prediction"),
                "volume_at_prediction": prediction.get("volume_at_prediction"),
                "bars_available": prediction.get("bars_available")
            }).execute()

            if result.data and len(result.data) > 0:
                prediction_id = result.data[0]["id"]
                print(f"✅ Stored prediction {prediction_id} for {prediction['symbol']}")
                return prediction_id
            else:
                print(f"⚠️ Failed to store prediction for {prediction['symbol']}")
                return None

        except Exception as e:
            print(f"❌ Error storing prediction: {str(e)}")
            return None

    async def get_predictions_needing_evaluation(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get predictions that haven't been evaluated yet and are old enough (24+ bars).

        Args:
            limit: Max number of predictions to return

        Returns:
            List of predictions ready for evaluation
        """
        try:
            # Get predictions from at least 30 minutes ago (30 bars for 1-min data)
            result = self.supabase.table("trade_predictions").select("*").eq(
                "outcome_evaluated", False
            ).lt(
                "timestamp", datetime.now().isoformat()
            ).limit(limit).execute()

            return result.data if result.data else []

        except Exception as e:
            print(f"❌ Error fetching predictions: {str(e)}")
            return []

    async def update_prediction_outcome(
        self,
        prediction_id: int,
        outcome_data: Dict[str, Any]
    ) -> bool:
        """
        Update prediction with evaluated outcome.

        Args:
            prediction_id: ID of prediction to update
            outcome_data: Dict containing:
                - max_favorable_excursion: float (%)
                - max_adverse_excursion: float (%)
                - hit_take_profit: bool
                - hit_stop_loss: bool
                - actual_outcome: str ('win', 'loss', 'breakeven', 'not_triggered')
                - prediction_accuracy_score: float (0-10)
                - price_movement_24h: float (%)

        Returns:
            True if successful, False otherwise
        """
        try:
            result = self.supabase.table("trade_predictions").update({
                "outcome_evaluated": True,
                "outcome_timestamp": datetime.now().isoformat(),
                "max_favorable_excursion": outcome_data.get("max_favorable_excursion"),
                "max_adverse_excursion": outcome_data.get("max_adverse_excursion"),
                "hit_take_profit": outcome_data.get("hit_take_profit"),
                "hit_stop_loss": outcome_data.get("hit_stop_loss"),
                "actual_outcome": outcome_data.get("actual_outcome"),
                "prediction_accuracy_score": outcome_data.get("prediction_accuracy_score"),
                "price_movement_24h": outcome_data.get("price_movement_24h")
            }).eq("id", prediction_id).execute()

            if result.data:
                print(f"✅ Updated outcome for prediction {prediction_id}")
                return True
            else:
                print(f"⚠️ Failed to update prediction {prediction_id}")
                return False

        except Exception as e:
            print(f"❌ Error updating prediction: {str(e)}")
            return False

    async def get_pattern_performance(
        self,
        pattern_type: str,
        min_confidence: float = 5.0
    ) -> Dict[str, Any]:
        """
        Analyze performance of a specific pattern type.

        Args:
            pattern_type: 'fvg', 'bos', or 'choch'
            min_confidence: Minimum confidence to include

        Returns:
            Dict with performance metrics
        """
        try:
            result = self.supabase.rpc(
                'get_pattern_performance',
                {
                    'pattern_type': pattern_type,
                    'min_confidence': min_confidence
                }
            ).execute()

            return result.data if result.data else {}

        except Exception as e:
            print(f"❌ Error getting pattern performance: {str(e)}")
            return {}

    async def get_confidence_calibration(self) -> List[Dict[str, Any]]:
        """
        Get confidence score calibration data.
        Shows how well our confidence scores predict actual outcomes.

        Returns:
            List of dicts with confidence ranges and actual win rates
        """
        try:
            # Group by confidence buckets and calculate win rates
            result = self.supabase.rpc('get_confidence_calibration').execute()
            return result.data if result.data else []

        except Exception as e:
            print(f"❌ Error getting confidence calibration: {str(e)}")
            return []


# Global instance
prediction_storage = PredictionStorage()
