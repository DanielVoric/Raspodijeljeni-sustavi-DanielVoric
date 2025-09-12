import os
from celery import Celery

REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

app = Celery(
	'scraper_tasks',
	broker=REDIS_URL,
	backend=REDIS_URL,
	include=[
		'scraperi.scraper_instar',
		'scraperi.scraper_links',
		'scraperi.scraper_chipoteka',
	],
)

app.conf.task_routes = {
	'scraperi.scraper_instar.scrape_instar': {'queue': 'instar_queue'},
	'scraperi.scraper_links.scrape_links_chunk': {'queue': 'links_queue'},
	'scraperi.scraper_chipoteka.scrape_chipoteka_chunk': {'queue': 'chipoteka_queue'},
}

