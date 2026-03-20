# 🧬 PubMed Research Bot

A chatbot that searches PubMed in real time and synthesises the findings using Claude (Anthropic).


## How it works

1. User asks a bio question
2. App queries the PubMed E-utilities API for the top 6 relevant papers
3. Abstracts are passed to Claude with a synthesis prompt
4. Claude returns a cited answer + key takeaways
5. Source articles with PubMed links are shown below the answer

