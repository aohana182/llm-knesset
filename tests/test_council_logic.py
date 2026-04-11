"""Tests for pure logic functions in council.py — no network, no DB."""
import pytest
from backend.council import parse_ranking_from_text, calculate_aggregate_rankings


# ── parse_ranking_from_text ───────────────────────────────────────────────────

class TestParseRankingFromText:
    def test_valid_final_ranking_block(self):
        text = (
            "Response A is good.\nResponse B is okay.\n\n"
            "FINAL RANKING:\n1. Response A\n2. Response B\n3. Response C"
        )
        result = parse_ranking_from_text(text)
        assert result == ["Response A", "Response B", "Response C"]

    def test_two_responses(self):
        text = "Some commentary.\n\nFINAL RANKING:\n1. Response B\n2. Response A"
        result = parse_ranking_from_text(text)
        assert result == ["Response B", "Response A"]

    def test_no_final_ranking_falls_back_to_full_text_scan(self):
        text = "I think Response B is best, then Response A."
        result = parse_ranking_from_text(text)
        assert result == ["Response B", "Response A"]

    def test_empty_text_returns_empty(self):
        assert parse_ranking_from_text("") == []

    def test_no_responses_in_text_returns_empty(self):
        assert parse_ranking_from_text("Nothing useful here.") == []

    def test_extra_whitespace_around_labels(self):
        text = "FINAL RANKING:\n1.  Response A\n2.  Response B"
        result = parse_ranking_from_text(text)
        assert result == ["Response A", "Response B"]

    def test_only_extracts_after_final_ranking_marker(self):
        text = "Response C appeared earlier.\n\nFINAL RANKING:\n1. Response A\n2. Response B"
        result = parse_ranking_from_text(text)
        assert result == ["Response A", "Response B"]
        assert "Response C" not in result

    def test_single_response(self):
        text = "FINAL RANKING:\n1. Response A"
        result = parse_ranking_from_text(text)
        assert result == ["Response A"]

    def test_four_responses(self):
        text = "FINAL RANKING:\n1. Response D\n2. Response A\n3. Response C\n4. Response B"
        result = parse_ranking_from_text(text)
        assert result == ["Response D", "Response A", "Response C", "Response B"]


# ── calculate_aggregate_rankings ─────────────────────────────────────────────

class TestCalculateAggregateRankings:
    def _make_ranking(self, model, ranking_text):
        return {"model": model, "ranking": ranking_text, "parsed_ranking": parse_ranking_from_text(ranking_text)}

    def test_three_voters_three_models_unanimous(self):
        label_to_model = {
            "Response A": "gpt-4o",
            "Response B": "claude",
            "Response C": "gemini",
        }
        ranking_text = "FINAL RANKING:\n1. Response A\n2. Response B\n3. Response C"
        stage2 = [
            self._make_ranking("gpt-4o", ranking_text),
            self._make_ranking("claude", ranking_text),
            self._make_ranking("gemini", ranking_text),
        ]
        result = calculate_aggregate_rankings(stage2, label_to_model)
        assert result[0]["model"] == "gpt-4o"
        assert result[0]["average_rank"] == 1.0
        assert result[1]["model"] == "claude"
        assert result[2]["model"] == "gemini"

    def test_average_rank_calculated_correctly(self):
        label_to_model = {"Response A": "gpt-4o", "Response B": "claude"}
        stage2 = [
            self._make_ranking("gpt-4o", "FINAL RANKING:\n1. Response A\n2. Response B"),
            self._make_ranking("claude", "FINAL RANKING:\n1. Response B\n2. Response A"),
        ]
        result = calculate_aggregate_rankings(stage2, label_to_model)
        models = {r["model"]: r["average_rank"] for r in result}
        assert models["gpt-4o"] == 1.5
        assert models["claude"] == 1.5

    def test_sorted_by_average_rank_ascending(self):
        label_to_model = {"Response A": "gpt-4o", "Response B": "claude", "Response C": "gemini"}
        stage2 = [
            self._make_ranking("x", "FINAL RANKING:\n1. Response C\n2. Response B\n3. Response A"),
        ]
        result = calculate_aggregate_rankings(stage2, label_to_model)
        assert result[0]["model"] == "gemini"
        assert result[-1]["model"] == "gpt-4o"

    def test_empty_stage2_returns_empty(self):
        result = calculate_aggregate_rankings([], {"Response A": "gpt-4o"})
        assert result == []

    def test_model_ranked_by_only_one_voter(self):
        label_to_model = {"Response A": "gpt-4o", "Response B": "claude"}
        stage2 = [
            self._make_ranking("gpt-4o", "FINAL RANKING:\n1. Response A"),
        ]
        result = calculate_aggregate_rankings(stage2, label_to_model)
        assert len(result) == 1
        assert result[0]["model"] == "gpt-4o"
        assert result[0]["rankings_count"] == 1

    def test_unknown_label_in_ranking_is_ignored(self):
        label_to_model = {"Response A": "gpt-4o"}
        stage2 = [
            self._make_ranking("gpt-4o", "FINAL RANKING:\n1. Response A\n2. Response Z"),
        ]
        result = calculate_aggregate_rankings(stage2, label_to_model)
        assert len(result) == 1
        assert result[0]["model"] == "gpt-4o"
