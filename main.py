from fastapi import FastAPI

app = FastAPI()

temp_bd = [{
    "id": 1,
    "race": "director",
    "name": "Мартынов Дмитрий",
    "level": 12,
    "profession": {
        "id": 1,
        "title": "Влиятельный человек",
        "description": "Эксперт по всем вопросам"
    },
},
    {
        "id": 2,
        "race": "worker",
        "name": "Андрей Косякин",
        "level": 12,
        "profession": {
            "id": 1,
            "title": "Дельфист-гребец",
            "description": "Уважаемый сотрудник"
        },
    },
]

@app.get("/warriors_list")
def warriors_list():
    return temp_bd

@app.get("/warrior/{warrior_id}")
def warriors_list(warrior_id: int):
    return [warrior for warrior in temp_bd if warrior.get("id") == warrior_id]

@app.post("/warrior")
def warriors_list(warrior: dict):
    temp_bd.append(warrior)
    return {"status": 200, "data": warrior}

@app.delete("/warrior/delete{warrior_id}")
def warrior_delete(warrior_id: int):
    for i, warrior in enumerate(temp_bd):
        if warrior.get("id") == warrior_id:
            temp_bd.pop(i)
            break
    return {"status": 201, "message": "deleted"}

@app.put("/warrior{warrior_id}")
def warrior_update(warrior_id: int, warrior: dict):
    for i, war in enumerate(temp_bd):
        if war.get("id") == warrior_id:
            temp_bd[i] = warrior
    return temp_bd