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
2. Set `SECRET_KEY` as a service variable. It is **required** — with `DEBUG`
   off the app refuses to start rather than fall back to the key committed in
   `settings.py`, which anyone reading the repo could use to forge session
   cookies and password-reset tokens. Generate one with:

   ```bash
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```

   `DEBUG` defaults to off on Railway, so it does not need to be set (setting
   `DEBUG=True` there will expose tracebacks and settings to visitors).
   `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` do not need to be set either —
   the app matches Railway's `*.up.railway.app` domain space, since Railway
   generates the service's public domain without publishing it as a variable.
   Set `ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS` explicitly if you attach a
   custom domain.
3. Deploy. The build runs `collectstatic`, and the start command runs `migrate`
   before handing off to gunicorn, which serves static files through WhiteNoise.
4. Create the admin account. Railway has no convenient interactive shell, so
   set these variables and the `accounts.0002_admin_from_env` migration creates
   the account during the deploy's `migrate` step:

   ```
   ADMIN_PHONE=0783108892
   ADMIN_PASSWORD=<a strong password>
   ADMIN_FULL_NAME=Valley Admin
   ```

   The migration is skipped entirely unless both `ADMIN_PHONE` and
   `ADMIN_PASSWORD` are set, and it never touches an account that already
   exists — changing `ADMIN_PASSWORD` afterwards does **not** reset the
   password, so change it from the admin UI instead. Once the account exists
   you can delete all three variables.

   Where you do have a shell, the equivalent one-off is:

   ```bash
   python manage.py create_admin 0783108892 <password> --full-name "Valley Admin"
   ```

5. Set the Cloudflare R2 variables so payment screenshots survive a redeploy
   (see below). Without them, uploads go to local disk, which on Railway is
   erased on every deploy — taking the proof behind every approved investment
   with it.

## Payment screenshot storage (Cloudflare R2)

Payment proofs are the only user uploads, and they are the evidence behind
every approved investment, so they are stored in Cloudflare R2 rather than on
the container's disk. Set these variables to turn it on:

```
R2_BUCKET_NAME=<bucket>
R2_ACCESS_KEY_ID=<key id>
R2_SECRET_ACCESS_KEY=<secret>
R2_ACCOUNT_ID=<cloudflare account id>     # or set R2_ENDPOINT directly
R2_ENDPOINT=https://<account id>.r2.cloudflarestorage.com
R2_REGION=auto
```

`R2_ENDPOINT` is derived from `R2_ACCOUNT_ID` when it isn't set explicitly.
Leave all of them unset to store uploads on the local disk, which is what
local development and the test suite use. Setting only some of them is a
startup error: uploads would otherwise land on a disk the host wipes on every
redeploy, losing the proof behind an approved investment.

The bucket stays **private**: image URLs are short-lived pre-signed links
(1 hour), because a proof screenshot shows a real person's payment details.
Uploads never overwrite an existing key, and no ACL is sent (R2 rejects
uploads that carry one). Checksum calculation is pinned to `when_required`:
boto3 1.36 and later otherwise send every upload as a chunked body with a
trailing CRC32 checksum, which R2 does not implement, and each upload fails.

To check a deployment end to end — upload, read back, signed URL, delete —
run this on the host itself:

```
python manage.py check_r2
```

It prints the bucket and endpoint in use and reports the storage backend's
own error when the round trip fails.

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
