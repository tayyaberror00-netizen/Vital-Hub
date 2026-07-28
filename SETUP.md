# Vital Hub — Local Setup (VS Code)

## 1. Get a free Gemini API key
Go to https://aistudio.google.com/apikey → Create API key → copy it.
(Do this even if you had old keys before — those were exposed in your frontend
files and should be treated as compromised. Delete them from AI Studio.)

## 2. Open the project
Open the `backend/` folder in VS Code (File → Open Folder).

## 3. Create a virtual environment
Open a terminal in VS Code (`` Ctrl+` ``) and run:

```bash
python -m venv venv
```

Activate it:
- Windows: `venv\Scripts\activate`
- Mac/Linux: `source venv/bin/activate`

You should see `(venv)` at the start of your terminal prompt.

## 4. Install dependencies
```bash
pip install -r requirements.txt
```

## 5. Create your `.env` file
Copy `.env.example` to `.env` in the same `backend/` folder, then edit it:

```bash
cp .env.example .env        # Mac/Linux
copy .env.example .env      # Windows
```

Open `.env` and set:
- `SECRET_KEY` — any long random string
- `JWT_SECRET` — a different long random string
- `GEMINI_API_KEY` — the key from step 1

## 6. Set up the database
```bash
python manage.py migrate
```

## 7. Load the product catalog
```bash
python manage.py seed_products
```

## 8. Create an admin account (for the /admin/ dashboard)
```bash
python manage.py create_admin --email you@example.com --password YourPassword123 --name "Your Name"
```

## 9. Run the server
```bash
python manage.py runserver
```

Open http://127.0.0.1:8000/ in your browser.

- Log in with the admin email/password from step 8 to reach the dashboard at
  http://127.0.0.1:8000/admin/
- Any other email/password combo you sign up with through the site is a
  normal customer account.

## What to test first
- **index.html** → click the floating AI Hub button, ask it something — should
  get a real Gemini response, not a canned reply.
- **nutrition.html** → fill the form, generate a plan, then generate a grocery list.
- **report-analyzer.html** → upload any image or PDF, click Analyze.
- **xray.html** → upload an image, run the scan.
- **consultation.html** → chat in the AI panel.
- **store.html → product-detail.html → checkout.html** → full purchase flow,
  ends on thank-you.html with a real order number.
- **appointment.html** → book a specialist, confirm it appears under
  `/admin/appointments/` when logged in as admin.

## If something breaks
- 500 error on any `/api/ai/...` call → check `GEMINI_API_KEY` is set in `.env`
  and the server was restarted after editing `.env`.
- Login redirects back to auth.html → check `JWT_SECRET`/`SECRET_KEY` are set.
- Empty store page → run `python manage.py seed_products` again.
