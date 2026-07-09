"""
Audit Engine — evaluates QA rules against live PP7 data.

Flow:
  1. Fetch reference data (looks, themes, groups) once per audit run
  2. Fetch all playlists → iterate items → fetch each presentation
  3. For each (item, rule) pair where rule.target matches, evaluate condition
  4. Return list of AuditResultItem

Condition operators:
  equals          — exact match (string / number / bool)
  not_equals      — inverse of equals
  contains        — substring / list membership
  not_contains    — inverse of contains
  exists          — field is present and not None/empty
  not_exists      — field is absent or None/empty
  matches_regex   — regex match on string value
"""
from __future__ import annotations

import re
from typing import Any
from sqlalchemy.orm import Session
from app.models.rule import Rule
from app.models.profile import Profile, ProfileRule
from app.schemas.audit import AuditResultItem
from app.services import propresenter as pp7


def _resolve(obj: Any, field: str) -> Any:
    """
    Traverse a nested dict using dot-notation field path.
    e.g. field="presentation_slide.theme.name" on a nested dict.
    Returns None if any key is missing.
    """
    parts = field.split(".")
    current = obj
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        elif isinstance(current, list) and part.isdigit():
            idx = int(part)
            current = current[idx] if idx < len(current) else None
        else:
            return None
    return current


def _evaluate_condition(actual: Any, operator: str, expected: Any) -> bool:
    """Return True if the condition passes."""
    if operator == "equals":
        return str(actual).lower() == str(expected).lower() if actual is not None else False
    if operator == "not_equals":
        return str(actual).lower() != str(expected).lower() if actual is not None else True
    if operator == "contains":
        if isinstance(actual, list):
            return expected in actual
        return str(expected).lower() in str(actual).lower() if actual is not None else False
    if operator == "not_contains":
        if isinstance(actual, list):
            return expected not in actual
        return str(expected).lower() not in str(actual).lower() if actual is not None else True
    if operator == "exists":
        return actual is not None and actual != "" and actual != []
    if operator == "not_exists":
        return actual is None or actual == "" or actual == []
    if operator == "matches_regex":
        if actual is None:
            return False
        return bool(re.search(str(expected), str(actual)))
    return False


def _check_item(
    item_id: str,
    item_name: str,
    item_type: str,
    item_data: dict,
    rule: Rule,
) -> AuditResultItem:
    """Evaluate a single rule against a single PP7 item."""
    cond = rule.condition
    field = cond.get("field", "")
    operator = cond.get("operator", "equals")
    expected = cond.get("value")

    actual = _resolve(item_data, field)
    passed = _evaluate_condition(actual, operator, expected)

    if passed:
        details = f"✓ '{field}' {operator} '{expected}'"
    else:
        details = (
            f"✗ Expected '{field}' to {operator} '{expected}', "
            f"but got '{actual}'"
        )

    fix_action = rule.fix_action
    fix_available = fix_action.get("type") not in (None, "noop") and not passed

    return AuditResultItem(
        item_id=item_id,
        item_name=item_name,
        item_type=item_type,
        rule_id=rule.id,
        rule_name=rule.name,
        status="pass" if passed else "fail",
        details=details,
        fix_available=fix_available,
    )


async def run_audit(
    db: Session,
    rules: list[Rule],
) -> list[AuditResultItem]:
    """
    Main audit entry point.
    Fetches all relevant PP7 data and evaluates each rule.
    """
    results: list[AuditResultItem] = []

    # Separate rules by target so we only fetch what we need
    targets = {r.target for r in rules}

    # ── Reference data ───────────────────────────────────────────────────────
    looks_data: list[dict] = []
    themes_data: list[dict] = []
    props_data: list[dict] = []
    macros_data: list[dict] = []
    messages_data: list[dict] = []

    try:
        if "look" in targets:
            looks_data = await pp7.get_looks(db)
    except Exception:
        pass

    try:
        if "theme" in targets:
            themes_data = await pp7.get_themes(db)
    except Exception:
        pass

    try:
        if "prop" in targets:
            props_data = await pp7.get_props(db)
    except Exception:
        pass

    try:
        if "macro" in targets:
            macros_data = await pp7.get_macros(db)
    except Exception:
        pass

    try:
        if "message" in targets:
            messages_data = await pp7.get_messages(db)
    except Exception:
        pass

    # ── Evaluate look rules ──────────────────────────────────────────────────
    look_rules = [r for r in rules if r.target == "look"]
    for look in looks_data:
        lid = look.get("id", {})
        lid_str = lid.get("uuid", str(lid)) if isinstance(lid, dict) else str(lid)
        lname = look.get("name", {})
        lname_str = lname.get("string", str(lname)) if isinstance(lname, dict) else str(lname)
        for rule in look_rules:
            results.append(_check_item(lid_str, lname_str, "look", look, rule))

    # ── Evaluate theme rules ─────────────────────────────────────────────────
    theme_rules = [r for r in rules if r.target == "theme"]
    for theme in themes_data:
        tid = theme.get("id", {})
        tid_str = tid.get("uuid", str(tid)) if isinstance(tid, dict) else str(tid)
        tname = theme.get("name", {})
        tname_str = tname.get("string", str(tname)) if isinstance(tname, dict) else str(tname)
        for rule in theme_rules:
            results.append(_check_item(tid_str, tname_str, "theme", theme, rule))

    # ── Evaluate prop rules ──────────────────────────────────────────────────
    prop_rules = [r for r in rules if r.target == "prop"]
    for prop in props_data:
        pid = prop.get("id", {})
        pid_str = pid.get("uuid", str(pid)) if isinstance(pid, dict) else str(pid)
        pname = prop.get("name", {})
        pname_str = pname.get("string", str(pname)) if isinstance(pname, dict) else str(pname)
        for rule in prop_rules:
            results.append(_check_item(pid_str, pname_str, "prop", prop, rule))

    # ── Evaluate macro rules ─────────────────────────────────────────────────
    macro_rules = [r for r in rules if r.target == "macro"]
    for macro in macros_data:
        mid = macro.get("id", {})
        mid_str = mid.get("uuid", str(mid)) if isinstance(mid, dict) else str(mid)
        mname = macro.get("name", {})
        mname_str = mname.get("string", str(mname)) if isinstance(mname, dict) else str(mname)
        for rule in macro_rules:
            results.append(_check_item(mid_str, mname_str, "macro", macro, rule))

    # ── Evaluate message rules ───────────────────────────────────────────────
    message_rules = [r for r in rules if r.target == "message"]
    for msg in messages_data:
        msgid = msg.get("id", {})
        msgid_str = msgid.get("uuid", str(msgid)) if isinstance(msgid, dict) else str(msgid)
        msgname = msg.get("name", {})
        msgname_str = msgname.get("string", str(msgname)) if isinstance(msgname, dict) else str(msgname)
        for rule in message_rules:
            results.append(_check_item(msgid_str, msgname_str, "message", msg, rule))

    # ── Evaluate presentation / slide rules ──────────────────────────────────
    pres_rules = [r for r in rules if r.target in ("presentation", "slide")]
    if pres_rules:
        try:
            playlists = await pp7.get_playlists(db)
        except Exception:
            playlists = []

        for playlist in playlists:
            pl_id = playlist.get("id", {})
            pl_id_str = pl_id.get("uuid", str(pl_id)) if isinstance(pl_id, dict) else str(pl_id)
            try:
                pl_items = await pp7.get_playlist(db, pl_id_str)
            except Exception:
                continue

            # pl_items is a list of playlist items; each may have a presentation uuid
            items = pl_items if isinstance(pl_items, list) else pl_items.get("items", [])
            for item in items:
                pres_ref = item.get("presentation", item)
                uuid_obj = pres_ref.get("presentationUUID") or pres_ref.get("uuid") or pres_ref.get("id")
                if not uuid_obj:
                    continue
                uuid_str = uuid_obj.get("uuid", str(uuid_obj)) if isinstance(uuid_obj, dict) else str(uuid_obj)

                try:
                    pres = await pp7.get_presentation(db, uuid_str)
                except Exception:
                    continue

                pres_name = pres.get("presentation", pres).get("name", {})
                pres_name_str = (
                    pres_name.get("string", str(pres_name))
                    if isinstance(pres_name, dict)
                    else str(pres_name)
                )

                # Presentation-level rules
                for rule in [r for r in pres_rules if r.target == "presentation"]:
                    results.append(
                        _check_item(uuid_str, pres_name_str, "presentation", pres, rule)
                    )

                # Slide-level rules — iterate cue groups / slides
                slide_rules = [r for r in pres_rules if r.target == "slide"]
                if slide_rules:
                    pres_data = pres.get("presentation", pres)
                    cue_groups = pres_data.get("cueGroups", [])
                    for group in cue_groups:
                        cues = group.get("cues", [])
                        for cue in cues:
                            cue_id = cue.get("id", {})
                            cue_id_str = cue_id.get("uuid", str(cue_id)) if isinstance(cue_id, dict) else str(cue_id)
                            cue_name = cue.get("name") or cue.get("label") or cue_id_str
                            for rule in slide_rules:
                                results.append(
                                    _check_item(
                                        f"{uuid_str}::{cue_id_str}",
                                        f"{pres_name_str} → {cue_name}",
                                        "slide",
                                        cue,
                                        rule,
                                    )
                                )

    return results


def get_rules_for_audit(db: Session, profile_id: int | None, rule_ids: list[int] | None) -> list[Rule]:
    """Resolve the list of rules to run based on profile_id or explicit rule_ids."""
    if profile_id is not None:
        profile = db.query(Profile).filter(Profile.id == profile_id).first()
        if not profile:
            return []
        return [pr.rule for pr in sorted(profile.rules, key=lambda pr: pr.position)]
    if rule_ids:
        return db.query(Rule).filter(Rule.id.in_(rule_ids)).all()
    # Default: run all rules
    return db.query(Rule).all()
