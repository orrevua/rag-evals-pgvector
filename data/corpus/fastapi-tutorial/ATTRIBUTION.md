# Attribution

The Markdown files in this directory are the **FastAPI tutorial** ("Tutorial - User Guide")
from the FastAPI documentation, copied unmodified from:

- Repository: https://github.com/fastapi/fastapi
- Path: `docs/en/docs/tutorial/`
- Commit: `4bdfbe4513084b19e22421ce1f916d8c1ac462a0`

FastAPI and its documentation are Copyright (c) 2018 Sebastián Ramírez and are released under the
MIT License, reproduced in [`LICENSE`](LICENSE) in this directory.

The files are kept byte-for-byte as upstream. MkDocs-only syntax (code includes like
`{* ../../docs_src/... *}`, admonition fences `/// tip`, heading anchors `{ #id }`, terminal
animation `<div class="termy">` blocks, inline HTML) is stripped at load time by
`src/ragevals/corpus.py`, not in these files. Note that the code samples the tutorial includes
from `docs_src/` are **not** part of this corpus, so questions are answerable from prose only.
