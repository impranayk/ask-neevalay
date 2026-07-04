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
   ↓  cosine search over data/knowledge.npz   ← built from data/knowledge.md
   ↓  grounded context + safety system prompt
   ↓  Groq (Llama 3.3 70B)  →  warm, streamed answer
```

- **Grounded & safe:** answers only from `data/knowledge.md`; no medical/emergency
  advice; no storing a child's personal data; graceful hand-off to WhatsApp/phone.
- **Lead capture:** a persistent **Book a visit / Call us** bar.
- **On brand:** Soft Aqua / Warm Gold / Clay Terracotta on Off-White, Quicksand +
  Nunito Sans, and the Neevu sprout mark.

## Editing what the bot knows

1. Edit **`data/knowledge.md`** (plain markdown; `##` headings become topics).
   Fill every `[TO CONFIRM]` note (fees, address, safety specifics, admissions).
2. Rebuild the index:
   ```bash
   python ingest/build_index.py
   ```
3. Commit the updated `data/knowledge.npz` + `data/chunks.json`.

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
3. In **Settings → Secrets**, add `GROQ_API_KEY = "…"`.
4. Embed on neevalay.com as a floating widget or a masked full-screen page.

---

_Ask Neevalay is the public assistant. A separate, authenticated **Neevalay
Educator Studio** (for teachers/staff: lesson plans, curriculum, observations)
lives in its own repository._
