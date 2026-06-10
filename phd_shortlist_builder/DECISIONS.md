# Decisions and Data Quality Trade-offs

This assignment rewards low contamination more than raw coverage. I therefore built the system as a
conservative retrieval-and-ranking pipeline rather than a broad scraper that treats every paper author as
a valid PhD supervisor.

## 1. Same-name-different-person collisions

OpenAlex author records are keyed by author IDs, but names remain ambiguous. The pipeline never merges
authors by name. It keeps the source author ID, current institution, country, works count, and concept
profile in the output. Records with weak affiliation evidence or common short names receive
`same_name_risk=true`, which lowers the ranking score. In a production extension, I would add homepage
verification via ROR/institution pages before exposing email addresses.

## 2. Career-stage errors

The implementation filters and penalizes likely junior profiles. It requires educational institution
affiliation, enough publication history, and relevant evidence. Low `works_count` profiles are removed or
marked with `career_stage_risk=true`. I intentionally avoid mining first authors from papers because that
would surface PhD students and postdocs. This loses some new assistant professors, but reduces the more
damaging error of recommending people who cannot supervise.

## 3. Wrong-domain leakage

The code does not rely on single keyword hits. It compares each candidate's concept profile and evidence
titles/abstracts against the complete student profile: stated interests, skills, projects, intro-call
summary, and resume text. Evidence with weak relevance is dropped before ranking. This is especially
important for ambiguous phrases such as “barcoding,” “trauma,” or “high-elevation systems,” where a
single token can point to the wrong discipline.

## 4. Country adherence

Target country is treated as a hard filter using structured OpenAlex institution metadata. The parser
prefers target-country educational affiliations from `affiliations`, then falls back to
`last_known_institutions` when appropriate, and the output validator checks country again before writing.
This is stricter than using program text, because institution country is structured and less error-prone.

## 5. Evidence quality

Each recommendation must include at least one verifiable evidence URL. The system uses DOI/OpenAlex work
links and records a `relevance_reason` so a reviewer can inspect why the item survived filtering. If no
paper evidence survives, the supervisor is not recommended. The trade-off is that strong supervisors with
poorly indexed publication metadata may be missed.

## 6. Eligibility in free-text ads

The current implementation treats linked programs conservatively: it emits institution program search
links with an explicit eligibility note instead of claiming a student is eligible for a vacancy. The
quality module includes regex patterns for “UK only,” “home fees,” “EU residents only,” and similar
phrases. If position scraping is added, these patterns should become hard filters for international
students before a position is attached to a recommendation.

## 7. Feedback loop bonus

`outcomes.py` implements a simple online-learning layer from historical outreach outcomes. Positive
signals such as `ADMIT`, `INTERVIEW`, and `POSITIVE_REPLY` boost supervisors, institutions, and areas.
Negative signals such as `WRONG_PERSON`, `BOUNCE`, and `NOT_RECRUITING` penalize them. This is
deliberately transparent and bounded so one noisy outcome cannot dominate relevance. A production system
would evolve this into a learning-to-rank model with per-domain calibration and delayed-feedback handling.

## Known limitations

- OpenAlex usually lacks email addresses; the system leaves `contact_email` null rather than hallucinating.
- Grants are represented in the schema but not fetched in the base implementation. NIH RePORTER, UKRI
  Gateway to Research, NSF Award Search, and Dimensions would be natural additions.
- Institution program links are search URLs, not fully parsed admissions pages.
- The scoring model is heuristic. It is inspectable and deterministic, but not yet mentor-calibrated.
