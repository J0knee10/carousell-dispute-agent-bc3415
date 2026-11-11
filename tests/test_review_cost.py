from dispute_agent.evaluation.review_cost import (
    Case,
    Costs,
    break_even,
    by_confidence,
    cheapest,
    evaluate,
    refund_share,
    unit_costs,
)

# Careful review S$20, standard S$10 (extra S$10 to escalate), order S$100, no AI cost.
COSTS = Costs(careful=20.0, standard=10.0, order_value=100.0, partial_share=0.2, llm_in=0.0, llm_out=0.0)


def _case(cid, pred, label, conf, judged=True, other=False, percent=None):
    return Case(cid, "run", label, pred, percent, conf, judged, other)


def test_unit_costs_follow_the_config():
    c = unit_costs("base")
    assert round(c.careful, 2) == 26.25  # 45 minutes at S$35 an hour
    assert round(c.extra, 3) == 13.125  # the agent saves half of it
    assert c.mistake(1.0) == c.careful + c.order_value


def test_refund_shares():
    assert refund_share("decline", None, 0.2) == 0
    assert refund_share("full_refund_with_return", None, 0.2) == 1
    assert refund_share("partial_refund", None, 0.2) == 0.2
    assert refund_share("partial_refund", 40, 0.2) == 0.4
    # a 40% refund given where a decline was due moves 40% of the order wrongly
    assert _case("A", "partial_refund", "decline", 0.9, percent=40).money_share(0.2) == 0.4
    assert _case("B", "decline", "full_refund_with_return", 0.9).money_share(0.2) == 1.0
    assert _case("C", "decline", "decline", 0.9).money_share(0.2) == 0.0


def test_who_is_escalated():
    assert _case("A", "decline", "decline", 0.6).escalated(0.7)
    assert not _case("A", "decline", "decline", 0.7).escalated(0.7)  # at the threshold is not below it
    assert _case("A", "decline", "decline", 1.0, other=True).escalated(0.7)  # the gate's other reasons
    assert not _case("A", "decline", "decline", 0.5, judged=False).escalated(0.7)  # rules cases: no threshold
    assert Case("A", "run", "decline", None, None, None, True, True).escalated(0.7)  # never answered


def test_evaluate_prices_staff_time_and_mistakes():
    cases = [
        _case("A", "decline", "decline", 1.0),
        _case("B", "decline", "full_refund_with_return", 0.9),  # wrong, costs 20 + 100 if it stands
    ]
    low = evaluate(cases, 0.7, COSTS)
    assert (low.escalated, low.caught, low.mistakes) == (0, 0, 1)
    assert low.total == 10 + 10 + 120
    high = evaluate(cases, 0.95, COSTS)
    assert (high.escalated, high.caught) == (1, 1)
    assert high.total == 10 + 20


def test_cheapest_keeps_the_current_threshold_on_a_tie():
    cases = [_case("A", "decline", "decline", 1.0)]
    results = [evaluate(cases, t, COSTS) for t in (0.5, 0.7, 0.9)]
    assert cheapest(results, 0.7) == (0.7, [0.5, 0.7, 0.9])
    assert cheapest(results, 0.8)[0] == 0.5


def test_raising_pays_only_when_mistakes_are_expensive():
    # Ten answers at 0.9, one wrong. Escalating all ten costs 10 x S$10 = S$100 extra.
    right = [_case(str(i), "decline", "decline", 0.9) for i in range(9)]
    big = right + [_case("W", "decline", "full_refund_with_return", 0.9)]  # mistake costs S$120
    small = right + [_case("W", "partial_refund", "decline", 0.9, percent=10)]  # mistake costs S$30
    assert cheapest([evaluate(big, t, COSTS) for t in (0.7, 0.95)], 0.7)[0] == 0.95
    assert cheapest([evaluate(small, t, COSTS) for t in (0.7, 0.95)], 0.7)[0] == 0.7
    assert break_even(big, 0.95, 0.7, COSTS) == "if a mistake costs over S$100"
    assert break_even(big, 0.5, 0.7, COSTS) == "same cases escalated"
    assert break_even(right, 0.95, 0.7, COSTS).startswith("never")


def test_by_confidence_compares_the_mistake_cost_with_the_extra_review():
    cases = [_case("A", "decline", "full_refund_with_return", 0.9), _case("B", "decline", "decline", 0.9),
             _case("C", "decline", "decline", 1.0)]
    rows = {r["confidence"]: r for r in by_confidence(cases, COSTS)}
    assert rows[0.9]["wrong"] == 1 and rows[0.9]["stand_cost"] == 60 and rows[0.9]["review_pays"]
    assert not rows[1.0]["review_pays"]
