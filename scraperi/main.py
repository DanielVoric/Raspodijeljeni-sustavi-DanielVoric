import uvicorn
import re
from datetime import datetime
from fastapi import FastAPI, Body
from celery.result import AsyncResult
from fastapi.staticfiles import StaticFiles
from .celery_app import app as celery_client 
from database.db import artikli

app = FastAPI()

app.mount("/ui", StaticFiles(directory="static", html=True), name="ui")


@app.post("/scrape/all")
async def scrape_all_shops():
    # Instar
    instar_task = celery_client.send_task('scraperi.scraper_instar.scrape_instar', queue='instar_queue')

    PAGE_CAP = 30
    CHUNK_SIZE = 5 

    links_ids: list[str] = []
    chip_ids: list[str] = []

    start = 1
    while start <= PAGE_CAP:
        end = min(start + (CHUNK_SIZE - 1), PAGE_CAP)

        # Links
        t1 = celery_client.send_task(
            'scraperi.scraper_links.scrape_links_chunk',
            args=[start, end],
            queue='links_queue',
        )
        links_ids.append(t1.id)

        # Chipoteka
        t2 = celery_client.send_task(
            'scraperi.scraper_chipoteka.scrape_chipoteka_chunk',
            args=[start, end],
            queue='chipoteka_queue',
        )
        chip_ids.append(t2.id)

        start = end + 1

    all_ids = [instar_task.id] + links_ids + chip_ids
    return {
        "instar": {"task_id": instar_task.id},
        "links": {"task_ids": links_ids, "pages": PAGE_CAP, "chunk_size": CHUNK_SIZE},
        "chipoteka": {"task_ids": chip_ids, "pages": PAGE_CAP, "chunk_size": CHUNK_SIZE},
        "all_task_ids": all_ids,
        "all_task_ids_csv": ",".join(all_ids),
    }

@app.get("/database/ping")
async def database_ping():
    try:
        client = artikli.database.client
        client.admin.command('ping')
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}

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
    ts = datetime.now().strftime("%d.%m.%Y/%H:%M")
    for it in all_items:
        if isinstance(it, dict) and "scraped_at" not in it:
            it["scraped_at"] = ts
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


@app.get("/database/list")
async def database_list():
    try:
        cursor = artikli.find({}, {"_id": 0})
        items = list(cursor)
        return {"count": len(items), "items": items}
    except Exception as e:
        return {"count": 0, "items": [], "error": str(e)}


@app.post("/results/save")
async def save_results_post(raw: str = Body(..., media_type="text/plain")):
    ids = re.findall(r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}', raw)
    merged = _merge_task_ids(ids)
    items = merged.get("items", [])
    inserted = 0
    error = None
    if items:
        try:
            ts = datetime.now().strftime("%d.%m.%Y/%H:%M")
            for it in items:
                if isinstance(it, dict) and "scraped_at" not in it:
                    it["scraped_at"] = ts
            res = artikli.insert_many(items, ordered=False)
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

