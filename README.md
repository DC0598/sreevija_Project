# Sreevija Vastara

Flask storefront and API. Local development uses SQLite; setting `DATABASE_URL`
uses PostgreSQL (Neon is supported) and stores uploaded product images in the
database, so they persist across Vercel serverless invocations.

## Run
```
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
ADMIN_EMAIL=you@example.com ADMIN_PASSWORD='choose-a-password' .venv/bin/python server.py
```
Open http://127.0.0.1:5050. If `ADMIN_PASSWORD` is unset, a random admin password is printed once on first start.
Env: `PORT`, `DB_PATH`.

## Deploy to Vercel with Neon

1. Create a Neon project and copy its PostgreSQL connection string. Use the
   pooled connection string and ensure it includes `sslmode=require`.
2. Import this GitHub repository as a Vercel project. Keep the project root at
   the repository root. Vercel detects the Flask app in `server.py` and serves
   the storefront assets in `public/`.
3. Add these Vercel environment variables for the environments you will deploy:
   - `DATABASE_URL`: the Neon connection string
   - `ADMIN_EMAIL`: the initial administrator's email
   - `ADMIN_PASSWORD`: a strong password for the initial administrator
4. Deploy. The app creates its tables and starter products in Neon on startup.
   The initial admin account is created only if Neon has no admin user.

Admin-uploaded JPG, PNG, and WEBP files are stored in the `media` table as
PostgreSQL `BYTEA` data and served back from `/uploads/<filename>`. No local
filesystem storage is used for uploads on Vercel. Existing data in a local
`shop.db` is not copied to Neon automatically.

## API
- Auth: `POST /api/auth/register|login|logout`, `GET /api/auth/me` (Bearer token)
- Shop: `GET /api/products[/id]`, `GET /api/pincode/<pin>`, `POST /api/orders` (guest or logged in; prices/stock checked server-side), `GET /api/orders`
- Admin: `GET /api/admin/stats|products|orders`, `POST|PUT|DELETE /api/admin/products[/id]`, `POST /api/admin/upload`, `PATCH /api/admin/orders/<id>`
- Admin UI: `/#/admin`

Online payment gateway (e.g. Razorpay) is not integrated; orders are stored with payment status `Pending` and the admin can mark them paid.
