from fastapi import FastAPI
from typing_extensions import TypedDict
from typing import List, Any
from models import Warrior, Profession
app = FastAPI()

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
def warriors_list() -> List[Warrior]:
    warrior_list:List[Warrior] = []
    for warrior in temp_bd['warriors']:
        warrior_list.append(Warrior(**warrior))
    return warrior_list


@app.get("/warrior/{warrior_id}")
def warriors_get(warrior_id: int) -> List[Warrior]:
    warrior_list:List[Warrior] = []
    for warrior in temp_bd['warriors']:
        if warrior.get('id') == warrior_id:
            warrior_list.append(Warrior(**warrior))
    return warrior_list


@app.post("/warrior")
def warriors_create(warrior: Warrior) -> TypedDict('Response', {"status": int, "data": Warrior}):
    #Пока без проверки на существование профессии
    warrior_to_append = warrior.model_dump()
    temp_bd["warriors"].append(warrior_to_append)
    return {"status": 200, "data": warrior}


@app.delete("/warrior/delete{warrior_id}")
def warrior_delete(warrior_id: int):
    for warrior in temp_bd['warriors']:
        if warrior['id'] == warrior_id:
            temp_bd["warriors"].remove(warrior)
            break
    return {"status": 201, "message": "deleted"}


@app.put("/warrior/{warrior_id}")
def warrior_update(warrior_id: int, warrior: Warrior) -> List[Warrior]:
    warriors:List[Warrior] = []
    for war in temp_bd['warriors']:
        if war['id'] == warrior_id:
            temp_bd['warriors'].remove(war)
            temp_bd['warriors'].append(warrior.model_dump())
        warriors.append(Warrior(**war))
    #Понимаю, много костылей, но работает
    return warriors

@app.get("/professions")
def get_professions() -> List[Profession]:
    professions:List[Profession] = [Profession(**prof) for prof in temp_bd['professions']]
    return professions

@app.get("/profession/{profession_id}")
def get_profession(profession_id: int) -> List[Profession]:
    profession = [Profession(**prof) for prof in temp_bd['professions'] if prof['id'] == profession_id]
    return profession

@app.post("/profession")
def create_profession(profession: Profession) -> TypedDict('Response', {"status": int, "data": Profession}):
    temp_bd['professions'].append(profession.model_dump())
    return {"status": 200, "data": profession}

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
def warrior_delete(profession_id: int):
    for profession in temp_bd['warriors']:
        if profession['id'] == profession_id:
            temp_bd["warriors"].remove(profession)
            break
    return {"status": 201, "message": "deleted"}