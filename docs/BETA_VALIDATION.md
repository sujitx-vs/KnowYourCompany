# Private-beta validation protocol

Status: prepared, not conducted. Do not record assumed user responses or claim market validation from fixture tests.

Recruit five students or early-career candidates preparing for an actual interview. Each participant should use a company they know or are applying to, and one ambiguous or less-documented company. Obtain feedback without supplying the answers or steering participants toward a positive rating.

## Tasks to observe

1. Start research and explain what the application is doing while waiting.
2. Decide whether the identified company is correct.
3. Read the company brief and follow a citation to its source.
4. Choose a career area and identify the next study action.
5. Explain which statements are company facts and which are recommendations.
6. Refresh during research, then return to the saved brief.
7. Download the PDF and describe what would make them use the product again.

Record task completion, points of confusion, abandonment, perceived waiting time, correctness concerns and useful next actions. Do not interpret a source count or confidence label as proof of correctness.

| Participant | Task completion | Delay understood? | Citation found? | Fact/advice distinction? | Return intent and reason | Suggested improvement |
|---|---|---|---|---|---|---|
| 1 | Pending | Pending | Pending | Pending | Pending | Pending |
| 2 | Pending | Pending | Pending | Pending | Pending | Pending |
| 3 | Pending | Pending | Pending | Pending | Pending | Pending |
| 4 | Pending | Pending | Pending | Pending | Pending | Pending |
| 5 | Pending | Pending | Pending | Pending | Pending | Pending |

## Quality and timing evaluation

Use the cases in tests/fixtures/evaluation_cases.json. Prepare concrete small-company and conflict/injection fixtures before a broad quality run; the descriptive entries there are coverage categories, not completed evaluations.

For every assessed company, manually review a sample of factual claims against their cited page text. Count correct identity, supported claims, missing or invalid citations, relevant career choices and clearly labelled uncertainty. Include non-English browser and PDF text checks; font coverage for all scripts is not assumed.

Use repeat runs on identical inputs to compare old/new implementations under comparable source availability, model, quota and hosting conditions. Separate cold start, warm uncached, cache hit, queue time, company stage, domain stage and PDF export. Report p50/p95 and provider cost per successful dossier, including failed-attempt costs where available. Do not extrapolate the synthetic scheduler result to end-to-end production latency.

## Commercial decision

Measure repeat usage and ask participants what they currently use and what they would replace. Validate whether saved research, multiple companies, deeper preparation or campus support creates repeat value. Determine a paid offering only after usefulness, repeat demand and service cost are established. Subscriptions, billing and institution administration are intentionally outside this implementation until that evidence exists.
