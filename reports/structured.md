# Eval report: `structured`

Baseline with structure-aware chunks (one per Markdown section)

- Embedder: `hash512`
- Generator: `fake-extractive`
- Judge: `offline:key-fact-recall`
- Questions: 40 (34 answerable, 6 unanswerable)

| Metric | Value |
|---|---|
| Retrieval hit rate@5 | 100.0% |
| Retrieval recall@5 | 95.1% |
| MRR | 0.936 |
| Evidence@5 (answer passage retrieved) | 97.1% |
| Answer correctness | 50.7% |
| Key-fact recall | 50.7% |
| Token F1 | 22.0% |
| Refusal accuracy | 87.5% |
| Unanswerable refused | 5/6 |
| Answerable wrongly refused | 4/34 |
| LLM cost | $0.0000 |

## By question type

| Type | n | hit@5 | recall@5 | MRR | evidence@5 | correctness |
|---|---|---|---|---|---|---|
| single | 28 | 100.0% | 98.2% | 0.941 | 100.0% | 53.0% |
| multi_hop | 6 | 100.0% | 80.6% | 0.917 | 83.3% | 40.3% |

## Per question

| id | type | hit@5 | RR | correctness | refusal ok | first retrieved |
|---|---|---|---|---|---|---|
| s01 | single | 1 | 1.00 | 1.00 | yes | query-params.md > Query Parameters > Required query parameters |
| s02 | single | 1 | 1.00 | 1.00 | yes | query-params.md > Query Parameters > Query parameter type conversion |
| s03 | single | 1 | 0.50 | 1.00 | yes | query-params.md > Query Parameters > Optional parameters |
| s04 | single | 1 | 0.50 | 0.00 | yes | query-param-models.md > Query Parameter Models > Query Parameters with a Pydantic Model |
| s05 | single | 1 | 1.00 | 0.67 | yes | query-params-str-validations.md > Query Parameters and String Validations > Query parameter list / multiple values > Query parameter list / multiple values with defaults |
| s06 | single | 1 | 1.00 | 1.00 | yes | path-params.md > Path Parameters > Order matters |
| s07 | single | 1 | 1.00 | 0.00 | yes | path-params.md > Path Parameters > Path parameters containing paths |
| s08 | single | 1 | 1.00 | 0.00 | yes | path-params-numeric-validations.md > Path Parameters and Numeric Validations > Import `Path` |
| s09 | single | 1 | 1.00 | 0.00 | NO | body.md > Request Body |
| s10 | single | 1 | 0.33 | 0.00 | NO | body-multiple-params.md > Body - Multiple Parameters > Mix `Path`, `Query` and body parameters |
| s11 | single | 1 | 1.00 | 1.00 | yes | body-multiple-params.md > Body - Multiple Parameters > Embed a single body parameter |
| s12 | single | 1 | 1.00 | 1.00 | yes | body-nested-models.md > Body - Nested Models > Nested Models |
| s13 | single | 1 | 1.00 | 1.00 | yes | body-updates.md > Body - Updates > Partial updates with `PATCH` > Using Pydantic's `exclude_unset` parameter |
| s14 | single | 1 | 1.00 | 0.50 | yes | header-param-models.md > Header Parameter Models > Disable Convert Underscores |
| s15 | single | 1 | 1.00 | 0.00 | NO | cookie-param-models.md > Cookie Parameter Models > Cookies with a Pydantic Model |
| s16 | single | 1 | 1.00 | 0.00 | yes | query-param-models.md > Query Parameter Models > Forbid Extra Query Parameters |
| s17 | single | 1 | 1.00 | 1.00 | yes | request-forms-and-files.md > Request Forms and Files |
| s18 | single | 1 | 1.00 | 0.00 | yes | request-files.md > Request Files > File Parameters with `UploadFile` |
| s19 | single | 1 | 1.00 | 0.50 | yes | request-forms.md > Form Data > Boolean Form Fields |
| s20 | single | 1 | 1.00 | 1.00 | yes | response-model.md > Response Model - Return Type > Response Model encoding parameters > Use the `response_model_exclude_unset` parameter |
| s21 | single | 1 | 1.00 | 0.00 | yes | response-status-code.md > Response Status Code > About HTTP status codes |
| s22 | single | 1 | 1.00 | 0.00 | yes | cors.md > CORS (Cross-Origin Resource Sharing) > Use `CORSMiddleware` |
| s23 | single | 1 | 1.00 | 0.50 | yes | middleware.md > Middleware > Multiple middleware execution order |
| s24 | single | 1 | 1.00 | 1.00 | yes | dependencies/sub-dependencies.md > Sub-dependencies > Using the same dependency multiple times |
| s25 | single | 1 | 1.00 | 1.00 | yes | security/first-steps.md > Security - First Steps > What it does |
| s26 | single | 1 | 1.00 | 0.33 | yes | security/oauth2-jwt.md > OAuth2 with Password (and hashing), Bearer with JWT tokens > Handle JWT tokens |
| s27 | single | 1 | 1.00 | 0.33 | yes | server-sent-events.md > Server-Sent Events (SSE) > Technical Details |
| s28 | single | 1 | 1.00 | 1.00 | yes | dependencies/dependencies-with-yield.md > Dependencies with yield > Early exit and `scope` |
| m01 | multi_hop | 1 | 0.50 | 0.00 | NO | path-operation-configuration.md > Path Operation Configuration |
| m02 | multi_hop | 1 | 1.00 | 0.67 | yes | static-files.md > Static Files > Use `StaticFiles` > What is "Mounting" |
| m03 | multi_hop | 1 | 1.00 | 0.50 | yes | middleware.md > Middleware |
| m04 | multi_hop | 1 | 1.00 | 0.00 | yes | sql-databases.md > SQL (Relational) Databases > Update the App with Multiple Models > Create Multiple Models > `HeroCreate` - the *data model* to create a hero |
| m05 | multi_hop | 1 | 1.00 | 0.50 | yes | stream-json-lines.md > Stream JSON Lines > Server-Sent Events (SSE) |
| m06 | multi_hop | 1 | 1.00 | 0.75 | yes | security/simple-oauth2.md > Simple OAuth2 with Password and Bearer > Get the `username` and `password` |
| u01 | unanswerable | - | - | - | yes | first-steps.md > First Steps > Recap |
| u02 | unanswerable | - | - | - | yes | index.md > Tutorial - User Guide > Install FastAPI |
| u03 | unanswerable | - | - | - | yes | path-params.md > Path Parameters > Recap |
| u04 | unanswerable | - | - | - | yes | testing.md > Testing > Separating tests > **FastAPI** app file |
| u05 | unanswerable | - | - | - | NO | request-files.md > Request Files > File Parameters with `UploadFile` |
| u06 | unanswerable | - | - | - | yes | security/first-steps.md > Security - First Steps > **FastAPI**'s `OAuth2PasswordBearer` > Use it |
