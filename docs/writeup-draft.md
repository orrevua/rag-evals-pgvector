---
title: "How I improved RAG accuracy from 42% to 57% (and what the number hides)"
status: draft
blog: orrevua.dev
repo: rag-evals-pgvector
---

<!--
DRAFT. Numbers marked {{LIKE_THIS}} are placeholders for real-model runs that have NOT been done
yet. Every other number comes from reports/RESULTS.md, produced offline with the hashing
embedder (hash512) and the extractive fake generator, judged by key-fact recall.
Before publishing: run exercise 11 in LEARNING.md, fill the placeholders, and decide whether the
title should quote the offline or the real-model numbers (probably the real ones, if they hold).
-->

# How I improved RAG accuracy from 42% to 57% (and what the number hides)

I'm a backend developer learning AI engineering. My first project: a question-answering service
over the FastAPI tutorial, using the database I already know (PostgreSQL, with pgvector). The
goal wasn't the chatbot. It was answering one question I kept running into in RAG blog posts:
*how do you know a change made it better?*

TL;DR: with a 40-question golden set and five pipeline configs, answer correctness went from
**42.2% (naive baseline) to 56.7% (structure-aware chunks + hybrid search + reranking)** in a
fully offline setup. With real models (`{{EMBEDDER}}` + Claude), it went from
**{{REAL_BASELINE_CORRECTNESS}} to {{REAL_BEST_CORRECTNESS}}**. But the most useful findings
were about the measurements, not the techniques.

## The setup

- **Corpus:** the FastAPI tutorial (51 Markdown pages, MIT licensed), pinned to one upstream
  commit. The code samples it includes from other files are *not* in the corpus, so some answers
  only exist in prose.
- **Store:** one `chunks` table with a `vector` column (pgvector) and a generated, weighted
  `tsvector` column for full-text search. Schema changes are plain numbered SQL files.
- **Pipeline:** chunker -> embedder -> retriever -> (reranker) -> generator, each behind a small
  interface so a *config* is just a choice of parts.
- **Offline first:** a deterministic hashing embedder and an extractive "fake LLM" that answers
  by quoting retrieved sentences with `[n]` citations, and refuses when the context doesn't
  cover the question. CI runs the whole thing with no API keys.

`[diagram: architecture mermaid from README]`

## The golden set

40 questions I wrote after reading every page:

- 28 single-hop ("What does `response_model_exclude_unset=True` do?"),
- 6 multi-hop, needing two pages ("How does mounting `StaticFiles` differ from including an
  `APIRouter` with respect to the OpenAPI docs?"),
- 6 unanswerable, where the right answer is "I don't know" ("How do I deploy to AWS Lambda
  with Mangum?").

Each item has an expected answer, expected source files and a few **key facts**, short phrases
any correct answer must contain (`use_cache=False`, `422`). A test checks every key fact really
appears in its source page. On the first run it flagged two "missing" facts, and both
turned out to be a bug in my Markdown cleaner that silently deleted the first line of every
unlabelled code block. The eval found a data bug before it found anything about retrieval.

## The metrics

| Metric | Question it answers |
|---|---|
| Hit@5, recall@5 | Is the right page in the top 5? (recall: all pages, for multi-hop) |
| MRR | How high is the first right page? |
| Evidence@5 | Did the passage that contains the answer reach the prompt? |
| Correctness | Is the answer right? Offline: key-fact recall. Online: LLM-as-judge (fast model). |
| Refusal accuracy | Did it refuse exactly the unanswerable questions? |

## Results

Offline (`hash512` embedder, extractive generator, key-fact judge), 34 answerable questions:

| Config | What changes | MRR | Evidence@5 | Correctness | Refusal acc. |
|---|---|---|---|---|---|
| baseline | fixed 800-char chunks, vector top-5 | 0.966 | 97.1% | 42.2% | 85.0% |
| hybrid | + full-text search, RRF | 0.980 | 97.1% | 50.8% | 97.5% |
| rerank | + BM25 rerank of 20 candidates | 0.971 | 100.0% | 50.3% | 95.0% |
| structured | Markdown-section chunks | 0.936 | 97.1% | 50.7% | 87.5% |
| combined | structured + hybrid + rerank | 0.971 | 97.1% | 56.7% | 95.0% |

Real models (`{{EMBEDDER}}`, `{{GENERATOR_MODEL}}`, judge `{{JUDGE_MODEL}}`):

| Config | MRR | Evidence@5 | Correctness (judge) | Refusal acc. | Cost per 40 questions |
|---|---|---|---|---|---|
| baseline | {{}} | {{}} | {{}} | {{}} | {{}} |
| hybrid | {{}} | {{}} | {{}} | {{}} | {{}} |
| rerank (`{{RERANKER}}`) | {{}} | {{}} | {{}} | {{}} | {{}} |
| structured | {{}} | {{}} | {{}} | {{}} | {{}} |
| combined | {{}} | {{}} | {{}} | {{}} | {{}} |

## What the number hides

**1. The retrieval metric everyone quotes was useless here.** Hit@5 was 100% for every config,
including the baseline. With 51 pages, finding the right *page* is easy; getting the right
*passage* in front of the model, ranked high, is the actual problem. I added evidence@5 and
leaned on MRR. Lesson: if a metric never moves, it isn't measuring your change.

**2. Half the gain came from refusing less, not retrieving better.** The baseline refused 4
answerable questions because its top chunks didn't cover the question's key terms. Hybrid search
pulled in chunks that did, so it stopped refusing them (0 false refusals), and each of those
questions went from 0 to some credit. "Hybrid search improved correctness by 8.6 points" is true,
and also misleading if you don't open the per-question report.

**3. Structure-aware chunking helped answers, not ranking.** Its MRR is the *lowest* of all
configs (0.936), yet correctness rose by 8.5 points: sections are coherent, so the sentence that
answers the question sits next to the heading that names it. Different metrics, different stories.

**4. Unanswerable questions are where heuristics break.** "What is the default maximum upload
size in MB?" fooled every offline config: the docs do say files are kept in memory "up to a
maximum size limit", just without a number. {{REAL_MODEL_RESULT_ON_U05}}

**5. Small eval, big error bars.** One question is about 3 points. I'd only trust differences of
~10 points or more on this set, and I chose the fake generator's refusal threshold while looking
at these same questions, so its refusal accuracy is optimistic. A held-out split is next.

## What I'd do differently

- Write paraphrased, user-style questions from the start; mine reuse the docs' vocabulary, which
  flatters lexical retrieval.
- Split the golden set into dev and test on day one.
- Track cost and latency per config in the same table as quality (the `request_log` table has
  the data: {{P95_LATENCY_BY_CONFIG}}, {{COST_PER_1K_QUESTIONS}}).

## Try it

```bash
git clone https://github.com/orrevua/rag-evals-pgvector && cd rag-evals-pgvector
make up   # or: make setup && make ingest && make eval-all
```

`{{LINK_TO_REPO}}` · `{{LINK_TO_RESULTS_MD}}`
