# Sreevija Vastara

Flask + SQLite backend that also serves the storefront in `public/`.

## Run
```
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
ADMIN_EMAIL=you@example.com ADMIN_PASSWORD='choose-a-password' .venv/bin/python server.py
```
Open http://127.0.0.1:5050. If `ADMIN_PASSWORD` is unset, a random admin password is printed once on first start.
Env: `PORT`, `DB_PATH`.

## API
- Auth: `POST /api/auth/register|login|logout`, `GET /api/auth/me` (Bearer token)
- Shop: `GET /api/products[/id]`, `GET /api/pincode/<pin>`, `POST /api/orders` (guest or logged in; prices/stock checked server-side), `GET /api/orders`
- Admin: `GET /api/admin/stats|products|orders`, `POST|PUT|DELETE /api/admin/products[/id]`, `POST /api/admin/upload`, `PATCH /api/admin/orders/<id>`
- Admin UI: `/#/admin`

Online payment gateway (e.g. Razorpay) is not integrated; orders are stored with payment status `Pending` and the admin can mark them paid.
