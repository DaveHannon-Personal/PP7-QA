"""
Fix Engine — applies PP7 API corrections for audit violations.

For each failed AuditResultItem with fix_available=True:
  - Looks up the rule's fix_action
  - Dispatches to the appropriate PP7 API call
  - Records success or failure

Supported fix_action types:
  set_field     — PUT updated JSON to the item's endpoint
  trigger_look  — GET /v1/look/{id}/trigger
  assign_theme  — PUT theme field on a presentation/slide
  noop          — No automatic fix available (manual intervention required)
"""
from __future__ import annotations

from sqlalchemy.orm import Session
from app.models.rule import Rule
from app.schemas.audit import AuditResultItem, FixResponse
from app.services import propresenter as pp7


async def apply_fixes(
    db: Session,
    results: list[AuditResultItem],
    item_ids: list[str] | None = None,
) -> FixResponse:
    """
    Apply fixes for the given audit result items.

    Args:
        db:       Database session.
        results:  Full list of AuditResultItem from the last audit run.
        item_ids: Specific item_id values to fix.  None = fix everything fixable.

    Returns:
        FixResponse with counts and per-item details.
    """
    fixable = [
        r for r in results
        if r.status == "fail"
        and r.fix_available
        and (item_ids is None or r.item_id in item_ids)
    ]

    fixed_count = 0
    failed_count = 0
    details: list[dict] = []

    for result in fixable:
        rule = db.query(Rule).filter(Rule.id == result.rule_id).first()
        if not rule:
            details.append({"item_id": result.item_id, "status": "error", "message": "Rule not found"})
            failed_count += 1
            continue

        fix = rule.fix_action
        fix_type = fix.get("type", "noop")

        try:
            if fix_type == "noop":
                details.append({
                    "item_id": result.item_id,
                    "item_name": result.item_name,
                    "status": "skipped",
                    "message": "No automatic fix available — manual correction required",
                })
                continue

            elif fix_type == "trigger_look":
                look_id = fix.get("value") or result.item_id
                await pp7.trigger_look(db, look_id)
                details.append({
                    "item_id": result.item_id,
                    "item_name": result.item_name,
                    "status": "fixed",
                    "message": f"Triggered look '{look_id}'",
                })
                fixed_count += 1

            elif fix_type == "set_field":
                field = fix.get("field", "")
                value = fix.get("value")
                item_type = result.item_type
                item_id = result.item_id.split("::")[0]  # strip slide suffix

                if item_type == "look":
                    current = await pp7.get_look(db, item_id)
                    _set_nested(current, field, value)
                    await pp7.set_look(db, item_id, current)

                elif item_type == "prop":
                    current = await pp7.get_prop(db, item_id)
                    _set_nested(current, field, value)
                    await pp7.set_prop(db, item_id, current)

                elif item_type == "macro":
                    current = await pp7.get_macro(db, item_id)
                    _set_nested(current, field, value)
                    await pp7.set_macro(db, item_id, current)

                elif item_type == "message":
                    current = await pp7.get_messages(db)
                    msg = next((m for m in current if _extract_id(m) == item_id), None)
                    if msg:
                        _set_nested(msg, field, value)
                        await pp7.set_message(db, item_id, msg)

                else:
                    details.append({
                        "item_id": result.item_id,
                        "item_name": result.item_name,
                        "status": "skipped",
                        "message": f"set_field not yet supported for target '{item_type}'",
                    })
                    continue

                details.append({
                    "item_id": result.item_id,
                    "item_name": result.item_name,
                    "status": "fixed",
                    "message": f"Set '{field}' = '{value}'",
                })
                fixed_count += 1

            elif fix_type == "assign_theme":
                # Theme assignment requires presentation-level update
                details.append({
                    "item_id": result.item_id,
                    "item_name": result.item_name,
                    "status": "skipped",
                    "message": "assign_theme: manual theme reassignment required via ProPresenter UI",
                })

            else:
                details.append({
                    "item_id": result.item_id,
                    "item_name": result.item_name,
                    "status": "skipped",
                    "message": f"Unknown fix type: '{fix_type}'",
                })

        except Exception as exc:
            details.append({
                "item_id": result.item_id,
                "item_name": result.item_name,
                "status": "error",
                "message": str(exc),
            })
            failed_count += 1

    return FixResponse(
        fixed_count=fixed_count,
        failed_count=failed_count,
        details=details,
    )


def _extract_id(obj: dict) -> str:
    """Extract UUID string from a PP7 ID object."""
    oid = obj.get("id", obj)
    if isinstance(oid, dict):
        return oid.get("uuid", str(oid))
    return str(oid)


def _set_nested(obj: dict, field: str, value) -> None:
    """Set a value in a nested dict using dot-notation path (in-place)."""
    parts = field.split(".")
    current = obj
    for part in parts[:-1]:
        if isinstance(current, dict):
            current = current.setdefault(part, {})
        else:
            return
    if isinstance(current, dict):
        current[parts[-1]] = value
