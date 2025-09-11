from celery import Celery

app = Celery(
	'scraper_tasks',
	broker='redis://localhost:6379/0',
	backend='redis://localhost:6379/0',
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

