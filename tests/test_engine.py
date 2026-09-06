"""
Unit tests for Figma AI Prompt Optimization Engine.
"""
import unittest
import sys
import os

# Add root directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.engine import PromptOptimizationEngine
from app.tokenizer_sim import estimate_tokens, calculate_compression_metrics
from app.presets import DEVICE_PRESETS, STYLE_PRESETS


class TestPromptOptimizer(unittest.TestCase):

    def setUp(self):
        self.engine = PromptOptimizationEngine()

    def test_estimate_tokens(self):
        sample = "Design a clean analytics dashboard for an AI platform."
        tokens = estimate_tokens(sample)
        self.assertGreater(tokens, 0)
        self.assertIsInstance(tokens, int)

    def test_compression_metrics(self):
        raw = "Please make me a dashboard with charts and table."
        opt = "[Frame: Desktop 1440px] [Hero: MetricCards(3)] [Content: DataTable]"
        metrics = calculate_compression_metrics(raw, opt, latency_ms=120)

        self.assertIn("reduction_percentage", metrics)
        self.assertIn("tokens_saved", metrics)
        self.assertGreaterEqual(metrics["tokens_saved"], 0)

    def test_offline_fallback_optimization(self):
        res = self.engine.optimize(
            user_input="Make a dark crypto wallet dashboard on desktop",
            device_id="desktop",
            style_id="minimal_dark"
        )

        self.assertTrue(res["success"])
        self.assertIn("optimized_prompt", res)
        self.assertIn("[Frame:", res["optimized_prompt"])
        self.assertIn("[Layout:", res["optimized_prompt"])
        self.assertIn("metrics", res)
        self.assertGreater(res["metrics"]["reduction_percentage"], 0)

    def test_presets_coverage(self):
        self.assertIn("desktop", DEVICE_PRESETS)
        self.assertIn("mobile", DEVICE_PRESETS)
        self.assertIn("saas_modern", STYLE_PRESETS)
        self.assertIn("minimal_dark", STYLE_PRESETS)


if __name__ == "__main__":
    unittest.main()
