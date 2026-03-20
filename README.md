# 🧬 PubMed Research Bot

A biomedical chatbot that searches PubMed in real time and synthesises the findings using Claude (Anthropic).

**Stack:** Python · Gradio · Anthropic API · PubMed E-utilities (free, no key needed)

---

## How it works

1. User asks a biomedical question
2. App queries the **PubMed E-utilities API** (free, no API key needed) for the top 6 relevant papers
3. Abstracts are passed to **Claude** with a synthesis prompt
4. Claude returns a cited answer + key takeaways
5. Source articles with PubMed links are shown below the answer

---

## Project structure

```
pubmed_bot/
├── app.py            # Main Gradio app
├── requirements.txt  # Python dependencies
├── render.yaml       # Render deploy config
├── .gitignore
└── README.md
```

---

## Local development

```bash
# 1. Clone / enter the folder
cd pubmed_bot

# 2. Create a virtual environment
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set your Anthropic API key
export ANTHROPIC_API_KEY="sk-ant-..."   # Windows: set ANTHROPIC_API_KEY=sk-ant-...

# 5. Run
python app.py
# Open http://localhost:7860
```

---

## Deploy to Render (free tier works)

### Step 1 — Push to GitHub

```bash
git init
git add .
git commit -m "initial commit"
# Create a new repo on github.com, then:
git remote add origin https://github.com/YOUR_USERNAME/pubmed-bot.git
git push -u origin main
```

### Step 2 — Create a Render Web Service

1. Go to [render.com](https://render.com) → **New → Web Service**
2. Connect your GitHub account and select the `pubmed-bot` repo
3. Render will auto-detect `render.yaml` — click **Apply**
4. Under **Environment Variables**, add:
   - Key: `ANTHROPIC_API_KEY`
   - Value: your key from [console.anthropic.com](https://console.anthropic.com)
5. Click **Deploy** — done! Render gives you a public `https://pubmed-bot.onrender.com` URL

### Step 3 — (Optional) Keep it awake on free tier

Render's free tier spins down after 15 min of inactivity. To avoid cold starts, use a free uptime monitor like [cron-job.org](https://cron-job.org) to ping your URL every 10 minutes.

---

## Deploy to Railway (alternative)

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login & deploy
railway login
railway init        # choose "Empty Project"
railway up

# Set env var in Railway dashboard or CLI:
railway variables set ANTHROPIC_API_KEY=sk-ant-...
```

Railway auto-detects `requirements.txt` and runs `python app.py`.

---

## Customisation ideas

| Idea | Where to change |
|---|---|
| Number of papers fetched | `max_results` in `search_pubmed()` |
| Claude model | `model=` in `synthesise()` |
| Answer length | `max_tokens` + system prompt |
| UI title / colours | `gr.Blocks(css=...)` section |
| Add date filter | PubMed `datetype=pdat&mindate=` param |

---

## API keys

| Service | Key needed? | Where to get it |
|---|---|---|
| Anthropic (Claude) | ✅ Yes | [console.anthropic.com](https://console.anthropic.com) |
| PubMed E-utilities | ❌ No | Free, no signup |

---

## License

MIT
