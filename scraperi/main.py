import uvicorn
import re
from fastapi import FastAPI, Body
from celery.result import AsyncResult
from .scraper_links import detect_last_page
from .scraper_chipoteka import detect_last_page as detect_last_page_chip
from .celery_app import app as celery_client 
from database.db import artikli

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Service running"}

@app.post("/scrape/instar")
async def scrape_instar():
    task = celery_client.send_task('scraperi.scraper_instar.scrape_instar', queue='instar_queue')
    return {"task_id": task.id}

@app.post("/scrape/links")
async def scrape_links_full():
    last = detect_last_page()
    if last == 0:
        return {"task_ids": [], "message": "No pages"}
    task_ids = []
    start = 1
    while start <= last:
        end = min(start + 4, last)  
        t = celery_client.send_task('scraperi.scraper_links.scrape_links_chunk', args=[start, end], queue='links_queue')
        task_ids.append(t.id)
        start = end + 1
    return {"task_ids": task_ids, "pages": last, "chunk_size": 5}

@app.post("/scrape/chipoteka")
async def scrape_chipoteka_full():
    last = detect_last_page_chip()
    if last == 0:
        return {"task_ids": [], "message": "No pages"}
    task_ids = []
    start = 1
    while start <= last:
        end = min(start + 4, last)
        t = celery_client.send_task('scraperi.scraper_chipoteka.scrape_chipoteka_chunk', args=[start, end], queue='chipoteka_queue')
        task_ids.append(t.id)
        start = end + 1
    return {"task_ids": task_ids, "pages": last, "chunk_size": 5}


@app.get("/results/{task_id}")
async def get_task_result(task_id: str):
    result = AsyncResult(task_id, app=celery_client)
    if result.successful():
        return {"status": result.state, "result": result.result}
    if result.failed():
        return {"status": result.state, "error": str(result.result)}
    return {"status": result.state}


def _merge_task_ids(ids: list[str]):
    all_items = []
    states: dict[str, str] = {}
    pending: list[str] = []
    for task_id in ids:
        r = AsyncResult(task_id, app=celery_client)
        states[task_id] = r.state
        if r.successful() and isinstance(r.result, list):
            all_items.extend(r.result)
        elif r.state in ("PENDING", "STARTED"):
            pending.append(task_id)
    return {
        "merged_count": len(all_items),
        "items": all_items,
        "states": states,
        "incomplete": pending,
    }

@app.post("/results/merge")
async def merge_results_post(raw: str = Body(..., media_type="text/plain")):
    """
    Primjer posta:
    "92855e25-a822-4f4d-ad2d-169e77d345ac",
    "7e03e933-a859-46bb-8fae-36e4551e00bb",
    "0d2cff1a-e70c-423a-8e47-2b163a125c74"
    """
    ids = re.findall(r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}', raw)
    return _merge_task_ids(ids)


@app.post("/results/save")
async def save_results_post(raw: str = Body(..., media_type="text/plain")):
    ids = re.findall(r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}', raw)
    merged = _merge_task_ids(ids)
    items = merged.get("items", [])
    inserted = 0
    error = None
    if items:
        try:
            res = artikli.insert_many(items)
            inserted = len(res.inserted_ids)
        except Exception as e:
            error = str(e)
    return {
        "received_tasks": ids,
        "incomplete": merged.get("incomplete", []),
        "merged_count": merged.get("merged_count", 0),
        "saved": inserted,
        "error": error,
    }


@app.delete("/database/clear")
async def clear_database():
    try:
        res = artikli.delete_many({})
        return {"deleted": res.deleted_count}
    except Exception as e:
        return {"deleted": 0, "error": str(e)}


if __name__ == "__main__":
    uvicorn.run("scraperi.main:app", reload=True)

