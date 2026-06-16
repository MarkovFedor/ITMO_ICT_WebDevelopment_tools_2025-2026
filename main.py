from fastapi import FastAPI, Depends, HTTPException, status, APIRouter
from typing import List
from auth import get_current_user, authenticate_user, get_user, create_access_token, get_password_hash, verify_password
from models import (
    Warrior,
    Profession,
    ProfessionDefault,
    Skill,
    SkillDefault,
    WarriorCreate,
    WarriorSkillsRead,
    User,
    UserCreate,
    UserLogin,
    UserPasswordUpdate
)
from connection import init_db, get_session
from sqlmodel import select
from fastapi.security import HTTPBearer

app = FastAPI()
protected = APIRouter(dependencies=[Depends(get_current_user)])
security = HTTPBearer()  
app.include_router(protected)
@app.on_event("startup")
def on_startup():
    init_db()
temp_bd = {
    "professions": 
    [
        {
            "id": 1,
            "title": "Влиятельный человек",
            "description": "Эксперт по всем вопросам"
        },
        {
            "id": 2,
            "title": "Дельфист-гребец",
            "description": "Уважаемый сотрудник"
        }
    ],
    "warriors":
    [
        {
            "id": 1,
            "race": "director",
            "name": "Мартынов Дмитрий",
            "level": 12,
            "profession_id": 1,
            "skills":
            [{
                "id": 1,
                "name": "Купле-продажа компрессоров",
                "description": ""

            },
        {
            "id": 2,
            "name": "Оценка имущества",
            "description": ""

        }]
        },
        {
    "id": 2,
    "race": "worker",
    "name": "Андрей Косякин",
    "level": 12,
    "profession_id": 2,
            "skills": []
        }

    ]
}




@protected.get("/warrior/{warrior_id}", response_model=WarriorSkillsRead)
def warriors_get(warrior_id: int, session=Depends(get_session)):
    warrior = session.get(Warrior, warrior_id)
    if not warrior:
        raise HTTPException(status_code=404, detail="Warrior not found")
    return warrior


@protected.post("/warrior", response_model=Warrior, status_code=status.HTTP_201_CREATED)
def warriors_create(warrior: WarriorCreate, session=Depends(get_session)):
    if warrior.profession_id is not None:
        profession = session.get(Profession, warrior.profession_id)
        if not profession:
            raise HTTPException(
                status_code=404, detail="Profession not found"
            )

    warrior_data = warrior.model_dump(exclude={"skills_ids"})
    warrior_db = Warrior.model_validate(warrior_data)

    if warrior.skills_ids:
        skills = session.exec(
            select(Skill).where(Skill.id.in_(warrior.skills_ids))
        ).all()
        if len(skills) != len(warrior.skills_ids):
            raise HTTPException(
                status_code=400, detail="One or more skill IDs do not exist"
            )
        warrior_db.skills = skills

    session.add(warrior_db)
    session.commit()
    session.refresh(warrior_db)
    return warrior_db


@protected.delete("/warrior/{warrior_id}", status_code=status.HTTP_200_OK)
def warrior_delete(warrior_id: int, session=Depends(get_session)):
    warrior = session.get(Warrior, warrior_id)
    if not warrior:
        raise HTTPException(status_code=404, detail="Warrior not found")
    session.delete(warrior)
    session.commit()
    return {"ok": True}


@protected.patch("/warrior/{warrior_id}", response_model=Warrior)
def warrior_update(
    warrior_id: int, warrior: WarriorCreate, session=Depends(get_session)
):
    db_warrior = session.get(Warrior, warrior_id)
    if not db_warrior:
        raise HTTPException(status_code=404, detail="Warrior not found")

    warrior_data = warrior.model_dump(exclude_unset=True, exclude={"skills_ids"})

    if "profession_id" in warrior_data and warrior_data["profession_id"] is not None:
        profession = session.get(Profession, warrior_data["profession_id"])
        if not profession:
            raise HTTPException(status_code=404, detail="Profession not found")

    for key, value in warrior_data.items():
        setattr(db_warrior, key, value)

    if warrior.skills_ids is not None:
        skills = session.exec(
            select(Skill).where(Skill.id.in_(warrior.skills_ids))
        ).all()
        if len(skills) != len(warrior.skills_ids):
            raise HTTPException(status_code=400, detail="One or more skill IDs do not exist")
        db_warrior.skills = skills

    session.add(db_warrior)
    session.commit()
    session.refresh(db_warrior)
    return db_warrior


@app.get("/professions_list", response_model=List[Profession])
def professions_list(session=Depends(get_session)):
    return session.exec(select(Profession)).all()


@app.get("/profession/{profession_id}", response_model=Profession)
def profession_get(profession_id: int, session=Depends(get_session)):
    profession = session.get(Profession, profession_id)
    if not profession:
        raise HTTPException(status_code=404, detail="Profession not found")
    return profession


@app.post("/profession", response_model=Profession, status_code=status.HTTP_201_CREATED)
def profession_create(prof: ProfessionDefault, session=Depends(get_session)):
    prof_db = Profession.model_validate(prof)
    session.add(prof_db)
    session.commit()
    session.refresh(prof_db)
    return prof_db


@app.put("/profession/{profession_id}", response_model=Profession)
def profession_update(
    profession_id: int, prof_data: ProfessionDefault, session=Depends(get_session)
):
    profession = session.get(Profession, profession_id)
    if not profession:
        raise HTTPException(status_code=404, detail="Profession not found")
    update_data = prof_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(profession, key, value)
    session.add(profession)
    session.commit()
    session.refresh(profession)
    return profession


@app.delete("/profession/{profession_id}", status_code=status.HTTP_200_OK)
def profession_delete(profession_id: int, session=Depends(get_session)):
    profession = session.get(Profession, profession_id)
    if not profession:
        raise HTTPException(status_code=404, detail="Profession not found")

    warriors_with_prof = session.exec(
        select(Warrior).where(Warrior.profession_id == profession_id)
    ).all()
    if warriors_with_prof:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete profession because it is assigned to warriors",
        )

    session.delete(profession)
    session.commit()
    return {"ok": True}


@app.get("/skills_list", response_model=List[Skill])
def skills_list(session=Depends(get_session)):
    return session.exec(select(Skill)).all()


@app.get("/skill/{skill_id}", response_model=Skill)
def get_skill(skill_id: int, session=Depends(get_session)):
    skill = session.get(Skill, skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return skill


@app.post("/skill", response_model=Skill, status_code=status.HTTP_201_CREATED)
def skill_create(skill: SkillDefault, session=Depends(get_session)):
    skill_db = Skill.model_validate(skill)
    session.add(skill_db)
    session.commit()
    session.refresh(skill_db)
    return skill_db


@app.delete("/skill/{skill_id}", status_code=status.HTTP_200_OK)
def skill_delete(skill_id: int, session=Depends(get_session)):
    skill = session.get(Skill, skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    session.delete(skill)
    session.commit()
    return {"ok": True}


@app.patch("/skill/{skill_id}", response_model=Skill)
def skill_update(skill_id: int, skill_data: SkillDefault, session=Depends(get_session)):
    db_skill = session.get(Skill, skill_id)
    if not db_skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    update_data = skill_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_skill, key, value)
    session.add(db_skill)
    session.commit()
    session.refresh(db_skill)
    return db_skill

@app.post("/register", status_code=status.HTTP_201_CREATED)
def register(user: UserCreate, session = Depends(get_session)):
    if session.exec(select(User).where(User.username == user.username)).first():
        raise HTTPException(status_code=400, detail="Username already exists")
    hashed = get_password_hash(user.password)
    new_user = User(username=user.username, password_hash=hashed)
    session.add(new_user)
    session.commit()
    return {"message": "User created"}

@app.post("/token")
def login(user: UserLogin, session = Depends(get_session)):
    db_user = authenticate_user(session, user.username, user.password)
    if not db_user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(data={"sub": db_user.username})
    return {"access_token": token, "token_type": "bearer"}

@protected.get("/warriors_list")
def warriors_list(credentials: str = Depends(security), session = Depends(get_session),
                  current_user: User = Depends(get_current_user)):
    return session.exec(select(Warrior)).all()

@app.post("/change_password")
def change_password( user: UserPasswordUpdate, session = Depends(get_session)):
    selected_user = session.exec(select(User).where(User.username == user.username)).first()
    if not selected_user:
        raise HTTPException(status_code = 400, detail = "User not found")
    
    if not verify_password(user.password, selected_user.password_hash):
        raise HTTPException(status_code = 400, detail = "Wrong password")
    
    selected_user.password_hash = get_password_hash(user.new_password)
    session.commit()

    return {"message": "password changed successfully"}