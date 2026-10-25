"""Turn a CSV of practice-session results into a weekly parent summary (Markdown).

Standard library only. The mastery rules mirror the coach instructions:

  * A lesson counts as MASTERED only at >= 80% accuracy. Below 80% earns nothing.
  * 100% accuracy earns a 1.25x points bonus.
  * Retries earn less: 2nd attempt 0.5x, 3rd 0.25x, 4th+ nothing (stops point farming).
  * Rushing (low accuracy AND under 30 seconds per question) earns nothing and is flagged.
  * Healthy "target zone" is roughly 80-85% average accuracy. Much higher means the
    work may be too easy; under 70% for 2+ sessions suggests a real gap.

CSV columns (header required):
  date,learner,subject,skill,lesson,attempt,accuracy_pct,questions,minutes,tutor_used

Usage:
  py progress_log.py --demo
  py progress_log.py sessions.csv --goal-lessons 8 --planned-sessions 5 --out summary.md
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path

PASS_PCT = 80.0
PERFECT_BONUS = 1.25
RETRY_MULTIPLIER = {1: 1.0, 2: 0.5, 3: 0.25}  # 4th attempt and later: 0
RUSH_SECONDS_PER_QUESTION = 30
GAP_PCT = 70.0
TOO_EASY_PCT = 95.0
BASE_POINTS = 10

DEMO_CSV = Path(__file__).parent / "fixtures" / "sessions_demo.csv"

REQUIRED = ["date", "learner", "subject", "skill", "lesson", "attempt",
            "accuracy_pct", "questions", "minutes", "tutor_used"]


@dataclass
class Session:
    day: date
    learner: str
    subject: str
    skill: str
    lesson: str
    attempt: int
    accuracy: float
    questions: int
    minutes: float
    tutor_used: bool

    @property
    def rushed(self) -> bool:
        if self.questions <= 0:
            return False
        secs = self.minutes * 60 / self.questions
        return self.accuracy < PASS_PCT and secs < RUSH_SECONDS_PER_QUESTION

    @property
    def mastered(self) -> bool:
        return self.accuracy >= PASS_PCT and not self.rushed

    @property
    def points(self) -> float:
        if not self.mastered:
            return 0.0
        mult = RETRY_MULTIPLIER.get(self.attempt, 0.0)
        bonus = PERFECT_BONUS if self.accuracy >= 100 else 1.0
        return BASE_POINTS * mult * bonus


def load_sessions(path: Path) -> list[Session]:
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        missing = [c for c in REQUIRED if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"CSV is missing column(s): {', '.join(missing)}")
        out = []
        for i, row in enumerate(reader, start=2):
            try:
                out.append(Session(
                    day=date.fromisoformat(row["date"].strip()),
                    learner=row["learner"].strip(),
                    subject=row["subject"].strip(),
                    skill=row["skill"].strip(),
                    lesson=row["lesson"].strip(),
                    attempt=int(row["attempt"]),
                    accuracy=float(row["accuracy_pct"]),
                    questions=int(row["questions"]),
                    minutes=float(row["minutes"]),
                    tutor_used=row["tutor_used"].strip().lower() in {"y", "yes", "true", "1"},
                ))
            except (ValueError, KeyError) as exc:
                raise ValueError(f"Bad row on line {i}: {exc}") from exc
    return out


def skill_table(sessions: list[Session]) -> list[dict]:
    """Mastery % per skill = lessons mastered / distinct lessons attempted."""
    by_skill: dict[tuple[str, str], dict] = {}
    for s in sessions:
        key = (s.subject, s.skill)
        d = by_skill.setdefault(key, {"lessons": set(), "mastered": set(), "acc": []})
        d["lessons"].add(s.lesson)
        d["acc"].append(s.accuracy)
        if s.mastered:
            d["mastered"].add(s.lesson)
    rows = []
    for (subject, skill), d in sorted(by_skill.items()):
        avg = sum(d["acc"]) / len(d["acc"])
        rows.append({
            "subject": subject,
            "skill": skill,
            "attempted": len(d["lessons"]),
            "mastered": len(d["mastered"]),
            "mastery_pct": round(100 * len(d["mastered"]) / len(d["lessons"])),
            "avg_accuracy": round(avg),
            "zone": zone(avg),
        })
    return rows


def zone(avg: float) -> str:
    if avg >= TOO_EASY_PCT:
        return "too easy?"
    if avg >= PASS_PCT:
        return "target zone"
    if avg >= GAP_PCT:
        return "stretch"
    return "gap?"


def flags(sessions: list[Session]) -> list[str]:
    out = []
    rushed = [s for s in sessions if s.rushed]
    if rushed:
        out.append(f"Rushing: {len(rushed)} attempt(s) had low accuracy at under "
                   f"{RUSH_SECONDS_PER_QUESTION}s per question. Speed isn't rewarded; correct is.")
    low_days = sorted({s.day for s in sessions if s.accuracy < GAP_PCT})
    if len(low_days) >= 2:
        out.append(f"Possible gap: accuracy under {GAP_PCT:.0f}% on {len(low_days)} days. "
                   "Step back to the prerequisite skill.")
    farmed = [s for s in sessions if s.attempt >= 4]
    if farmed:
        out.append(f"Retry loop: {len(farmed)} lesson attempt(s) at 4th try or later (no points). "
                   "Sit with them for one lesson instead of another retry.")
    if sessions and all(s.accuracy >= TOO_EASY_PCT for s in sessions):
        out.append("Everything at 95%+: the work may be too easy. Consider moving ahead.")
    return out


def suggestion(lessons_mastered: int, goal: int, sessions_done: int, planned: int,
               flag_list: list[str]) -> str:
    if any(f.startswith("Rushing") for f in flag_list):
        return "Name the rushing calmly at the goal meeting and keep the goal the same."
    if any(f.startswith("Possible gap") for f in flag_list):
        return "Shrink next week's goal by a third and spend one session on the prerequisite skill."
    if goal and lessons_mastered < goal and sessions_done < planned:
        return "Protect the session slots first; the goal was fine, the sessions didn't happen."
    if goal and lessons_mastered < goal:
        return "Cut the goal by a third for one week to rebuild momentum."
    if goal and lessons_mastered >= goal * 1.5:
        return "Goal was easy. Let them propose a bigger one."
    return "Keep the same goal. Celebrate the streak."


def build_summary(sessions: list[Session], goal_lessons: int = 0, planned_sessions: int = 0,
                  points_cap: float | None = None) -> str:
    if not sessions:
        return "# Weekly parent summary\n\nNo sessions logged this week.\n"
    start = min(s.day for s in sessions)
    end = max(s.day for s in sessions)
    lines = [f"# Weekly parent summary: {start.isoformat()} to {end.isoformat()}", ""]
    by_learner: dict[str, list[Session]] = defaultdict(list)
    for s in sessions:
        by_learner[s.learner].append(s)

    for learner, rows in sorted(by_learner.items()):
        mastered = {(s.subject, s.lesson) for s in rows if s.mastered}
        days = sorted({s.day for s in rows})
        minutes = sum(s.minutes for s in rows)
        pts = sum(s.points for s in rows)
        capped = min(pts, points_cap) if points_cap is not None else pts
        tutor = sum(1 for s in rows if s.tutor_used)
        f = flags(rows)
        lines += [f"## {learner}", ""]
        lines += ["| Measure | This week |", "|---|---|"]
        goal_txt = f" / goal {goal_lessons}" if goal_lessons else ""
        sess_txt = f" / planned {planned_sessions}" if planned_sessions else ""
        lines.append(f"| Lessons mastered (80%+) | {len(mastered)}{goal_txt} |")
        lines.append(f"| Sessions done | {len(days)}{sess_txt} |")
        lines.append(f"| Focused minutes | {minutes:.0f} |")
        cap_txt = f" (capped at {points_cap:.0f})" if points_cap is not None and pts > points_cap else ""
        lines.append(f"| Points earned | {capped:.1f}{cap_txt} |")
        lines.append(f"| Times the tutor was used when stuck | {tutor} |")
        lines += ["", "**Mastery by skill**", "",
                  "| Subject | Skill | Mastered / tried | Mastery % | Avg accuracy | Zone |",
                  "|---|---|---|---|---|---|"]
        for r in skill_table(rows):
            lines.append(f"| {r['subject']} | {r['skill']} | {r['mastered']} / {r['attempted']} | "
                         f"{r['mastery_pct']}% | {r['avg_accuracy']}% | {r['zone']} |")
        lines += ["", "**Flags**", ""]
        lines += [f"- {x}" for x in f] if f else ["- None this week."]
        lines += ["", "**One adjustment for next week**", "",
                  f"- {suggestion(len(mastered), goal_lessons, len(days), planned_sessions, f)}", ""]
    lines.append("_Generated by progress_log.py. Points reward work the learner controls "
                 "(mastered lessons), never test scores._")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("csv", nargs="?", help="session log CSV")
    ap.add_argument("--demo", action="store_true", help="use the bundled synthetic log")
    ap.add_argument("--goal-lessons", type=int, default=0)
    ap.add_argument("--planned-sessions", type=int, default=0)
    ap.add_argument("--points-cap", type=float, default=None)
    ap.add_argument("--out", help="write Markdown here instead of printing")
    a = ap.parse_args(argv)

    if a.demo:
        path = DEMO_CSV
        a.goal_lessons = a.goal_lessons or 8
        a.planned_sessions = a.planned_sessions or 5
        a.points_cap = a.points_cap if a.points_cap is not None else 100
    elif a.csv:
        path = Path(a.csv)
    else:
        ap.error("give a CSV path or --demo")

    try:
        sessions = load_sessions(path)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    md = build_summary(sessions, a.goal_lessons, a.planned_sessions, a.points_cap)
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(md, encoding="utf-8")
        print(f"wrote {a.out}")
    else:
        sys.stdout.write(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
