## 1. Manifest and intake foundation

- [x] 1.1 Define and validate the versioned `cs2-intake.json` schema for source views, admission, identity, finish, assets, camera, provenance, confidence, warnings, and exactness tier.
- [x] 1.2 Define manifest state transitions, required/optional fields by route, atomic writes, resume behavior, extension namespace, and compatibility/rollback flag (`--cs2-pipeline legacy|manifest-v1`).
- [x] 1.3 Add a CS2 pipeline orchestrator that runs reference admission, image probing, heuristic routing, classification-record validation, intake-correctness, and manifest persistence with `proceed`, `request-input`, `fallback`, `rejected`, `unsupported-family`, and `unsupported-subtype` outcomes.
- [x] 1.4 Define the deterministic classification-record schema and offline fixture adapter for live vision/agent providers, including confidence, evidence references, provider/version, timeout, and unavailable behavior.
- [x] 1.5 Add offline fixtures and tests for valid image-only intake, invalid reference rejection, confident class contradiction, classification absence, unsupported family/subtype, and missing optional dependencies.

## 2. Golden fixture and review contract

- [x] 2.1 Verify or replace the knife reference with a rights-safe committed golden fixture and annotate identity, visible regions, critical features, camera, and hidden-region confidence.
- [x] 2.2 Define a versioned review-scene preset recording camera, transform, environment hash, exposure, tone mapping, resolution, background, and renderer version.
- [ ] 2.3 Calibrate and freeze positive/negative golden-render thresholds for silhouette IoU, aspect/scale deltas, painted-region masks, color/pattern/wear regions, and critical features before making CS2 gates blocking.

## 3. Identity, metadata, and evidence provenance

- [x] 3.1 Implement identity precedence from explicit user metadata to resolved metadata to classification record, while keeping `detect_cs2.py` non-authoritative.
- [x] 3.2 Adapt `fetch_cs2_metadata.py` to enrich the manifest with paint index, float range, rarity, preview URL, source provenance, and ambiguity errors.
- [x] 3.3 Normalize missing float, paint seed, hidden-view, and finish-style values into explicit approximation/confidence records consumed by spec authoring.
- [x] 3.4 Add tests covering unique metadata resolution, ambiguous records, no-match handling, and image-only continuation.

## 4. Texture acquisition and surface evidence

- [x] 4.1 Adapt local VPK discovery and `extract_cs2_textures.py` output into manifest asset records with source, map class, path, and IP boundary metadata.
- [x] 4.2 Define packed-channel decoding, color spaces, UV orientation, texture dimensions, missing-channel derivation, scalar/map metalness, and authored-texture rejection conditions.
- [x] 4.3 Add a map adapter that maps classified color, normal, roughness/metalness, mask, height, and AO assets into independent `referencePbr.maps` channels.
- [x] 4.4 Connect `delight_albedo.py`, camera evidence, and texture/projection provenance to the manifest without making local extraction a required dependency.
- [x] 4.5 Add tests for successful map classification, missing VPK/tool fallback, gitignored output enforcement, and incomplete-map validation.

## 5. Geometry family registry

- [x] 5.1 Define the family-adapter interface for component tree, subtype key, topology, painted regions, material assignments, feature targets, attachment rules, and review viewpoints.
- [x] 5.2 Replace the single CS2 knife-shaped template path with a registered, fixture-backed knife adapter that preserves observed blade/edge/spine, grip, guard/quillon, fastener, and pommel details.
- [x] 5.3 Add explicit unsupported-family/subtype responses for pistol, rifle, SMG, sniper, heavy, glove, and unknown knife subtypes; defer their adapters to separate changes.
- [x] 5.4 Add family-selection and backwards-compatibility tests proving unsupported families cannot fall back to the knife tree and generic object/character fixtures remain unchanged.

## 6. Spec and finish-route integration

- [x] 6.1 Make `new_pre_spec_assessment.py` consume the manifest, preserve CS2 collection evidence, and carry item family, exactness tier, route, and confidence into the assessment.
- [x] 6.2 Make `new_sculpt_spec.py` select the knife adapter and map manifest painted/unpainted regions, finish style, wear, paint seed, and local detail evidence into the spec.
- [x] 6.3 Add explicit route/tier selection for `reference-projection`, `authored-texture`, and `procedural-finish`, with deterministic request-input/fallback semantics.
- [x] 6.4 Extend sculpt validation to reject missing adapters, missing projection inputs, missing independent texture channels, invalid exactness claims, and unavailable environments for view-dependent finishes.
- [x] 6.5 Add integration tests for image-only Doppler/Fade, metadata-assisted wear, authored-texture map wiring, procedural fallback, and route/tier separation.

## 7. Projection, generator, and runtime build

- [x] 7.1 Create `runtime/cs2-preview/` with pinned Three.js/TypeScript dependencies, renderer entry point, manifest/spec loader, and commands for preview, fixed-view capture, and two orbit captures.
- [x] 7.2 Make the projection descriptor consume manifest camera/de-lit/source-image records and return deterministic request-input/fallback results when prerequisites are absent.
- [x] 7.3 Implement the runtime projective texture shader, UV render-target bake, coverage mask, output ownership, and manifest review-artifact update.
- [x] 7.4 Add a headless/browser smoke test that loads the generated knife factory, renders the fixed view and two orbits, and verifies baked output/coverage metadata.
- [x] 7.5 Update the Three.js generator to consume knife geometry, region assignments, independent reference maps, procedural fallback, environment setup, and exactness metadata.
- [x] 7.6 Add an end-to-end generated TypeScript fixture for the reference-projected knife, verifying material channels and environment setup.

## 8. Review gates and documentation

- [x] 8.1 Extend stage 4 review inputs and reports with family identity, painted-region correctness, projection coverage, exactness tier, per-region confidence, approximation notes, and versioned review-scene metadata.
- [x] 8.2 Make calibrated multi-angle non-degeneracy, critical silhouette, finish/material response, and identity-detail failures blocking for the knife pipeline.
- [x] 8.3 Add offline end-to-end manifest tests and browser-backed end-to-end tests for image-only, metadata-assisted, authored-texture fixture, and explicit procedural fallback routes.
- [x] 8.4 Update `SKILL.md`, CS2 intake/build guidance, CLI documentation, and examples to document the manifest workflow, evidence tiers, knife-first support boundary, runtime host, IP boundary, and honest single-view limitations.
- [x] 8.5 Run the full test suite, triage the existing reference-admission baseline failure separately, and manually verify the committed knife fixture through `runtime/cs2-preview` with fixed/orbit screenshots and a review artifact.
