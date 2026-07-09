"""Rules router — CRUD for individual QA rules + conflict detection."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.rule import Rule
from app.schemas.rule import RuleCreate, RuleUpdate, RuleRead
from app.schemas.audit import RuleConflict
from app.services.conflict_detector import detect_conflicts

router = APIRouter(prefix="/api/rules", tags=["rules"])


@router.get("", response_model=list[RuleRead])
def list_rules(db: Session = Depends(get_db)):
    return db.query(Rule).order_by(Rule.created_at).all()


@router.post("", response_model=RuleRead, status_code=201)
def create_rule(body: RuleCreate, db: Session = Depends(get_db)):
    rule = Rule(
        name=body.name,
        description=body.description,
        target=body.target,
        severity=body.severity,
    )
    rule.condition = body.condition.model_dump()
    rule.fix_action = body.fix_action.model_dump()
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.get("/{rule_id}", response_model=RuleRead)
def get_rule(rule_id: int, db: Session = Depends(get_db)):
    rule = db.query(Rule).filter(Rule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return rule


@router.put("/{rule_id}", response_model=RuleRead)
def update_rule(rule_id: int, body: RuleUpdate, db: Session = Depends(get_db)):
    rule = db.query(Rule).filter(Rule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    if body.name is not None:
        rule.name = body.name
    if body.description is not None:
        rule.description = body.description
    if body.target is not None:
        rule.target = body.target
    if body.severity is not None:
        rule.severity = body.severity
    if body.condition is not None:
        rule.condition = body.condition.model_dump()
    if body.fix_action is not None:
        rule.fix_action = body.fix_action.model_dump()
    db.commit()
    db.refresh(rule)
    return rule


@router.delete("/{rule_id}", status_code=204)
def delete_rule(rule_id: int, db: Session = Depends(get_db)):
    rule = db.query(Rule).filter(Rule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    db.delete(rule)
    db.commit()


# ── Conflict detection ───────────────────────────────────────────────────────

@router.get("/conflicts", response_model=list[RuleConflict])
def get_all_conflicts(db: Session = Depends(get_db)):
    """Return all conflicts across every rule in the library."""
    rules = db.query(Rule).order_by(Rule.created_at).all()
    return detect_conflicts(rules)


@router.post("/conflicts/check", response_model=list[RuleConflict])
def check_conflicts_for_ids(rule_ids: list[int], db: Session = Depends(get_db)):
    """Return conflicts for a specific ordered list of rule IDs (e.g. a profile's rules)."""
    rules = []
    for rid in rule_ids:
        r = db.query(Rule).filter(Rule.id == rid).first()
        if r:
            rules.append(r)
    return detect_conflicts(rules)
