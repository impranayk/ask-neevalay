# Leads, analytics & website embed

Two optional add-ons for Ask Neevalay:
1. **Capture leads + log questions** (needs a Supabase database).
2. **Embed the bot on neevalay.com** (a floating widget or a full page).

Both are optional and dark by default — the chat works without either.

---

## 1. Leads & analytics (Supabase)

When configured, Neevu can **capture a parent's callback request** (name, phone,
programme) right inside the chat, and **log what parents ask** so you can see the
top questions and what's going unanswered.

### a. Create the tables

In Supabase → **SQL Editor** → run:

```sql
-- Parent enquiries captured in the chat
create table if not exists leads (
  id          bigint generated always as identity primary key,
  created_at  timestamptz not null default now(),
  name        text,
  phone       text,
  child_age   text,
  programme   text,
  message     text,
  source      text,
  session_id  text
);
alter table leads enable row level security;

-- Question analytics (what parents ask; what we had info for)
create table if not exists chat_logs (
  id          bigint generated always as identity primary key,
  created_at  timestamptz not null default now(),
  question    text,
  answered    boolean,
  top_score   real,
  session_id  text
);
alter table chat_logs enable row level security;
```

RLS is enabled with **no public policies**, so the public/anon key can't read
these — the app writes with the server-side **service_role** key only.

### b. Add the secrets

On <https://share.streamlit.io> → your app → **Settings → Secrets**:

```toml
SUPABASE_URL = "https://YOURPROJECT.supabase.co"
SUPABASE_KEY = "your-service_role-key"     # the secret key, NOT the anon key

# Optional: get a WhatsApp/email alert on every new lead. Point this at a
# Zapier / Make / n8n webhook (or a Supabase Edge Function) that sends the
# message. Leave it out to just store leads in the table.
# LEAD_WEBHOOK_URL = "https://hooks.zapier.com/…"

# Optional: max parent messages per session before Neevu hands off to WhatsApp
# (protects the shared Groq daily quota on a public endpoint). Default 25.
# MAX_MESSAGES_PER_SESSION = "25"
```

> You can **reuse the same Supabase project** as the Neevalay Educator Studio —
> these are just two extra tables. Keep the service_role key in Secrets only.

### c. Where the data shows up

- **Leads:** Supabase → Table editor → `leads`. (Set `LEAD_WEBHOOK_URL` for
  instant alerts.)
- **Top questions / gaps:** `chat_logs`. Look for rows with `answered = false` or
  a low `top_score` — those are questions the site/knowledge base can't answer
  yet. Add those answers to **[data/knowledge.md](data/knowledge.md)** (or the
  website) and rebuild the index.

### d. Free lead delivery → Google Sheet (recommended)

Get every lead into a **Google Sheet** (and optionally an email) — 100% free, no
third-party service. Uses the `LEAD_WEBHOOK_URL` the app already posts to.

1. Create a sheet at <https://sheets.new> — name it e.g. "Neevalay Leads".
2. **Extensions → Apps Script**. Delete the default code and paste
   **[embed/google-sheet-leads.gs](embed/google-sheet-leads.gs)**.
   *(Optional: set `NOTIFY_EMAIL = "you@neevalay.com"` at the top for an email per lead.)*
3. **Deploy → New deployment** → gear ⚙️ → **Web app**.
   - Execute as: **Me**
   - Who has access: **Anyone**  ← required so the bot can post
4. **Deploy** → authorize (it's your own script; "Advanced → Go to project → Allow").
5. Copy the **Web app URL** (ends in `/exec`).
6. Add it to the Streamlit secrets:
   ```toml
   LEAD_WEBHOOK_URL = "https://script.google.com/macros/s/…/exec"
   ```
7. Reboot → submit a test callback → a row appears in the Sheet. Bookmark it and
   **Share** it with your team.

---

## 2. Embed on neevalay.com

The bot supports a `?mini` mode (minimal header) made for embedding.

### Option A — floating "Ask Neevu" bubble (recommended)

Adds a chat bubble to the bottom-right of **every page**.

Paste the contents of **[embed/floating-widget.html](embed/floating-widget.html)**
just before the closing `</body>` tag of your site. In **WordPress**: use a
footer **Custom HTML** widget, or a "footer scripts" plugin, or your theme's
*Footer code* box.

### Option B — a dedicated full page

Host **[embed/fullscreen.html](embed/fullscreen.html)** at, say,
`neevalay.com/ask-neevu.html` and link it from your menu ("Ask Neevu"). It fills
the window with the assistant under your own title + favicon.

Both load `https://ask-neevalay.streamlit.app/?mini` — edit that URL in the file
if your app URL changes.

> **Tip:** keep the app awake so parents never hit a cold start — add the app URL
> to an uptime monitor like [cron-job.org](https://cron-job.org) (every ~5 min,
> "follow redirects" on).
