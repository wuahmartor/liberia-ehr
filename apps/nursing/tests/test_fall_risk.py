from django.test import SimpleTestCase

from apps.nursing.fall_risk import calculate_morse, score_assessment


class FallRiskScoringTests(SimpleTestCase):
    def test_morse_score_uses_standard_six_items(self):
        score = calculate_morse(
            {
                "history_of_falling": True,
                "secondary_diagnosis": True,
                "ambulatory_aid": "furniture",
                "iv_or_heparin_lock": True,
                "gait": "impaired",
                "mental_status": "overconfident",
            }
        )
        self.assertEqual(score, 125)

    def test_low_risk_inputs_remain_low_across_comparison(self):
        result = score_assessment(
            {
                "ambulatory_aid": "none",
                "gait": "normal",
                "mental_status": "oriented",
            }
        )
        self.assertEqual(result["morse_score"], 0)
        self.assertEqual(result["overall_level"], "low")

    def test_conservative_result_uses_highest_model_level(self):
        result = score_assessment(
            {
                "history_of_falling": True,
                "secondary_diagnosis": True,
                "ambulatory_aid": "furniture",
                "iv_or_heparin_lock": True,
                "gait": "impaired",
                "mental_status": "overconfident",
                "sedating_medication": True,
                "dizziness_or_hypotension": True,
                "toileting_assistance": True,
            }
        )
        self.assertEqual(result["morse_level"], "high")
        self.assertEqual(result["overall_level"], "high")
        self.assertFalse(result["model_comparison"]["logistic"]["validated"])
        self.assertFalse(result["model_comparison"]["xgboost"]["validated"])
