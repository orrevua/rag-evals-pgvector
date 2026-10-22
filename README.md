# rag-evals-pgvector

RAG question answering over the FastAPI tutorial, backed by PostgreSQL + pgvector, with an
evaluation suite. Work in progress: see the commit history for milestones.

```bash
make setup && make ingest
uv run ragevals ask "How do I declare an optional query parameter?"
make serve   # POST /ask
```
