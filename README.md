# Ask Neevalay 🌱

**A warm, parent-facing AI assistant for [Neevalay Tots](https://neevalay.com)** —
"Nurturing Roots, Shaping the Future."

*Neevu*, the assistant, answers parents' questions about our programmes, learning
approach, admissions, timings and daily care — **only** from the school's own
information — and gently helps families **book a visit**. It never invents fees or
policies; when it doesn't know, it connects the parent to our team.

Built with free, open-source tools (no license fees): **Streamlit** UI +
**Groq** (open Llama models) for generation + on-device **fastembed** retrieval
over a curated knowledge base.

---

## How it works

```
Parent question
   ↓  embed (fastembed, on CPU)
   ↓  cosine search over data/knowledge.npz   ← crawled from neevalay.com
   ↓  grounded context (with page URLs) + safety system prompt
   ↓  Groq (Llama 3.3 70B)  →  warm, streamed answer + links to the source page
```

- **Grounded in your website + a curated supplement:** `ingest/build_index.py`
  crawls every content page on **neevalay.com**, strips nav/footer boilerplate, and
  embeds the real text — **plus** the curated answers in
  [`data/knowledge.md`](data/knowledge.md) (timings, fee policy, safety, admission
  steps the site may not spell out). The bot answers only from that content and
  links to the relevant page; for anything it doesn't cover it invites contact.
- **Lead capture:** contextual **Book a visit / WhatsApp / Call / Admission-form**
  buttons on high-intent answers, plus an in-chat **"Request a callback"** form
  (name + phone + programme) that stores the enquiry — see
  [EMBED_AND_DB.md](EMBED_AND_DB.md).
- **Analytics:** every question is logged (anonymised) so you can see the top
  questions and what's going unanswered, and fill those gaps.
- **Safe & fair:** no medical/emergency advice; no storing a child's personal
  data; a per-session message cap protects the shared Groq quota on the public URL.
- **On brand:** Soft Aqua / Warm Gold / Clay Terracotta on Off-White, Nunito.

## Keeping the bot's knowledge current

The bot's knowledge **is** your website. To refresh it after you update the site:

```bash
python ingest/build_index.py     # re-crawls neevalay.com and rebuilds the index
```

Then commit the updated `data/knowledge.npz` + `data/chunks.json`. This also runs
**automatically every night** via GitHub Actions (`.github/workflows/refresh-index.yml`),
so site changes flow into the bot without any manual step.

## Run locally

```bash
python -m venv .venv && .venv\Scripts\activate      # (source .venv/bin/activate on macOS/Linux)
pip install -r requirements.txt
copy .env.example .env                               # then paste your GROQ_API_KEY
python ingest/build_index.py                          # build the knowledge index
streamlit run streamlit_app.py
```

Get a free Groq key at <https://console.groq.com/keys>.

## Deploy (Streamlit Community Cloud)

1. Push this repo to GitHub.
2. On <https://share.streamlit.io>, point at `streamlit_app.py`.
3. In **Settings → Secrets**, add `GROQ_API_KEY = "…"`. *(Optional)* add the
   Supabase secrets to turn on **leads + analytics** — see [EMBED_AND_DB.md](EMBED_AND_DB.md).
4. **Embed on neevalay.com** — paste [`embed/floating-widget.html`](embed/floating-widget.html)
   before `</body>` for a floating bubble, or host [`embed/fullscreen.html`](embed/fullscreen.html)
   as a dedicated page. Full guide in [EMBED_AND_DB.md](EMBED_AND_DB.md).

Live: <https://ask-neevalay.streamlit.app>

## Keeping it awake

Streamlit's free tier sleeps an app after inactivity, so an external uptime
monitor keeps it warm (no cold "wake-up" for parents):

- **[cron-job.org](https://cron-job.org)** pings the app URL every 5 minutes.
  (Enable "follow redirects / treat redirects as success" so Streamlit's `303`
  session handshake counts as a success.)

---

_Ask Neevalay is the public assistant. A separate, authenticated **Neevalay
Educator Studio** (for teachers/staff: lesson plans, curriculum, observations)
lives in its own repository._
