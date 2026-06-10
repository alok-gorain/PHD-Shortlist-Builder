# PhD Shortlist Builder

Production-quality take-home solution for the **AI Engineer — PhD Shortlist Builder** assignment.

## Problem understanding

Given a student profile, produce a ranked JSON shortlist of PhD supervisors/programs in the student's
target countries. The hard part is not calling an LLM; it is avoiding data contamination: wrong country,
wrong person, junior non-supervisors, weak evidence, and generic matching.

This solution builds a deterministic retrieval, filtering, scoring, validation, and feedback-loop
pipeline. It prioritizes mentor-approved quality over maximum list length.

## Solution approach

1. Parse and validate a student JSON profile.
2. Query OpenAlex for researchers in each stated research area, restricted to target-country institutions.
3. Retrieve each candidate's highly cited/relevant works.
4. Drop candidates without verifiable paper evidence.
5. Penalize likely same-name and career-stage risks.
6. Rank by topical fit, evidence strength, academic authority, and optional outcome-feedback signals.
7. Emit a documented JSON schema with quality flags and validation warnings.

## Data sources

- OpenAlex Authors API for researcher identities, affiliations, countries, concepts, and publication counts.
- OpenAlex Works API for evidence papers and DOI/OpenAlex links.
- Optional historical outreach CSV for feedback-loop ranking adjustments.

No email is guessed. `contact_email` remains null unless a future trusted source is added.

## Project structure

```text
solution/
  phd_shortlist/              # Python package
    builder.py                # End-to-end shortlist builder
    cli.py                    # Command-line interface
    quality.py                # Data-quality flags and eligibility heuristics
    scoring.py                # Ranking and tiering
    outcomes.py               # Bonus feedback-loop implementation
    data_sources/openalex.py  # Cached OpenAlex client
    models/schema.py          # Pydantic input/output schema
  examples/
    sample_student_profile.json
    outcomes_sample.csv
  sample_output/
    sample_biomaterials_001.json
  tests/
  README.md
  DECISIONS.md
  schema.md
  requirements.txt
  pyproject.toml
```

## Setup

```bash
cd solution
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Run

Generate a shortlist:

```bash
phd-shortlist build examples/sample_student_profile.json \
  --output sample_output/sample_biomaterials_001.json \
  --openalex-mailto your-email@example.com
```

If you are behind a corporate proxy with a self-signed certificate chain, use
`--insecure-skip-tls-verify` only as a last resort.

With the bonus feedback loop:

```bash
phd-shortlist build examples/sample_student_profile.json \
  --outcomes-csv examples/outcomes_sample.csv \
  --output sample_output/sample_biomaterials_001.json
```

Validate an output file:

```bash
phd-shortlist validate sample_output/sample_biomaterials_001.json
```

Run tests:

```bash
pytest
```

## Output format

The output is one JSON file per student. Each recommendation contains:

- supervisor identity and institution
- country, constrained to target countries
- evidence papers with URLs
- matched student research areas
- personalized `why_match`
- tier and ranking score
- linked programs/positions
- quality flags for reviewer triage

See `schema.md` for the full documented schema.

## Assumptions

- Target countries are hard constraints; uncertain country records are excluded.
- OpenAlex coverage is sufficient for a first-pass shortlist on mainstream research areas.
- It is better to omit contact email than to hallucinate or scrape unreliable addresses.
- Program/open-position links require final human eligibility verification unless parsed from a trusted ad.
- The sample profile is representative because the assignment PDF did not include a separate student JSON.

## Known limitations

- Grants are supported by schema but not fetched in the base public-data implementation.
- Email discovery is not implemented.
- Some genuine early-career assistant professors may be under-ranked due to conservative career-stage guards.
- Full 50–200 coverage depends on topic breadth and OpenAlex availability.
