# Deployment Guide (TradeFlow)

## 1) Prepare Environment Variables
Use `.env.example` as template and set production values:

- `DJANGO_DEBUG=False` (or `DEBUG=False`)
- `SECRET_KEY=<long-random-secret>`
- `ALLOWED_HOSTS=<your-domain>,<platform-domain>`
- `CSRF_TRUSTED_ORIGINS=https://<your-domain>,https://<platform-domain>`
- `DATABASE_URL=...` (or `DB_*` variables)

If using Gmail SMTP, set:
- `EMAIL_HOST_USER`
- `EMAIL_HOST_PASSWORD` (Gmail App Password)

## 2) Install Dependencies
Use your platform's Python environment and install project deps.

## 3) Run Migrations and Collect Static
```bash
python manage.py migrate
python manage.py collectstatic --noinput
```

## 4) Create Admin User (first deploy only)
```bash
python manage.py createsuperuser
```

## 5) Start the App
Use a production WSGI server (for example gunicorn):
```bash
gunicorn brokerage_platform.wsgi:application --bind 0.0.0.0:$PORT
```

## 6) Verify Health
```bash
python manage.py check --deploy
```
Expected: no major security warnings.

## 7) Staff Wallet Dashboard
After login with a staff/superuser account:
- Open `/admin-dashboard/wallets/`
- Edit user cash + crypto balances (`BTC`, `ETH`, `BNB`, `SOL`)
- Save changes; values immediately reflect in user wallet/account pages.
