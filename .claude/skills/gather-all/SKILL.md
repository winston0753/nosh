---
name: gather-all
description: Gather Nosh pilot data for neighborhoods in data/pilot/neighborhoods.yaml whose status is "todo", one after another. Use as /gather-all (every todo area), /gather-all 3 (at most three), or /gather-all palo-alto cupertino (only the named slugs).
---

# Gather "todo" neighborhoods

Arguments: **$ARGUMENTS**

- Empty: handle every area whose status is `todo`.
- A number: handle at most that many `todo` areas.
- One or more slugs: handle only those areas, and only if their status is
  `todo`. Use this form when several terminals run at once, giving each
  terminal a different set of slugs.

Data files only: no application code, no migrations, no commits, no staging.

1. Read `data/pilot/neighborhoods.yaml` and build your list from the
   arguments above, in file order.
2. Read `.claude/skills/gather-neighborhood/SKILL.md`.
3. For each area on your list, in order:
   a. **Re-read `neighborhoods.yaml` immediately before starting it.** If its
      status is no longer `todo`, another session has taken it: skip it and
      say so. Never work on an area marked `in_progress` or `done`.
   b. Claim it straight away by setting its status to `in_progress`, changing
      only that one line of the file. Then carry out the gather-neighborhood
      procedure in full for that slug.
   c. Finish the area completely, including its report, the check script,
      and the status update, before starting the next.
4. When you edit `neighborhoods.yaml`, re-read it first and change only your
   own area's status line, so another session's change is not overwritten.
5. Keep your own notes short between areas. Everything worth keeping is in
   the files; do not carry restaurant or menu detail from one area to the
   next.
6. If a stop rule fires for an area, record it in that area's
   `menus_report.md`, leave its status `in_progress`, and move on to the
   next area. Do not stop the whole run.
7. At the end, run `python3 data/pilot/check.py` and show its table. Then
   list: areas completed, areas skipped because another session had them,
   areas stopped early and why, and the spot-check restaurants for each.

Do not group, classify, or map dishes. Do not commit.
