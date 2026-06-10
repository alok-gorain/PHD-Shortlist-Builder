# Output JSON Schema

The generated shortlist is a single JSON object validated by Pydantic models in
`phd_shortlist/models/schema.py`.

## Top-level object

| Field | Type | Description |
| --- | --- | --- |
| `student_id` | string | Stable identifier copied from the input profile. |
| `schema_version` | string | Output contract version, currently `1.0`. |
| `metadata` | object | Generation metadata and warnings. |
| `recommendations` | array | Ranked supervisor recommendations. |

## `metadata`

| Field | Type | Description |
| --- | --- | --- |
| `generated_at` | ISO datetime | UTC generation timestamp. |
| `generator_version` | string | Package version. |
| `data_sources` | string[] | APIs or datasets used. |
| `target_countries` | string[] | Canonical country names used as hard filters. |
| `requested_min` | integer | Requested minimum recommendation count. |
| `requested_max` | integer | Requested maximum recommendation count. |
| `total_recommendations` | integer | Number of returned recommendations. |
| `warnings` | string[] | Non-fatal issues such as low coverage. |

## `recommendations[]`

| Field | Type | Description |
| --- | --- | --- |
| `supervisor_id` | string | Stable source identifier, usually OpenAlex author ID suffix. |
| `name` | string | Supervisor name. |
| `institution` | string | Current institution from source metadata. |
| `country` | string | Must be inside `metadata.target_countries`. |
| `contact_email` | string/null | Email if obtainable; left null when not safely sourced. |
| `profile_url` | string | Source profile URL. |
| `research_focus` | string[] | Source concepts/fields. |
| `matched_student_areas` | string[] | Student research areas matched by the system. |
| `evidence` | object[] | Verifiable papers, grants, or positions. At least one required. |
| `why_match` | string | Personalized outreach rationale referencing specific PI work. |
| `tier` | enum | `reach`, `target`, or `safety`. |
| `score` | number | Normalized ranking score in `[0, 1]`. |
| `linked_programs_or_positions` | object[] | Program/open-position links or search URLs. |
| `quality_flags` | object | Same-name, career-stage, evidence, and eligibility risks. |
| `source_metadata` | object | Debuggable source IDs, counts, and score breakdown. |

## `evidence[]`

| Field | Type | Description |
| --- | --- | --- |
| `type` | enum | `paper`, `grant`, or `position`. |
| `title` | string | Evidence title. |
| `year` | integer/null | Publication or award year. |
| `url` | string | Verifiable source link. |
| `source` | string | Data source name. |
| `relevance_reason` | string | Why this evidence survived relevance filtering. |

## Hard validation rules

- Every recommendation must have at least one evidence item with a URL.
- Every recommendation country must be within the target country set.
- `supervisor_id` values must be unique.
- `why_match` must be present and personalized to the student.
