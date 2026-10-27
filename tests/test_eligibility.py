from datetime import timedelta

import pytest

from dispute_agent.agent.eligibility import check_eligibility, window_close


def test_seed_cases_match_intended_eligibility(seeds):
    for case in seeds.values():
        result = check_eligibility(case)
        assert result.eligible == case.meta.target_eligible, case.case_id


@pytest.mark.parametrize(
    "case_id, status",
    [("S01", "eligible"), ("S16", "not_covered"), ("S17", "not_covered"), ("S18", "not_covered"), ("S19", "not_covered"), ("S20", "procedural")],
)
def test_status(seeds, case_id, status):
    assert check_eligibility(seeds[case_id]).status == status


def test_tracked_mail_window_is_two_days(seeds):
    case = seeds["S01"].model_copy(deep=True)
    delivered = case.order.delivered_at
    case.dispute.raised_at = delivered + timedelta(days=2) - timedelta(minutes=1)
    assert check_eligibility(case).status == "eligible"
    case.dispute.raised_at = delivered + timedelta(days=2, minutes=1)
    assert check_eligibility(case).status == "not_covered"


def test_certified_window_is_longer(seeds):
    case = seeds["S01"].model_copy(deep=True)
    case.order.programme = "certified"
    case.dispute.raised_at = case.order.delivered_at + timedelta(days=6)
    assert check_eligibility(case).status == "eligible"


def test_completion_closes_window_early(seeds):
    case = seeds["S01"].model_copy(deep=True)
    case.order.completed_at = case.order.delivered_at + timedelta(hours=1)
    close, why = window_close(case)
    assert close == case.order.completed_at
    assert "completed" in why
    assert check_eligibility(case).status == "not_covered"


def test_every_failed_check_cites_a_clause(seeds):
    for cid in ("S16", "S17", "S19", "S20"):
        failed = [c for c in check_eligibility(seeds[cid]).checks if not c.passed]
        assert failed and all(c.clause_ids for c in failed), cid
