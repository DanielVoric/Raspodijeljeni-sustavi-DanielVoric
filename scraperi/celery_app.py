from celery import Celery

app = Celery('scraper_tasks', broker='redis://localhost:6379/0', backend='redis://localhost:6379/0', include=['scraperi.scraper_instar'],)

app.conf.task_routes = {
	'scraperi.scraper_instar.scrape_instar': {'queue': 'instar_queue'},
}

