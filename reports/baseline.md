# Eval report: `baseline`

Fixed 800-char chunks, pgvector cosine top-5

- Embedder: `hash512`
- Generator: `fake-extractive`
- Judge: `offline:key-fact-recall`
- Questions: 40 (34 answerable, 6 unanswerable)

| Metric | Value |
|---|---|
| Retrieval hit rate@5 | 100.0% |
| Retrieval recall@5 | 94.8% |
| MRR | 0.966 |
| Evidence@5 (answer passage retrieved) | 97.1% |
| Answer correctness | 42.2% |
| Key-fact recall | 42.2% |
| Token F1 | 21.6% |
| Refusal accuracy | 85.0% |
| Unanswerable refused | 4/6 |
| Answerable wrongly refused | 4/34 |
| LLM cost | $0.0000 |

## By question type

| Type | n | hit@5 | recall@5 | MRR | evidence@5 | correctness |
|---|---|---|---|---|---|---|
| single | 28 | 100.0% | 99.1% | 0.958 | 96.4% | 42.6% |
| multi_hop | 6 | 100.0% | 75.0% | 1.000 | 100.0% | 40.3% |

## Per question

| id | type | hit@5 | RR | correctness | refusal ok | first retrieved |
|---|---|---|---|---|---|---|
| s01 | single | 1 | 1.00 | 1.00 | yes | query-params.md > Query Parameters |
| s02 | single | 1 | 1.00 | 1.00 | yes | query-params.md > Query parameter type conversion |
| s03 | single | 1 | 1.00 | 1.00 | yes | query-params-str-validations.md > Use `Annotated` in the type for the `q` parameter |
| s04 | single | 1 | 0.33 | 0.00 | yes | query-param-models.md > Optional Query Parameter Models |
| s05 | single | 1 | 1.00 | 0.67 | yes | query-params-str-validations.md > Query parameter list / multiple values |
| s06 | single | 1 | 1.00 | 1.00 | yes | path-params.md > Pydantic |
| s07 | single | 1 | 1.00 | 0.00 | yes | path-params.md > Path parameters containing paths |
| s08 | single | 1 | 1.00 | 0.00 | yes | path-params-numeric-validations.md > Path Parameters and Numeric Validations |
| s09 | single | 1 | 1.00 | 0.00 | NO | body.md > Request Body |
| s10 | single | 1 | 1.00 | 0.60 | yes | body.md > Request body + path parameters |
| s11 | single | 1 | 1.00 | 1.00 | yes | body-multiple-params.md > Multiple body params and query |
| s12 | single | 1 | 1.00 | 1.00 | yes | body-nested-models.md > Use the submodel as a type |
| s13 | single | 1 | 1.00 | 0.00 | yes | body-updates.md > Partial updates recap |
| s14 | single | 1 | 1.00 | 0.50 | yes | header-param-models.md > Forbid Extra Headers |
| s15 | single | 1 | 1.00 | 0.00 | NO | cookie-params.md > Declare `Cookie` parameters |
| s16 | single | 1 | 1.00 | 0.00 | yes | query-param-models.md > Check the Docs |
| s17 | single | 1 | 1.00 | 1.00 | yes | request-forms-and-files.md > Request Forms and Files |
| s18 | single | 1 | 1.00 | 0.00 | yes | request-files.md > Define `File` Parameters |
| s19 | single | 1 | 1.00 | 0.50 | yes | request-forms.md > Define `Form` parameters |
| s20 | single | 1 | 1.00 | 1.00 | yes | response-model.md > Response Model encoding parameters |
| s21 | single | 1 | 1.00 | 0.00 | yes | response-status-code.md > Response Status Code |
| s22 | single | 1 | 1.00 | 0.00 | yes | cors.md > Use `CORSMiddleware` |
| s23 | single | 1 | 1.00 | 0.50 | yes | middleware.md > Before and after the `response` |
| s24 | single | 1 | 1.00 | 0.00 | NO | dependencies/sub-dependencies.md > Using the same dependency multiple times |
| s25 | single | 1 | 1.00 | 0.00 | yes | security/first-steps.md > The `password` flow |
| s26 | single | 1 | 1.00 | 0.33 | yes | security/oauth2-jwt.md > Hash and verify the passwords |
| s27 | single | 1 | 0.50 | 0.33 | yes | stream-json-lines.md > No Return Type |
| s28 | single | 1 | 1.00 | 0.50 | yes | dependencies/dependencies-with-yield.md > Early exit and `scope` |
| m01 | multi_hop | 1 | 1.00 | 0.00 | NO | dependencies/dependencies-in-path-operation-decorators.md > Dependencies for a group of *path operations* |
| m02 | multi_hop | 1 | 1.00 | 0.67 | yes | static-files.md > What is "Mounting" |
| m03 | multi_hop | 1 | 1.00 | 0.50 | yes | middleware.md > Middleware |
| m04 | multi_hop | 1 | 1.00 | 0.00 | yes | sql-databases.md > `HeroCreate` - the *data model* to create a hero |
| m05 | multi_hop | 1 | 1.00 | 0.50 | yes | stream-json-lines.md > No Return Type |
| m06 | multi_hop | 1 | 1.00 | 0.75 | yes | security/simple-oauth2.md > Simple OAuth2 with Password and Bearer |
| u01 | unanswerable | - | - | - | yes | first-steps.md > About FastAPI Cloud |
| u02 | unanswerable | - | - | - | yes | index.md > Install FastAPI |
| u03 | unanswerable | - | - | - | yes | query-params-str-validations.md > Additional validation |
| u04 | unanswerable | - | - | - | NO | first-steps.md > Define a *path operation decorator* |
| u05 | unanswerable | - | - | - | NO | request-files.md > Define `File` Parameters |
| u06 | unanswerable | - | - | - | yes | dependencies/index.md > Declare the dependency, in the "dependant" |
