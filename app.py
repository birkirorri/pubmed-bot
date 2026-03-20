import os
import re
import requests
import xml.etree.ElementTree as ET
import anthropic
import gradio as gr

# ── Anthropic client ───────────────────────────────────────────────────────────
client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

# ── PubMed helpers ─────────────────────────────────────────────────────────────
ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH  = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
ESUM    = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"


def search_pubmed(query: str, max_results: int = 6) -> list[str]:
    """Return a list of PubMed IDs for the query."""
    params = {
        "db": "pubmed",
        "term": query,
        "retmax": max_results,
        "sort": "relevance",
        "retmode": "json",
    }
    r = requests.get(ESEARCH, params=params, timeout=15)
    r.raise_for_status()
    return r.json().get("esearchresult", {}).get("idlist", [])


def fetch_abstracts(pmids: list[str]) -> list[dict]:
    """Fetch title + abstract for each PMID."""
    if not pmids:
        return []

    # summaries (journal, date, authors)
    sum_params = {"db": "pubmed", "id": ",".join(pmids), "retmode": "json"}
    sum_r = requests.get(ESUM, params=sum_params, timeout=15)
    sum_r.raise_for_status()
    summaries = sum_r.json().get("result", {})

    # full abstracts via XML
    abs_params = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "rettype": "abstract",
        "retmode": "xml",
    }
    abs_r = requests.get(EFETCH, params=abs_params, timeout=15)
    abs_r.raise_for_status()
    root = ET.fromstring(abs_r.text)

    abstract_map = {}
    for article in root.findall(".//PubmedArticle"):
        pmid_el = article.find(".//PMID")
        abs_el  = article.find(".//AbstractText")
        if pmid_el is not None:
            abstract_map[pmid_el.text] = abs_el.text if abs_el is not None else ""

    articles = []
    for pmid in pmids:
        s = summaries.get(pmid, {})
        authors = ", ".join(
            a.get("name", "") for a in (s.get("authors") or [])[:3]
        )
        articles.append(
            {
                "pmid": pmid,
                "title": s.get("title", "No title"),
                "authors": authors,
                "source": s.get("source", ""),
                "pubdate": s.get("pubdate", ""),
                "abstract": abstract_map.get(pmid, ""),
            }
        )
    return articles


# ── Claude synthesis ───────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are a biomedical research assistant with deep expertise in reading and synthesising scientific literature.

You will receive a user question and a numbered list of PubMed abstracts.
Your task:
1. Write a clear, concise answer to the question based on the evidence in the abstracts.
2. Cite papers inline using their number, e.g. [1], [2].
3. End with a short "Key takeaways" section (3–5 bullet points).
4. Be scientifically accurate but accessible to a graduate-level reader.
5. If the evidence is insufficient or contradictory, say so explicitly.
Keep your total response under 600 words."""


def synthesise(question: str, articles: list[dict]) -> str:
    article_block = "\n\n---\n\n".join(
        f"[{i+1}] PMID:{a['pmid']}\n"
        f"Title: {a['title']}\n"
        f"Authors: {a['authors']}\n"
        f"Journal: {a['source']} ({a['pubdate']})\n"
        f"Abstract: {a['abstract'] or 'Not available'}"
        for i, a in enumerate(articles)
    )
    user_msg = f"Question: {question}\n\nRelevant PubMed abstracts:\n\n{article_block}"

    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
    )
    return message.content[0].text


# ── Format output for Gradio ───────────────────────────────────────────────────
def format_articles(articles: list[dict]) -> str:
    if not articles:
        return "_No articles found._"
    lines = []
    for i, a in enumerate(articles):
        lines.append(
            f"**[{i+1}] {a['title']}**  \n"
            f"_{a['authors']} — {a['source']} ({a['pubdate']})_  \n"
            f"🔗 [PubMed](https://pubmed.ncbi.nlm.nih.gov/{a['pmid']}/)"
        )
    return "\n\n---\n\n".join(lines)


# ── Main bot function ──────────────────────────────────────────────────────────
def pubmed_bot(question: str, history: list):
    if not question.strip():
        yield history, "", "Please enter a question."
        return

    # Step 1 — search
    yield history, "", "🔍 Searching PubMed…"
    try:
        pmids = search_pubmed(question)
    except Exception as e:
        yield history, "", f"❌ PubMed search error: {e}"
        return

    if not pmids:
        yield history, "", "⚠️ No PubMed articles found for that query. Try rephrasing."
        return

    # Step 2 — fetch abstracts
    yield history, "", f"📄 Fetching {len(pmids)} abstracts…"
    try:
        articles = fetch_abstracts(pmids)
    except Exception as e:
        yield history, "", f"❌ Abstract fetch error: {e}"
        return

    article_md = format_articles(articles)

    # Step 3 — synthesise
    yield history, "", "🤖 Synthesising with Claude…"
    try:
        answer = synthesise(question, articles)
    except Exception as e:
        yield history, "", f"❌ Claude API error: {e}"
        return

    # Build final chat history entry
    full_reply = f"{answer}\n\n---\n### 📚 Source Articles\n\n{article_md}"
    history = history + [[question, full_reply]]
    yield history, "", ""


# ── Gradio UI ──────────────────────────────────────────────────────────────────
CSS = """
#chatbot { font-size: 14px; }
#title { text-align: center; margin-bottom: 4px; }
#subtitle { text-align: center; color: #888; margin-bottom: 16px; }
"""

with gr.Blocks(css=CSS, title="PubMed Research Bot") as demo:
    gr.Markdown("# 🧬 PubMed Research Bot", elem_id="title")
    gr.Markdown(
        "Ask any biomedical question — I'll search PubMed for recent papers "
        "and synthesise the findings using Claude.",
        elem_id="subtitle",
    )

    chatbot = gr.Chatbot(elem_id="chatbot", height=520, bubble_full_width=False)
    status  = gr.Markdown("")

    with gr.Row():
        question_box = gr.Textbox(
            placeholder="e.g. What is the role of gut microbiome in depression?",
            label="Your question",
            scale=5,
        )
        send_btn = gr.Button("Send 🚀", variant="primary", scale=1)

    gr.Examples(
        examples=[
            "What are the latest findings on CRISPR off-target effects?",
            "How does gut microbiome affect mental health?",
            "What is known about mRNA vaccine long-term immunogenicity?",
            "What are novel treatments for glioblastoma in 2024?",
        ],
        inputs=question_box,
    )

    state = gr.State([])

    def on_submit(q, hist):
        yield from pubmed_bot(q, hist)

    send_btn.click(on_submit, [question_box, state], [chatbot, question_box, status])
    question_box.submit(on_submit, [question_box, state], [chatbot, question_box, status])

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=int(os.environ.get("PORT", 7860)))
