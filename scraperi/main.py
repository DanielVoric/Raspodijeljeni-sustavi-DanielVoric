import uvicorn
from fastapi import FastAPI
from db import artikli
from celery import Celery
from celery.result import AsyncResult


app = FastAPI()

celery_client = Celery('scraper_tasks', broker='redis://localhost:6379/0', backend='redis://localhost:6379/0')


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


@app.post("/scrape/instar")
async def start_instar_scrape():
    task = celery_client.send_task('scraperi.scraper_instar.scrape_instar', queue='instar_queue')
    return {"task_id": task.id}


@app.get("/results/{task_id}")
async def get_task_result(task_id: str):
    result = AsyncResult(task_id, app=celery_client)
    if result.successful():
        return {"status": result.state, "result": result.result}
    if result.failed():
        return {"status": result.state, "error": str(result.result)}
    return {"status": result.state}


if __name__ == "__main__":
    uvicorn.run("main:app")

