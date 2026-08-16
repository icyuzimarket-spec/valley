# Valley Investment

Django-based investment platform. Users register with a phone number, invest in
one of 13 fixed plans (12%/day for 50 days), pay externally and upload proof,
and an admin approves/rejects. Approved investments accrue daily income + a
one-time welcome bonus; referrals earn an 8% commission on a friend's first
approved investment. Withdrawals run Mon-Sat, 06:30-23:30, with a 24h cooldown
between requests.

## Setup (Windows / PowerShell)

```powershell
cd valley
python -m venv venv
venv\Scripts\pip install -r requirements.txt
copy .env.example .env   # then edit SECRET_KEY for anything beyond local dev
venv\Scripts\python manage.py migrate
venv\Scripts\python manage.py create_admin 0783108892 <password> --full-name "Valley Admin"
venv\Scripts\python manage.py runserver
```

Then visit http://127.0.0.1:8000/, and http://127.0.0.1:8000/admin/ to sign in
as the admin and configure **Site Settings** (WhatsApp number/group, Telegram
group, payee name/payment code, and confirm the default referral fallback is
set to your admin account).

The 13 investment plans are seeded automatically by the
`investments/migrations/0002_seed_plans.py` data migration — no manual setup
needed.

## Daily earnings

Dashboard visits self-heal daily income (any missed days are caught up
automatically, capped at 50 days per investment) — there is no background
worker required to launch. For exact daily timing you can optionally wire the
idempotent management command to Windows Task Scheduler:

```powershell
schtasks /create /tn "ValleyDailyCredit" /tr "C:\path\to\valley\venv\Scripts\python.exe C:\path\to\valley\manage.py credit_daily_earnings" /sc daily /st 00:05
```

## Deploying to PythonAnywhere

See the bash command guide provided separately, or in short: clone the repo
into a PythonAnywhere Bash console, create a virtualenv, `pip install -r
requirements.txt`, create a `.env` from `.env.example` (set `DEBUG=False`,
`ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS` to your `*.pythonanywhere.com` domain),
run `migrate` + `collectstatic`, then wire up the Web tab (source code path,
virtualenv path, WSGI file, and static/media URL mappings) and reload.

## Deploying to Railway

The repo ships a `railway.json` (and an equivalent `Procfile`), so Railway
builds and starts the app without any command typed into the dashboard — leave
the service's **Build Command** and **Start Command** fields empty, otherwise
they override the config file.

1. Add a **Postgres** database to the project. Railway injects `DATABASE_URL`
   into the service, and the app picks it up automatically. This is not
   optional: Railway's filesystem is ephemeral, so a SQLite file is wiped on
   every deploy along with all users and investments.
2. Set the service variables:

   ```
   SECRET_KEY=<a long random string>
   DEBUG=False
   ```

   `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` do not need to be set — the app
   adds Railway's generated domain (`RAILWAY_PUBLIC_DOMAIN`) to both. Set them
   anyway if you attach a custom domain.
3. Deploy. The build runs `collectstatic`, and the start command runs `migrate`
   before handing off to gunicorn, which serves static files through WhiteNoise.
4. Create the admin account once, from the service's shell (`railway run`, or
   the dashboard's terminal):

   ```bash
   python manage.py create_admin 0783108892 <password> --full-name "Valley Admin"
   ```

Note that uploaded payment screenshots go to `MEDIA_ROOT` on local disk, which
is also ephemeral — attach a Railway volume mounted at `/app/media` (or move to
object storage) so proofs survive a redeploy.

## Running tests

```powershell
venv\Scripts\python manage.py test
```

## Key business rules implemented

- Signup referral code is optional; invalid/blank codes attribute the new
  user to the admin configured as `SiteSettings.fallback_referrer`. Referral
  commission (8%) only pays out for genuine referral codes, not the fallback.
- Welcome bonus (1000 RWF) pays once, on a user's first approved investment.
- All balance-affecting admin actions (approve/reject investment or
  withdrawal) go through `investments/services.py` and `wallet/services.py`
  — the Django admin change forms are read-only for money fields, and only
  the bulk actions (which call these services) can approve/reject, so bonuses
  and commissions can never be bypassed by a raw field edit.
- `Admin Control` in the navbar links straight to `/admin/` for full raw
  Django admin access; `User Management` in the navbar is the day-to-day
  approve/reject workflow with screenshot previews.
