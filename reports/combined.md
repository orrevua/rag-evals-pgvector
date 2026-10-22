# Eval report: `combined`

Structure-aware chunks + hybrid retrieval + rerank

- Embedder: `hash512`
- Generator: `fake-extractive`
- Judge: `offline:key-fact-recall`
- Questions: 40 (34 answerable, 6 unanswerable)

| Metric | Value |
|---|---|
| Retrieval hit rate@5 | 100.0% |
| Retrieval recall@5 | 94.1% |
| MRR | 0.971 |
| Evidence@5 (answer passage retrieved) | 97.1% |
| Answer correctness | 56.7% |
| Key-fact recall | 56.7% |
| Token F1 | 26.8% |
| Refusal accuracy | 95.0% |
| Unanswerable refused | 4/6 |
| Answerable wrongly refused | 0/34 |
| LLM cost | $0.0000 |

## By question type

| Type | n | hit@5 | recall@5 | MRR | evidence@5 | correctness |
|---|---|---|---|---|---|---|
| single | 28 | 100.0% | 98.2% | 0.964 | 100.0% | 59.0% |
| multi_hop | 6 | 100.0% | 75.0% | 1.000 | 83.3% | 45.8% |

## Per question

| id | type | hit@5 | RR | correctness | refusal ok | first retrieved |
|---|---|---|---|---|---|---|
| s01 | single | 1 | 1.00 | 1.00 | yes | query-params.md > Query Parameters > Defaults |
| s02 | single | 1 | 1.00 | 1.00 | yes | query-params.md > Query Parameters > Query parameter type conversion |
| s03 | single | 1 | 1.00 | 1.00 | yes | query-params-str-validations.md > Query Parameters and String Validations > Add `Query` to `Annotated` in the `q` parameter |
| s04 | single | 1 | 1.00 | 0.00 | yes | query-params-str-validations.md > Query Parameters and String Validations > Custom Validation |
| s05 | single | 1 | 1.00 | 0.67 | yes | query-params-str-validations.md > Query Parameters and String Validations > Query parameter list / multiple values |
| s06 | single | 1 | 1.00 | 1.00 | yes | path-params.md > Path Parameters > Order matters |
| s07 | single | 1 | 1.00 | 0.00 | yes | path-params.md > Path Parameters > Path parameters containing paths |
| s08 | single | 1 | 1.00 | 0.00 | yes | path-params-numeric-validations.md > Path Parameters and Numeric Validations > Number validations: greater than or equal |
| s09 | single | 1 | 1.00 | 0.25 | yes | body.md > Request Body |
| s10 | single | 1 | 0.50 | 0.60 | yes | body-multiple-params.md > Body - Multiple Parameters > Singular values in body |
| s11 | single | 1 | 1.00 | 1.00 | yes | body-multiple-params.md > Body - Multiple Parameters > Embed a single body parameter |
| s12 | single | 1 | 1.00 | 1.00 | yes | body-nested-models.md > Body - Nested Models > Nested Models |
| s13 | single | 1 | 1.00 | 1.00 | yes | body-updates.md > Body - Updates > Partial updates with `PATCH` > Partial updates recap |
| s14 | single | 1 | 1.00 | 0.50 | yes | header-param-models.md > Header Parameter Models > Disable Convert Underscores |
| s15 | single | 1 | 0.50 | 0.50 | yes | testing.md > Testing > Testing: extended example > Extended testing file |
| s16 | single | 1 | 1.00 | 0.00 | yes | query-param-models.md > Query Parameter Models > Forbid Extra Query Parameters |
| s17 | single | 1 | 1.00 | 1.00 | yes | request-forms-and-files.md > Request Forms and Files |
| s18 | single | 1 | 1.00 | 0.00 | yes | request-files.md > Request Files > Multiple File Uploads > Multiple File Uploads with Additional Metadata |
| s19 | single | 1 | 1.00 | 0.50 | yes | request-forms.md > Form Data > Boolean Form Fields |
| s20 | single | 1 | 1.00 | 1.00 | yes | response-model.md > Response Model - Return Type > Response Model encoding parameters > Use the `response_model_exclude_unset` parameter |
| s21 | single | 1 | 1.00 | 0.50 | yes | response-status-code.md > Response Status Code > About HTTP status codes |
| s22 | single | 1 | 1.00 | 0.00 | yes | cors.md > CORS (Cross-Origin Resource Sharing) > Use `CORSMiddleware` |
| s23 | single | 1 | 1.00 | 0.50 | yes | middleware.md > Middleware > Multiple middleware execution order |
| s24 | single | 1 | 1.00 | 1.00 | yes | dependencies/sub-dependencies.md > Sub-dependencies > Using the same dependency multiple times |
| s25 | single | 1 | 1.00 | 1.00 | yes | security/first-steps.md > Security - First Steps > What it does |
| s26 | single | 1 | 1.00 | 0.67 | yes | security/oauth2-jwt.md > OAuth2 with Password (and hashing), Bearer with JWT tokens > Handle JWT tokens |
| s27 | single | 1 | 1.00 | 0.33 | yes | server-sent-events.md > Server-Sent Events (SSE) > Technical Details |
| s28 | single | 1 | 1.00 | 0.50 | yes | dependencies/dependencies-with-yield.md > Dependencies with yield > Early exit and `scope` > `scope` for sub-dependencies |
| m01 | multi_hop | 1 | 1.00 | 0.33 | yes | bigger-applications.md > Bigger Applications - Multiple Files > Another module with `APIRouter` |
| m02 | multi_hop | 1 | 1.00 | 0.67 | yes | static-files.md > Static Files > Use `StaticFiles` > What is "Mounting" |
| m03 | multi_hop | 1 | 1.00 | 0.50 | yes | middleware.md > Middleware |
| m04 | multi_hop | 1 | 1.00 | 0.00 | yes | sql-databases.md > SQL (Relational) Databases > Update the App with Multiple Models |
| m05 | multi_hop | 1 | 1.00 | 0.50 | yes | stream-json-lines.md > Stream JSON Lines > Server-Sent Events (SSE) |
| m06 | multi_hop | 1 | 1.00 | 0.75 | yes | security/simple-oauth2.md > Simple OAuth2 with Password and Bearer > Get the `username` and `password` |
| u01 | unanswerable | - | - | - | yes | first-steps.md > First Steps > Deploy your app (optional) |
| u02 | unanswerable | - | - | - | yes | handling-errors.md > Handling Errors > Add custom headers |
| u03 | unanswerable | - | - | - | yes | security/first-steps.md > Security - First Steps > **FastAPI**'s `OAuth2PasswordBearer` |
| u04 | unanswerable | - | - | - | NO | dependencies/index.md > Dependencies > Integrated with OpenAPI |
| u05 | unanswerable | - | - | - | NO | request-files.md > Request Files > File Parameters with `UploadFile` |
| u06 | unanswerable | - | - | - | yes | bigger-applications.md > Bigger Applications - Multiple Files > Configure the `entrypoint` in `pyproject.toml` |
