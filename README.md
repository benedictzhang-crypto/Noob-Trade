# Stock Pattern Analysis Dashboard

This project is split into two simple parts:

- `frontend/`: Vue 3 + Vite
- `backend/`: Flask

The goal is to give you a clean beginner-friendly starting point for a stock pattern analysis dashboard without connecting to real APIs yet.

## Email Setup For Other Users

If you want other people to download the app and successfully:

- register accounts
- verify email addresses
- reset passwords
- receive login alerts

then the backend must be connected to a real outbound mail provider.

Use [backend/.env.example](/Users/benedict/Desktop/NoobTrade/backend/.env.example) as your template and configure:

- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `EMAIL_FROM`
- `APP_BASE_URL`

Recommended mode split:

- local development: `APP_ENV=development` and `ALLOW_LOCAL_EMAIL_BYPASS=true`
- shared or distributed app: `APP_ENV=production` and `ALLOW_LOCAL_EMAIL_BYPASS=false`

In production mode, Noob Trade will now refuse to silently bypass email delivery. That prevents shipping a build that only works on the developer's machine.

## Project Structure

```text
project-root/
  frontend/
  backend/
  README.md
```

## Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The frontend will usually run at `http://localhost:5173`.

## Backend Setup

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

The backend will run at `http://localhost:5000`.

## Local PostgreSQL Path

If you want to move beyond local SQLite without changing the quant logic, use PostgreSQL locally.

1. install PostgreSQL on your machine
2. create a database named `noobtrade`
3. set:

```bash
export DATABASE_URL="postgresql+psycopg://localhost/noobtrade"
```

4. sync the current SQLite seed into PostgreSQL:

```bash
cd backend
python scripts/sync_sqlite_to_postgres.py
```

Current note:

- the tracked local seed currently contains the top 50 symbol universe in `symbols`
- if more `daily_prices`, `daily_indicators`, or `pattern_windows` are added to SQLite later, the same sync script will carry them into PostgreSQL

## Incremental Data Updates

Once the initial symbol universe is in place, you do not need to rebuild the full database every month.

Use the incremental sync script to pull only a recent rolling history window, then upsert the latest prices, indicators, and pattern windows into the configured database:

```bash
cd backend
python scripts/incremental_sync_cache.py --symbols AAPL,NVDA,MSFT,AMZN,GOOGL,GOOG,META,AVGO,TSLA,BRK.B --history-limit 1400
```

What this does:

- fetches a recent rolling history window instead of the full 10-year history
- upserts new rows instead of replacing the whole database
- rebuilds indicators and pattern windows only from the recent window
- lets future collaborators continue 11-50 using the same workflow

Recommended workflow:

1. initial load for the top 50 universe
2. monthly or weekly incremental sync using `incremental_sync_cache.py`
3. keep the app code stable while only updating the data layer

## Full Local Cache Build

The tracked SQLite seed keeps `daily_prices` at roughly 10-year depth, but the
repo does not ship a huge fully expanded cache DB in git.

To build the full local daily cache from the seeded prices on your own machine:

```bash
python backend/scripts/build_full_daily_cache.py
```

That script:

- reuses the existing `backend/noobtrade_local.db`
- expands `daily_indicators` to the same daily coverage as `daily_prices`
- expands `pattern_windows` for `timeframe=daily` and `window_size=30`
- is safe to rerun and skips symbols that already look complete
- prints final row counts and runs `PRAGMA integrity_check`

For smaller resumable runs:

```bash
python backend/scripts/build_full_daily_cache.py --symbols AAPL,NVDA
python backend/scripts/build_full_daily_cache.py --force
```

## Notes

- The frontend currently shows a simple dashboard layout.
- The backend currently returns a placeholder JSON message.
- No real stock data APIs are connected yet.

## Temporary Share Link

If you want a temporary public link without buying a domain, deploying, or pushing to GitHub, you can use the built-in share scripts in this project.

From the project root:

```bash
chmod +x scripts/start_share.sh scripts/stop_share.sh start-share.command stop-share.command
./scripts/start_share.sh
```

Or on macOS, you can double-click:

- `start-share.command`
- `stop-share.command`

What this does:

- builds the Vue frontend
- starts the Flask server locally
- opens a temporary public tunnel through `localhost.run`
- prints a shareable HTTPS link

Important:

- the link is temporary and changes each time you restart the share script
- your computer must stay on and connected to the internet
- file updates are easy: edit code, then run the start script again to rebuild and refresh the shared link

## Desktop Launcher

This project now includes a cross-platform desktop launcher in [launcher/](/Users/samuel/Documents/stock_pattern_project/launcher).

What it does:

- automatically syncs the GitHub repository
- automatically installs backend dependencies into an isolated runtime
- automatically installs frontend dependencies and builds the Vue app
- automatically starts Flask
- automatically opens a temporary `localhost.run` HTTPS share link
- shows the link in a GUI and lets the user copy it
- includes `Start`, `One-click Update`, `Stop Service`, and `Regenerate Link` buttons

### Build the macOS app

```bash
cd /Users/samuel/Documents/stock_pattern_project
chmod +x build_mac.sh
./build_mac.sh
```

Output:

- `dist/NoobTrade.app`

### Build the Windows app

Run this from Windows:

```bat
build_windows.bat
```

Output:

- `dist\NoobTrade\NoobTrade.exe`

### Launcher requirements

The launcher checks for these system tools:

- `git`
- `python3` or `python`
- `npm`
- `ssh`

If any are missing, the GUI shows a readable error instead of failing silently.

### Open the launcher directly on macOS

From the project root:

```bash
chmod +x start-launcher.command
```

Then you can double-click:

- `start-launcher.command`

It will:

1. detect `python3` or `python`
2. install launcher dependencies if needed
3. open the Noob Trade launcher GUI

### Double-click runtime flow

When the desktop app is opened, it will:

1. locate or clone the Noob Trade project
2. pull the latest code from GitHub
3. create/update the backend runtime
4. install backend requirements
5. install frontend dependencies
6. build the frontend
7. start Flask
8. open a `localhost.run` HTTPS tunnel
9. display the public share link in the GUI

## iOS App Shell

This project now also includes a Capacitor-based iOS shell path so the Noob Trade product can move from a mobile website to a real App Store submission workflow.

Key files:

- [package.json](/Users/samuel/Documents/stock_pattern_project/package.json)
- [capacitor.config.ts](/Users/samuel/Documents/stock_pattern_project/capacitor.config.ts)
- [APP_STORE_RELEASE.md](/Users/samuel/Documents/stock_pattern_project/APP_STORE_RELEASE.md)
- [build_ios_release.sh](/Users/samuel/Documents/stock_pattern_project/scripts/mobile/build_ios_release.sh)

### Prepare the iOS shell

```bash
cd /Users/samuel/Documents/stock_pattern_project
npm install
npm run mobile:prepare:ios
```

### Open the project in Xcode

```bash
cd /Users/samuel/Documents/stock_pattern_project
npm run mobile:open:ios
```

### What still requires Apple tooling

- Apple Developer account
- Signing certificates and provisioning
- Xcode archive upload
- App Store Connect listing details

Use [APP_STORE_RELEASE.md](/Users/samuel/Documents/stock_pattern_project/APP_STORE_RELEASE.md) as the release checklist.

## Web Clip / Installable App Mode

The project now also works as an installable web app.

What that means:

- iPhone / iPad: open in Safari and use `Add to Home Screen`
- Windows: open in Edge or Chrome and choose `Install app`
- macOS: open in Safari or Chrome and add/install it as an app window

The frontend now includes:

- a web app manifest
- a service worker
- installable app icons
- an in-product `Install App` button

So for classroom demos, you can use the web version like an app now, and keep the Capacitor iOS path for later App Store submission.
