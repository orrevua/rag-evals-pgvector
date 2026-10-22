# Eval report: `rerank`

Baseline + rerank 20 vector candidates down to 5

- Embedder: `hash512`
- Generator: `fake-extractive`
- Judge: `offline:key-fact-recall`
- Questions: 40 (34 answerable, 6 unanswerable)

| Metric | Value |
|---|---|
| Retrieval hit rate@5 | 100.0% |
| Retrieval recall@5 | 95.1% |
| MRR | 0.971 |
| Evidence@5 (answer passage retrieved) | 100.0% |
| Answer correctness | 50.3% |
| Key-fact recall | 50.3% |
| Token F1 | 25.5% |
| Refusal accuracy | 95.0% |
| Unanswerable refused | 4/6 |
| Answerable wrongly refused | 0/34 |
| LLM cost | $0.0000 |

## By question type

| Type | n | hit@5 | recall@5 | MRR | evidence@5 | correctness |
|---|---|---|---|---|---|---|
| single | 28 | 100.0% | 98.2% | 0.964 | 100.0% | 52.4% |
| multi_hop | 6 | 100.0% | 80.6% | 1.000 | 100.0% | 40.3% |

## Per question

| id | type | hit@5 | RR | correctness | refusal ok | first retrieved |
|---|---|---|---|---|---|---|
| s01 | single | 1 | 1.00 | 1.00 | yes | query-params.md > Query Parameters |
| s02 | single | 1 | 1.00 | 1.00 | yes | query-params.md > Query parameter type conversion |
| s03 | single | 1 | 1.00 | 1.00 | yes | query-params-str-validations.md > Use `Annotated` in the type for the `q` parameter |
| s04 | single | 1 | 1.00 | 0.00 | yes | query-params-str-validations.md > Alias parameters |
| s05 | single | 1 | 1.00 | 0.67 | yes | query-params-str-validations.md > Query parameter list / multiple values |
| s06 | single | 1 | 1.00 | 1.00 | yes | path-params.md > Pydantic |
| s07 | single | 1 | 1.00 | 0.00 | yes | path-params.md > Path convertor |
| s08 | single | 1 | 1.00 | 0.00 | yes | path-params-numeric-validations.md > Better with `Annotated` |
| s09 | single | 1 | 1.00 | 0.25 | yes | body.md > Request Body |
| s10 | single | 1 | 0.50 | 0.60 | yes | body-multiple-params.md > Multiple body parameters |
| s11 | single | 1 | 1.00 | 1.00 | yes | body-multiple-params.md > Multiple body params and query |
| s12 | single | 1 | 1.00 | 1.00 | yes | body-nested-models.md > Set types |
| s13 | single | 1 | 1.00 | 0.00 | yes | body-updates.md > Partial updates recap |
| s14 | single | 1 | 1.00 | 0.50 | yes | header-param-models.md > Forbid Extra Headers |
| s15 | single | 1 | 0.50 | 1.00 | yes | testing.md > Extended testing file |
| s16 | single | 1 | 1.00 | 0.00 | yes | query-param-models.md > Check the Docs |
| s17 | single | 1 | 1.00 | 1.00 | yes | request-forms-and-files.md > Request Forms and Files |
| s18 | single | 1 | 1.00 | 0.00 | yes | request-files.md > Multiple File Uploads |
| s19 | single | 1 | 1.00 | 0.50 | yes | request-forms.md > Define `Form` parameters |
| s20 | single | 1 | 1.00 | 1.00 | yes | response-model.md > Response Model encoding parameters |
| s21 | single | 1 | 1.00 | 0.50 | yes | response-status-code.md > About HTTP status codes |
| s22 | single | 1 | 1.00 | 0.00 | yes | cors.md > Use `CORSMiddleware` |
| s23 | single | 1 | 1.00 | 0.50 | yes | middleware.md > Multiple middleware execution order |
| s24 | single | 1 | 1.00 | 1.00 | yes | dependencies/sub-dependencies.md > Using the same dependency multiple times |
| s25 | single | 1 | 1.00 | 0.00 | yes | security/first-steps.md > The `password` flow |
| s26 | single | 1 | 1.00 | 0.33 | yes | security/oauth2-jwt.md > Hash and verify the passwords |
| s27 | single | 1 | 1.00 | 0.33 | yes | server-sent-events.md > SSE with POST |
| s28 | single | 1 | 1.00 | 0.50 | yes | dependencies/dependencies-with-yield.md > Early exit and `scope` |
| m01 | multi_hop | 1 | 1.00 | 0.00 | yes | bigger-applications.md > *Path operations* with `APIRouter` |
| m02 | multi_hop | 1 | 1.00 | 0.67 | yes | static-files.md > Static Files |
| m03 | multi_hop | 1 | 1.00 | 0.50 | yes | middleware.md > Middleware |
| m04 | multi_hop | 1 | 1.00 | 0.00 | yes | sql-databases.md > Run the App |
| m05 | multi_hop | 1 | 1.00 | 0.50 | yes | server-sent-events.md > Server-Sent Events (SSE) |
| m06 | multi_hop | 1 | 1.00 | 0.75 | yes | security/simple-oauth2.md > Simple OAuth2 with Password and Bearer |
| u01 | unanswerable | - | - | - | yes | first-steps.md > About FastAPI Cloud |
| u02 | unanswerable | - | - | - | yes | request-forms.md > About "Form Fields" |
| u03 | unanswerable | - | - | - | yes | first-steps.md > Step 2: create a `FastAPI` "instance" |
| u04 | unanswerable | - | - | - | NO | first-steps.md > Define a *path operation decorator* |
| u05 | unanswerable | - | - | - | NO | request-files.md > File Parameters with `UploadFile` |
| u06 | unanswerable | - | - | - | yes | bigger-applications.md > Include a *path operation* |
