from fastapi import FastAPI, HTTPException
from parse_data import parse_profs
from models import ParseRequest
from parse_data import generate_warriors

app = FastAPI()

@app.post("/parse")
def parse(parse_req: ParseRequest | None = None):
    try:
        count = parse_profs(parse_req)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate")
def generate(count: int):
    try:
        generate_warriors(count)
        return {"status":"success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))