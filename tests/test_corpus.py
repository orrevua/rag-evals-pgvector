from ragevals.corpus import clean_markdown, load_corpus
from ragevals.settings import get_settings

RAW = """# First Steps { #first-steps }

The simplest FastAPI file could look like this:

{* ../../docs_src/first_steps/tutorial001_py310.py *}

/// tip | Pro tip

Use [the docs](https://fastapi.tiangolo.com) and <abbr title="Application">app</abbr>.

///

<div class="termy">

```console
$ <font color="#4E9A06">fastapi</font> dev
```

</div>

![Swagger UI](https://example.com/img.png)

```Python hl_lines="1"
q: str | None = None
```
"""


def test_clean_markdown_strips_mkdocs_noise():
    text = clean_markdown(RAW)
    assert text.startswith("# First Steps\n")
    assert "{*" not in text and "#first-steps" not in text
    assert "///" not in text
    assert "termy" not in text and "<font" not in text
    assert "Swagger UI" not in text  # images removed
    assert "Use the docs and app." in text  # links and inline HTML keep their text
    assert "```python\nq: str | None = None\n```" in text


def test_load_real_corpus():
    docs = load_corpus(get_settings().corpus_dir)
    sources = {d.source for d in docs}
    assert "query-params.md" in sources
    assert "security/oauth2-jwt.md" in sources
    assert "LICENSE" not in sources and "ATTRIBUTION.md" not in sources
    by_source = {d.source: d for d in docs}
    assert by_source["query-params.md"].title == "Query Parameters"
    assert all("{*" not in d.text for d in docs)
