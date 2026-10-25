# Parent guide: set it up, run it, review it

About 30 minutes to set up, then 2 minutes a night and 15 minutes a week.

## 1. Set up two Claude Projects

| Project | Who uses it | Instructions | Knowledge |
|---|---|---|---|
| Home Learning Coach | You | [claude/PROJECT_INSTRUCTIONS.md](../claude/PROJECT_INSTRUCTIONS.md) | Your filled-in [coach-playbook-template.md](../claude/knowledge/coach-playbook-template.md) |
| "I'm stuck" Tutor | Your kid | [claude/TUTOR_INSTRUCTIONS.md](../claude/TUTOR_INSTRUCTIONS.md) | Nothing needed |

Steps:
1. In claude.ai, create a new Project and paste the instructions (everything below the line).
2. Fill in the playbook template with nicknames, goals and your reward amounts. Leave out school names, test IDs and anything identifying. Upload it to the coach project.
3. Create the tutor project the same way. Use it on a device you can see, and decide whether your kid uses your account or their own supervised one.
4. Prefer Claude Code? Copy `skills/home-learning-coach` into `~/.claude/skills/` instead of step 1.

## 2. Pick a practice source

The coach and tutor don't teach the curriculum. Use any practice app or workbook that has short lessons and a clear score per lesson. The key is a score you can log.

## 3. Run the nightly routine (30 to 35 minutes)

1. Two-minute check-in: "What's your goal tonight?" Start a visible timer.
2. 25-minute focus block, phones in another room, screen where you can see it.
3. Stuck for 2+ minutes: try it on paper, then open the tutor.
4. Two-minute wrap-up. Log each lesson as one row in a CSV:

```
date,learner,subject,skill,lesson,attempt,accuracy_pct,questions,minutes,tutor_used
2026-10-19,Sam,Math,Equivalent fractions,M-101,1,90,10,9,N
```

A spreadsheet works fine; export it as CSV at the end of the week.

## 4. Weekly review (15 minutes)

```bash
py progress_log.py my-week.csv --goal-lessons 8 --planned-sessions 5 --points-cap 100 --out summary.md
```

Paste `summary.md` into the coach project and say "prep the goal meeting." Then:

1. Skim the tutor notes from the week. Look for "Hints used: 3" a lot, or anything that looks like the tutor did the work.
2. Hold the goal meeting with your kid. Let them propose the goal; you adjust.
3. Pay the reward in person.

## 5. What to watch

| You see | Do this |
|---|---|
| Mastery % in "too easy?" | Let them move ahead |
| "gap?" on two days | Go back one skill, sit with them for a lesson |
| Rushing flag | Name it calmly. Speed isn't rewarded |
| Sessions under plan | Protect the time slot before touching the goal |
| Stress, tears, lost sleep | Pause for a week. Homework and sleep come first |

## Privacy checklist

- Nicknames only, in the playbook and in the CSV
- No school names, test IDs, diagnoses or photos in either project
- Review the tutor chat log weekly
- Check your Claude privacy settings and choose what you are comfortable with

Independent parent project; not affiliated with or endorsed by Alpha School.
