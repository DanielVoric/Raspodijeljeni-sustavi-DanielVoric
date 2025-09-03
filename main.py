import uvicorn
from fastapi import FastAPI
from db import artikli


app = FastAPI()


@app.get("/")
async def message():
    try:
        artikli.find_one()
        return {"data": "Baza je spojena"}
    except Exception as e:
        return {"data": "Greška u spajanju", "error": str(e)}


@app.get("/test")
def test1():
    return {"status": "ok"}

@app.get("/test-artikli")
def test_artikli():
    artikli_list = list(artikli.find())
    for a in artikli_list:
        a["_id"] = str(a["_id"])
    return {"artikli": artikli_list}


if __name__ == "__main__":
    uvicorn.run("main:app")

