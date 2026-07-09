"""Profiles router — CRUD for rule collections (profiles)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.rule import Rule
from app.models.profile import Profile, ProfileRule
from app.schemas.profile import ProfileCreate, ProfileUpdate, ProfileRead, ProfileSummary

router = APIRouter(prefix="/api/profiles", tags=["profiles"])


def _attach_rules(profile: Profile, rule_ids: list[int], db: Session) -> None:
    """Replace all rules on a profile with the given ordered rule_ids."""
    # Remove existing associations
    db.query(ProfileRule).filter(ProfileRule.profile_id == profile.id).delete()
    for pos, rid in enumerate(rule_ids):
        rule = db.query(Rule).filter(Rule.id == rid).first()
        if not rule:
            raise HTTPException(status_code=404, detail=f"Rule {rid} not found")
        db.add(ProfileRule(profile_id=profile.id, rule_id=rid, position=pos))


@router.get("", response_model=list[ProfileSummary])
def list_profiles(db: Session = Depends(get_db)):
    profiles = db.query(Profile).order_by(Profile.created_at).all()
    return [
        ProfileSummary(
            id=p.id,
            name=p.name,
            description=p.description,
            rule_count=len(p.rules),
            created_at=p.created_at,
        )
        for p in profiles
    ]


@router.post("", response_model=ProfileRead, status_code=201)
def create_profile(body: ProfileCreate, db: Session = Depends(get_db)):
    existing = db.query(Profile).filter(Profile.name == body.name).first()
    if existing:
        raise HTTPException(status_code=409, detail="A profile with that name already exists")
    profile = Profile(name=body.name, description=body.description)
    db.add(profile)
    db.flush()  # get profile.id
    _attach_rules(profile, body.rule_ids, db)
    db.commit()
    db.refresh(profile)
    return _to_read(profile)


@router.get("/{profile_id}", response_model=ProfileRead)
def get_profile(profile_id: int, db: Session = Depends(get_db)):
    profile = db.query(Profile).filter(Profile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return _to_read(profile)


@router.put("/{profile_id}", response_model=ProfileRead)
def update_profile(profile_id: int, body: ProfileUpdate, db: Session = Depends(get_db)):
    profile = db.query(Profile).filter(Profile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    if body.name is not None:
        profile.name = body.name
    if body.description is not None:
        profile.description = body.description
    if body.rule_ids is not None:
        _attach_rules(profile, body.rule_ids, db)
    db.commit()
    db.refresh(profile)
    return _to_read(profile)


@router.delete("/{profile_id}", status_code=204)
def delete_profile(profile_id: int, db: Session = Depends(get_db)):
    profile = db.query(Profile).filter(Profile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    db.delete(profile)
    db.commit()


def _to_read(profile: Profile) -> ProfileRead:
    from app.schemas.rule import RuleRead
    rules = [
        RuleRead(
            id=pr.rule.id,
            name=pr.rule.name,
            description=pr.rule.description,
            target=pr.rule.target,
            severity=pr.rule.severity,
            condition=pr.rule.condition,
            fix_action=pr.rule.fix_action,
            created_at=pr.rule.created_at,
            updated_at=pr.rule.updated_at,
        )
        for pr in sorted(profile.rules, key=lambda x: x.position)
    ]
    return ProfileRead(
        id=profile.id,
        name=profile.name,
        description=profile.description,
        rules=rules,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )
