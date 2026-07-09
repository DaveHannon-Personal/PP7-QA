"""
Audit router — run compliance checks and apply fixes.

Endpoints:
  POST /api/audit/run    — run audit for a profile or rule list
  POST /api/audit/fix    — apply fixes for specific (or all) failed items
  POST /api/audit/run-and-fix — run audit, fix all, re-run (full loop iteration)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.audit import AuditRunRequest, AuditReport, FixRequest, FixResponse, AuditResultItem
from app.services.audit_engine import run_audit, get_rules_for_audit
from app.services.fix_engine import apply_fixes
from app.services.conflict_detector import detect_conflicts

router = APIRouter(prefix="/api/audit", tags=["audit"])

# In-memory cache of last audit results (keyed by a simple run ID)
# In a production system this would be stored in DB or Redis.
_last_results: list[AuditResultItem] = []


def _annotate_last_wins(results: list[AuditResultItem], rules) -> list[AuditResultItem]:
    """
    When multiple rules target the same (item_id, field) pair, annotate all but
    the last-in-sequence as superseded. The last rule in the chain wins for fixes.
    """
    from collections import defaultdict
    # Build ordered index: (item_id, field) -> list of result indices in sequence order
    field_map: dict[tuple, list[int]] = defaultdict(list)
    for idx, r in enumerate(results):
        # Look up the rule's condition field
        rule = next((ru for ru in rules if ru.id == r.rule_id), None)
        if rule:
            field = rule.condition.get("field", "")
            if field:
                field_map[(r.item_id, field)].append(idx)

    annotated = list(results)
    for (item_id, field), indices in field_map.items():
        if len(indices) > 1:
            # All but the last are superseded
            for superseded_idx in indices[:-1]:
                r = annotated[superseded_idx]
                annotated[superseded_idx] = r.model_copy(
                    update={"details": r.details + " ⚠ Superseded by a later rule (last-rule-wins)."}
                )
    return annotated


@router.post("/run", response_model=AuditReport)
async def run_audit_endpoint(body: AuditRunRequest, db: Session = Depends(get_db)):
    global _last_results

    rules = get_rules_for_audit(db, body.profile_id, body.rule_ids)
    if not rules:
        raise HTTPException(status_code=400, detail="No rules to run. Create rules or select a profile.")

    results = await run_audit(db, rules)
    results = _annotate_last_wins(results, rules)
    _last_results = results

    conflicts = detect_conflicts(rules)

    # Resolve profile name
    profile_name = None
    if body.profile_id:
        from app.models.profile import Profile
        p = db.query(Profile).filter(Profile.id == body.profile_id).first()
        profile_name = p.name if p else None

    return AuditReport(
        profile_id=body.profile_id,
        profile_name=profile_name,
        total_items_checked=len(results),
        pass_count=sum(1 for r in results if r.status == "pass"),
        fail_count=sum(1 for r in results if r.status == "fail"),
        skip_count=sum(1 for r in results if r.status == "skipped"),
        results=results,
        conflicts=conflicts,
    )


@router.post("/fix", response_model=FixResponse)
async def fix_endpoint(body: FixRequest, db: Session = Depends(get_db)):
    if not _last_results:
        raise HTTPException(
            status_code=400,
            detail="No audit results to fix. Run an audit first.",
        )

    item_ids = None if body.result_ids == ["all"] else body.result_ids
    return await apply_fixes(db, _last_results, item_ids)


@router.post("/run-and-fix", response_model=AuditReport)
async def run_and_fix_endpoint(body: AuditRunRequest, db: Session = Depends(get_db)):
    """Run audit → fix all fixable items → re-run audit. Returns final report."""
    global _last_results

    rules = get_rules_for_audit(db, body.profile_id, body.rule_ids)
    if not rules:
        raise HTTPException(status_code=400, detail="No rules to run.")

    results = await run_audit(db, rules)
    results = _annotate_last_wins(results, rules)
    _last_results = results

    # Fix all fixable items
    await apply_fixes(db, results, item_ids=None)

    # Re-run audit and return updated report
    results = await run_audit(db, rules)
    results = _annotate_last_wins(results, rules)
    _last_results = results

    conflicts = detect_conflicts(rules)

    profile_name = None
    if body.profile_id:
        from app.models.profile import Profile
        p = db.query(Profile).filter(Profile.id == body.profile_id).first()
        profile_name = p.name if p else None

    return AuditReport(
        profile_id=body.profile_id,
        profile_name=profile_name,
        total_items_checked=len(results),
        pass_count=sum(1 for r in results if r.status == "pass"),
        fail_count=sum(1 for r in results if r.status == "fail"),
        skip_count=sum(1 for r in results if r.status == "skipped"),
        results=results,
        conflicts=conflicts,
    )
