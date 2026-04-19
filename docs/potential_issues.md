# Autologic — Potential Issues

Last updated: 2026-02-26

Items identified during reverse-engineering that may represent bugs, misintent, or design concerns. Tracked separately from the spec.

## Likely Bugs

1. **`Heat.compliment` misspelling** — should be `complement`. Used in `heat.py` and `event.py`. Functional but misleading. (Naming debt)

2. **Instructor minimum: `round()` vs README's `÷`** — `roles_and_minima()` uses `round(number_of_novices / novice_denominator)` with a floor of `MIN_INSTRUCTOR_PER_HEAT`. The README says `≥ (novices in complement) ÷ (novice denominator)`. The `≥` framing suggests floor or ceil as the rounding policy, not banker's rounding. Python's `round()` (banker's rounding) diverges from both floor and ceil for a range of inputs — e.g., 7/3 = 2.33 rounds to 2 but ceils to 3. Whether `round()` is the intended behavior is ambiguous.

3. **`exit(1)` in algorithm on max iterations exceeded** — `randomize.py` calls `exit(1)` when the iteration limit is hit. The GUI catches this as `SystemExit`, but this is a control-flow antipattern. Should raise a domain exception.

4. **Off-by-one in outer iteration loop** — `iteration = -1` combined with `while iteration < max_iterations` and `iteration += 1` at loop start means the algorithm runs `max_iterations + 1` iterations (0 through `max_iterations` inclusive), not `max_iterations`.

5. **6-heat run/work mapping maps every heat to itself** — the formula `(running + 5) % 6 + 1 = running` for all values. A heat cannot simultaneously run and work. This makes 6-heat events produce an invalid schedule. Likely the formula was designed for 3-4 heat events and was never tested beyond that.

6. **Unbounded inner loop in `randomize_heats()`** — the inner loop retries until CAM classes are in the same heat AND heat sizes are valid. There is no iteration limit; if the constraints are unsatisfiable for a given set of categories, this loop runs forever (with observer notifications every 100 iterations as the only interrupt point).

7. ~~**`questionary` CLI prompt reachable from GUI**~~ — fixed. `Participant.set_assignment()` no longer prompts; no-show + special-assignment conflicts are now collected into `Event.no_show_special_assignments` and resolved by the caller (GUI via `messagebox.askyesno`, CLI via warning print).

## Possible Misintent

8. **`gate` role loaded but never used** — member attributes CSV has a `gate` column, and the value is loaded as a Participant attribute, but `roles_and_minima()` does not include `gate`. The role is never assigned or validated. Unclear if this is a planned future role or dead code.

9. **CAM class same-heat constraint is hardcoded** — `randomize_heats()` requires all categories starting with `"CAM-"` to be in the same heat. This is not configurable and not documented in the README's validation section.

10. **No parameter bounds validation** — the pydantic Config model does not enforce lower bounds on `number_of_heats`, `heat_size_parity`, `novice_size_parity`, or `novice_denominator`. Zero values produce division-by-zero at runtime.

## Design Concerns

11. **`Heat.participants` recomputes on every access** — the property iterates all categories and flattens participant lists each time. Low severity at current event sizes but could matter if accessed in hot loops.

12. **Config round-trip through pickle** — `config_snapshot` is embedded in the Event pickle. On reload, the GUI applies the snapshot permissively (ignores unknown keys). Schema evolution across versions could produce silent config drift.

13. **Run/work mapping formula for 4+ heats is non-obvious** — `(running + 5) % number_of_heats + 1` works for 4, 5, 7, and 8 heats but fails for 6 (see item 5). The intent for arbitrary heat counts is unclear.
