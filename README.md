# AkcijoSC – Distribuirani webscraper
AkcijoSC je distribuirani sustav za scraping koji koristi FastAPI, celery workere s redisom kao brokerom te MongoDB za pohranu podataka. Celery koristi gevent pool radnika (optimizacija).

## Preduvjeti
- Docker Desktop (Windows, WSL2)

ILI

- Redis server [Redis website](https://redis.io/download)
- MongoDB [MongoDB website](https://www.mongodb.com/try/download/community)
- Python paketi iz `requirements.txt`.

## Konfiguracija

MongoDB koristi vezu na moj database, za promjenu je potreban samo drugi URI, ili odkomentirati localhost databaase u `.env.example` i `docker-compose.yml`

## Opcija A: Pokretanje uz Docker

Iz root projekta pokrenite:

```
docker compose build --no-cache
docker compose up -d
docker compose ps
```

Otvorite:
- UI: http://localhost:8000/ui za GUI sučelje
- Docs: http://localhost:8000/docs za Swagger UI


## Opcija B: Pokretanje lokalno (bez Dockera)

1) Kreirajte i aktivirajte virtualno okruženje, pa instalirajte `requirements.txt`:
```
py -3.11 -m venv venv
venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
```

2) Postavite varijable okruženja (PowerShell):
```
$env:REDIS_URL = "redis://localhost:6379/0"
$env:MONGODB_URI = "mongodb+srv://<user>:<pass>@<cluster>/?retryWrites=true&w=majority" (za vaš db)
```

3) Pokrenite Redis:

- Instalirajte Redis lokalno i pokrenite ga na portu 6379.
- Navigirajte se putem Powershella u instalation folder i upišite komandu redis-server.
- Iz drugog Powershella isprobajte funkcionalnost sa: redis-cli ping

4) Pokrenite Celery workere (u odvojenim terminalima):

!Važno!
Ako u postavkama nije dozvoljeno izvršavanje vanjskih skripti (i ne želite staviti unrestrited) potrebno je upisati ovu naredbu u svaki terminal.
Za bolje performanse povečati broj nakon -c. (concurrency level)
```
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
```

```
venv\\Scripts\\Activate.ps1
python -m celery -A scraperi.celery_app:app worker -Q links_queue -P gevent -c 100 -Ofair -n links@%h -l INFO
```
```
venv\\Scripts\\Activate.ps1
python -m celery -A scraperi.celery_app:app worker -Q chipoteka_queue -P gevent -c 100 -Ofair -n chipoteka@%h -l INFO
```
```powershell
venv\\Scripts\\Activate.ps1
python -m celery -A scraperi.celery_app:app worker -Q instar_queue -P gevent -c 100 -Ofair -n instar@%h -l INFO
```

5) Pokrenite API:
```powershell
venv\\Scripts\\Activate.ps1
uvicorn scraperi.main:app --host 0.0.0.0 --port 8000
```

6) Otvorite UI i koristite aplikaciju:
- UI: http://localhost:8000/ui
- Docs: http://localhost:8000/docs za Swagger UI


## Tijek korištenja
1) U UI-ju kliknite “Start Scrape” za pokretanje zadataka.
2) Pričekajte da merge prikaže pronađene stavke i da nema više pending zadataka.
3) Kliknite “Save to DB” za spremanje rezultata u MongoDB.
4) Kliknite Load Table (from merge)
4) “Load from DB” učitava spremljene stavke.

## API rute
- POST `/scrape/all` zakazuje scraping (Instar + Links + Chipoteka); vraća task ID-ove.
- POST `/results/merge` spaja završene rezultate (iz task id-eva); vraća stavke.
- POST `/results/save` sprema spojene stavke u Mongo (iz task id-eva); vraća broj spremljenih.
- GET `/database/list` vraća sve spremljene stavke.
- DELETE `/database/clear` briše sve iz kolekcije.
- GET `/database/ping` brza provjera konekcije na bazu.

## Čišćenje / reset

Samo ovaj projekt:
```powershell
docker compose down --rmi all --volumes --remove-orphans
```

---
Javni repozitorij za projekt iz kolegija Raspodijeljeni Sustavi.

