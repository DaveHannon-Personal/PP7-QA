"""
Conflict Detector — identifies duplicate and contradictory QA rules.

Two rules conflict when they target the same PP7 field on the same object type
and their conditions are mutually exclusive or identical.

Conflict types:
  duplicate     — identical target + field + operator + value; same check twice
  contradiction — same target + field, but conditions cannot both be satisfied
                  (e.g. "equals A" vs "equals B", or "exists" vs "not_exists")

Resolution policy (documented in README):
  Rules run sequentially in list order. When two conflicting rules are both
  applied to the same item, the LAST rule in the sequence wins for fix actions.
  Both results still appear in the audit report so the user can see all outcomes.
"""
from __future__ import annotations

from dataclasses import dataclass
from app.models.rule import Rule

# Pairs of operators that directly contradict each other on the same field+value
_OPPOSING_OPERATORS: set[frozenset[str]] = {
    frozenset({"equals", "not_equals"}),
    frozenset({"exists", "not_exists"}),
    frozenset({"contains", "not_contains"}),
}


@dataclass
class RuleConflict:
    conflict_type: str          # "duplicate" | "contradiction"
    rule_a_id: int
    rule_a_name: str
    rule_b_id: int
    rule_b_name: str
    target: str
    field: str
    description: str            # human-readable explanation


def detect_conflicts(rules: list[Rule]) -> list[RuleConflict]:
    """
    Compare every pair of rules and return all detected conflicts.
    O(n²) — acceptable for typical rule set sizes (< 200 rules).
    """
    conflicts: list[RuleConflict] = []

    for i, a in enumerate(rules):
        cond_a = a.condition
        field_a = cond_a.get("field", "")
        op_a = cond_a.get("operator", "")
        val_a = str(cond_a.get("value", "")).strip().lower()

        for b in rules[i + 1 :]:
            if a.target != b.target:
                continue

            cond_b = b.condition
            field_b = cond_b.get("field", "")
            if field_a != field_b or not field_a:
                continue

            op_b = cond_b.get("operator", "")
            val_b = str(cond_b.get("value", "")).strip().lower()

            # ── Duplicate: identical condition ──────────────────────────────
            if op_a == op_b and val_a == val_b:
                conflicts.append(
                    RuleConflict(
                        conflict_type="duplicate",
                        rule_a_id=a.id,
                        rule_a_name=a.name,
                        rule_b_id=b.id,
                        rule_b_name=b.name,
                        target=a.target,
                        field=field_a,
                        description=(
                            f"Both rules check that '{field_a}' {op_a} '{cond_a.get('value')}' "
                            f"on target '{a.target}'. This is redundant."
                        ),
                    )
                )
                continue

            # ── Contradiction: opposing operators ───────────────────────────
            op_pair = frozenset({op_a, op_b})
            if op_pair in _OPPOSING_OPERATORS:
                # For equals/not_equals and contains/not_contains,
                # only a contradiction if the value is the same
                if op_pair in (
                    frozenset({"equals", "not_equals"}),
                    frozenset({"contains", "not_contains"}),
                ):
                    if val_a != val_b:
                        # Different values — not strictly contradictory
                        # (e.g. "equals A" vs "not_equals B" can both be true)
                        pass
                    else:
                        conflicts.append(
                            RuleConflict(
                                conflict_type="contradiction",
                                rule_a_id=a.id,
                                rule_a_name=a.name,
                                rule_b_id=b.id,
                                rule_b_name=b.name,
                                target=a.target,
                                field=field_a,
                                description=(
                                    f"'{field_a}' cannot satisfy both "
                                    f"'{op_a} {cond_a.get('value')}' and "
                                    f"'{op_b} {cond_b.get('value')}' simultaneously on '{a.target}'."
                                ),
                            )
                        )
                else:
                    # exists vs not_exists — always a contradiction
                    conflicts.append(
                        RuleConflict(
                            conflict_type="contradiction",
                            rule_a_id=a.id,
                            rule_a_name=a.name,
                            rule_b_id=b.id,
                            rule_b_name=b.name,
                            target=a.target,
                            field=field_a,
                            description=(
                                f"One rule requires '{field_a}' to {op_a}, "
                                f"but the other requires it to {op_b} on '{a.target}'. "
                                f"These conditions are mutually exclusive."
                            ),
                        )
                    )
                continue

            # ── Contradiction: two different "equals" values on same field ──
            if op_a == "equals" and op_b == "equals" and val_a != val_b:
                conflicts.append(
                    RuleConflict(
                        conflict_type="contradiction",
                        rule_a_id=a.id,
                        rule_a_name=a.name,
                        rule_b_id=b.id,
                        rule_b_name=b.name,
                        target=a.target,
                        field=field_a,
                        description=(
                            f"'{field_a}' cannot equal both '{cond_a.get('value')}' and "
                            f"'{cond_b.get('value')}' on '{a.target}'. "
                            f"If both run, the last rule in the sequence will win."
                        ),
                    )
                )

    return conflicts
