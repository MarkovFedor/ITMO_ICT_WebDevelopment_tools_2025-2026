from fastapi import FastAPI, Depends, HTTPException
from typing_extensions import TypedDict
from typing import List, Any, Union
from models import Warrior, Profession,WarriorDefault, ProfessionDefault,WarriorProfessions, Skill, SkillDefault, SkillWarriorLink, WarriorCreate, WarriorSkillsRead
from connection import init_db, get_session
from sqlmodel import select
import logging

app = FastAPI()

logger = logging.getLogger('uvicorn.info')

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


@app.get("/warriors_list")
def warriors_list(session=Depends(get_session)) -> List[Warrior]:
    return session.exec(select(Warrior)).all()


@app.get("/warrior/{warrior_id}", response_model=WarriorSkillsRead)
def warriors_get(warrior_id: int, session=Depends(get_session)) -> Warrior:
    warrior = session.get(Warrior, warrior_id)
    return warrior


@app.post("/warrior", response_model=Warrior)
def warriors_create(warrior: WarriorCreate, session=Depends(get_session)) -> TypedDict('Response', {"status": int,"data": Warrior}):
    #Пока без проверки на существование профессии
    #warrior_to_append = warrior.model_dump()
    #temp_bd["warriors"].append(warrior_to_append)
    logger.info(warrior)
    warrior_data = warrior.model_dump(exclude={"skills_ids"})
    warrior_db = Warrior.model_validate(warrior_data)
    if warrior.skills_ids:
        skills = session.exec(select(Skill).where(Skill.id.in_(warrior.skills_ids))).all()
        warrior_db.skills = skills
    session.add(warrior_db)
    session.commit()
    session.refresh(warrior_db)
    return {"status": 200, "data": warrior}

@app.delete("/warrior/delete{warrior_id}")
def warrior_delete(warrior_id: int, session=Depends(get_session)):
    warrior = session.get(Warrior, warrior_id)
    if not warrior:
        raise HTTPException(status_code=404, detail="Warrior not found")
    session.delete(warrior)
    session.commit()
    return {"ok": True}


@app.patch("/warrior{warrior_id}")
def warrior_update(warrior_id: int, warrior: WarriorDefault, session=Depends(get_session)) -> WarriorDefault:
    db_warrior = session.get(Warrior, warrior_id)
    if not db_warrior:
        raise HTTPException(status_code=404, detail="Warrior not found")
    warrior_data = warrior.model_dump(exclude_unset=True)
    for key, value in warrior_data.items():
        setattr(db_warrior, key, value)
    session.add(db_warrior)
    session.commit()
    session.refresh(db_warrior)
    return db_warrior

@app.get("/professions_list")
def professions_list(session=Depends(get_session)) -> List[Profession]:
    return session.exec(select(Profession)).all()


@app.get("/profession/{profession_id}")
def profession_get(profession_id: int, session=Depends(get_session)) -> Profession:
    return session.get(Profession, profession_id)


@app.post("/profession")
def profession_create(prof: ProfessionDefault, session=Depends(get_session)) -> TypedDict('Response', {"status": int,"data": Profession}):
    prof = Profession.model_validate(prof)
    session.add(prof)
    session.commit()
    session.refresh(prof)
    return {"status": 200, "data": prof}

@app.put("/professioin/{profession_id}")
def profession_update(profession_id: int, profession: Warrior) -> List[Warrior]:
    warriors:List[Warrior] = []
    for war in temp_bd['warriors']:
        if war['id'] == profession_id:
            temp_bd['warriors'].remove(war)
            temp_bd['warriors'].append(profession.model_dump())
        warriors.append(Warrior(**war))
    #Понимаю, много костылей, но работает
    return warriors

@app.delete("/profession/delete/{profession_id}")
def profession_delete(profession_id: int):
    for profession in temp_bd['warriors']:
        if profession['id'] == profession_id:
            temp_bd["warriors"].remove(profession)
            break
    return {"status": 201, "message": "deleted"}

@app.get("/skills_list")
def skills_list(session=Depends(get_session)) -> List[Skill]:
    return session.exec(select(Skill)).all()

@app.get("/skill/{skill_id}")
def get_skill(skill_id:int, session=Depends(get_session)) -> List[Skill]:
    return session.get(Skill, skill_id)

@app.post("/skill")
def skill_create(skill: SkillDefault, session=Depends(get_session)) -> TypedDict('Response', {"status": int,"data": Skill}):
    #Пока без проверки на существование профессии
    #warrior_to_append = warrior.model_dump()
    #temp_bd["warriors"].append(warrior_to_append)
    skill = Skill.model_validate(skill)
    session.add(skill)
    session.commit()
    session.refresh(skill)
    return {"status": 200, "data": skill}

@app.delete("/warrior/delete{skill_id}")
def skill_delete(skill_id: int, session=Depends(get_session)):
    skill = session.get(Skill, skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    session.delete(skill)
    session.commit()
    return {"ok": True}

@app.patch("/skill{skill_id}")
def skill_update(skill_id: int, skill: SkillDefault, session=Depends(get_session)) -> SkillDefault:
    db_skill = session.get(Skill, skill_id)
    if not db_skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    skill_data = skill.model_dump(exclude_unset=True)
    for key, value in skill_data.items():
        setattr(db_skill, key, value)
    session.add(db_skill)
    session.commit()
    session.refresh(db_skill)
    return db_skill