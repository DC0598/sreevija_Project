# Sreevija Vastara

Django storefront with server-rendered templates, Django authentication, and a
PostgreSQL database. Local development uses SQLite unless `DATABASE_URL` is set.
Product images uploaded in the staff area are stored as bytes in the database.

## Run locally

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
# Set SECRET_KEY, ADMIN_EMAIL and ADMIN_PASSWORD in .env.
.venv/bin/python manage.py migrate
.venv/bin/python manage.py seed_store
.venv/bin/python manage.py create_initial_admin
.venv/bin/python manage.py runserver
```

Open http://127.0.0.1:8000. Product browsing, search, filters, cart, checkout,
customer accounts, wishlist, order history, and the staff dashboard are Django
templates. The dashboard is at `/manage/`.

## Deploy to Vercel with Neon

1. In the existing Vercel project, keep the root directory at the repository
   root. Vercel detects Django from `manage.py`.
2. Set `DATABASE_URL` to the Neon pooled PostgreSQL connection string,
   `SECRET_KEY` to a new random secret, `ADMIN_EMAIL` to the admin email, and
   `ADMIN_PASSWORD` to a strong admin password. Set them for each environment
   that should have a deployment.
3. Push the code and deploy. Vercel runs `build.py`, which applies Django
   migrations, imports the previous app's product catalog and image bytes if
   present, seeds products if the catalog is empty, and creates the initial
   staff account if one does not already exist. It also collects static assets
   into `public/static` so Vercel serves them from its CDN.
   If you use a custom domain, also add it to the `ALLOWED_HOSTS` environment
   variable (comma-separated).

Uploaded JPG, PNG, and WEBP images are stored in the `shop_productimage` table
and served from `/uploads/<filename>`, so uploads persist between serverless
calls. The existing Neon tables from the previous app are left untouched; the
Django app uses its own tables. Legacy products and any referenced uploaded
images are imported into the Django catalog on the first deploy. Existing
customer accounts and orders are not imported.

Orders are recorded with payment status `Pending`. No online payment gateway is
connected; staff can update order/payment status from `/manage/`.
