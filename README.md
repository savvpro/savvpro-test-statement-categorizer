# Statement Categorizer

A web app that reads a bank statement (CSV) for a small PC hardware business, sorts every transaction into a tax category, and lets you review and fix the rows it is not sure about.

This file covers setup and running only. See `DESIGN.md` for how the categorizer decides.

## Requirements

- Python 3.11 or newer
- Node.js 18 or newer and npm
- Docker and Docker Compose 

## Run with Docker

From the repository root:

```
cp .env.example .env
docker compose up --build
```

Then open:

- App: http://localhost:5173
- API docs: http://localhost:8000/docs

Stop with `Ctrl+C`, then `docker compose down`. The SQLite database is kept in a Docker volume, so your data survives restarts.


## Sample data

All data is fake. To generate three sample statements (one per CSV layout):

```
cd backend
python scripts/generatefakestatement.py
```

The files are written to `backend/sampledata/`. Upload any of them in the app to try it out.

## Using the app

1. Open the app and choose a CSV file from `backend/sampledata/`.
2. Click upload. Each row appears with a category, a confidence score and a reason.
3. Open the "Needs Review" tab, pick the right category for each row, and keep "Remember this for similar rows" ticked to save a rule.
4. Check the totals per category at the top.

## Running the tests and linter

```
cd backend
pytest
ruff check .
```

## Project layout

```
backend/    FastAPI app, parsers, categorizer, tests, scripts
frontend/   React + Vite app
compose.yml Docker Compose setup
```
 ## IMPORTANT

 Because i made it so when duplicate files are added (uploading the same file twice), the application identifies the identical hashes and flags the whole file as duplicate, meaning it will force them to the not spending category so double counting can be prevented. This is something i feel like is imperative for an application like this, as it's easy to make huge mistakes due to double counting if someone isn't cautious. To do a complete clean restart, the local.db file needs to be deleted. This can be safely done using these commands in the terminal:
 
 Remove-Item -Recurse -Force local.db


 New-Item local.db -ItemType File

 Then finally, start the application with docker
 docker compose up --build
 NOTE: I had to use my alternate github account as my primary one (Saimhaider26) got suspended, reason unknown but it's looking like it's because of me linking it to fiverr which in turn possibly flagged it as third party bot.

 