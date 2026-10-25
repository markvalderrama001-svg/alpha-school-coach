import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import progress_log as pl  # noqa: E402


def s(acc, attempt=1, questions=10, minutes=10, day=date(2026, 10, 19), lesson="L1",
      skill="Fractions", learner="Sam"):
    return pl.Session(day, learner, "Math", skill, lesson, attempt, acc, questions, minutes, False)


def test_below_80_earns_nothing():
    assert not s(79).mastered
    assert s(79).points == 0


def test_perfect_score_bonus():
    assert s(100).points == pytest.approx(12.5)
    assert s(90).points == pytest.approx(10)


def test_retry_points_shrink():
    assert s(90, attempt=2).points == pytest.approx(5)
    assert s(90, attempt=3).points == pytest.approx(2.5)
    assert s(90, attempt=4).points == 0


def test_rushing_detected_and_unpaid():
    fast = s(60, questions=10, minutes=3)  # 18 s per question
    assert fast.rushed and fast.points == 0
    slow = s(60, questions=10, minutes=10)
    assert not slow.rushed


def test_mastery_pct_per_skill():
    rows = pl.skill_table([s(90, lesson="A"), s(70, lesson="B"), s(85, lesson="B", attempt=2)])
    assert rows[0]["mastered"] == 2 and rows[0]["attempted"] == 2 and rows[0]["mastery_pct"] == 100


def test_gap_flag_needs_two_days():
    one = [s(60, day=date(2026, 10, 19))]
    two = one + [s(65, day=date(2026, 10, 20))]
    assert not any("gap" in f for f in pl.flags(one))
    assert any("gap" in f for f in pl.flags(two))


def test_points_cap_applied():
    md = pl.build_summary([s(100, lesson=str(i)) for i in range(10)], points_cap=50)
    assert "| Points earned | 50.0 (capped at 50) |" in md


def test_demo_summary_end_to_end(tmp_path):
    out = tmp_path / "summary.md"
    assert pl.main(["--demo", "--out", str(out)]) == 0
    md = out.read_text(encoding="utf-8")
    assert "## Sam" in md
    assert "| Lessons mastered (80%+) | 8 / goal 8 |" in md
    assert "Rushing: 1 attempt(s)" in md
    assert "| Reading | Making inferences | 0 / 1 | 0% |" in md


def test_missing_column_is_a_clear_error(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("date,learner\n2026-10-19,Sam\n", encoding="utf-8")
    with pytest.raises(ValueError, match="missing column"):
        pl.load_sessions(bad)
