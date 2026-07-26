# Generic image intake

`cs2_manifest.py` writes schema v2. A primary image is the only required input. It is admitted independently and, when valid, produces `state: proceed` with a `genericHandoff`, even if no item can be identified.

```bash
python3 forge/stage1_intake/cs2_manifest.py reference.png --out intake.json
python3 forge/stage2_spec/new_pre_spec_assessment.py "Observed object" --manifest intake.json --out assessment.json
python3 forge/stage2_spec/new_sculpt_spec.py "Observed object" --manifest intake.json --assessment assessment.json --out spec.json
```

`sourceViews` uses `role: primary` and optional `role: secondary`; consumers select the primary role rather than an array position. Version-1 manifests normalize their first source into the primary role for read compatibility.

Identity is optional enrichment. Candidates are stable, ranked provider records. Use `--confirm accept --candidate-id <id>` only after the user accepts a candidate. `none-of-these` and `continue-generically` clear adapter eligibility; `add-secondary` pauses for another image while retaining the generic handoff. A registered adapter is selected only for an accepted candidate.

Secondary admission and association are recorded independently. A duplicate, unreadable, ambiguous, or contradictory secondary image requests replacement but cannot revoke a valid primary's generic continuation. Provider and retrieval outcomes live under `enrichment` and remain non-blocking.

`genericHandoff` carries the primary source plus observed geometry, materials, details, inferred regions, route, exactness tier, and explicit null identity/adapter sentinels. Generic authoring writes `genericIntake`; it does not choose knife geometry.
