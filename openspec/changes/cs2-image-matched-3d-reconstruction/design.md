## Context

The repository already has independent CS2-aware pieces: reference admission and probing, heuristic CS2 routing, intake-correctness checks, local CS2 spec search, optional skin metadata lookup, optional VPK texture extraction, CS2 finish profiles, procedural component generation, projection descriptors, and staged visual review. They currently communicate mostly through CLI arguments and ad-hoc JSON files. The result is not a reliable vertical pipeline: a detector has no orchestrator caller, extracted maps are not normalized into `referencePbr.maps`, the projection script does not bake pixels, and the CS2 component tree is effectively knife-shaped.

The design must preserve the image-first promise for the initial knife slice. A reference image plus a deterministic classification record remains sufficient to produce a useful model, while optional metadata and legal local game assets improve exactness. The system must never claim that an unseen side, exact float, paint seed, or Valve-authored texture was recovered when it was not observed or supplied.

## Goals / Non-Goals

**Goals:**

- Establish one manifest-driven contract from reference intake through spec authoring, build, and review.
- Maximize visible agreement with the input image across silhouette, proportions, geometry, painted/bare regions, color, PBR response, pattern, wear, and micro-details.
- Establish a family-adapter boundary and fully implement only the knife adapter in this change; unsupported families must fail explicitly rather than use a knife template.
- Support three explicit evidence tiers: image-only, metadata-assisted, and exact-texture.
- Integrate de-lighting, camera matching, projection, texture channels, environment lighting, and multi-angle validation without silently skipping required evidence.
- Keep all optional acquisition paths offline-capable and IP-safe.
- Provide a named browser runtime and reproducible render-scene contract for the final gate.

**Non-Goals:**

- Recovering hidden geometry or exact back-side textures from a single view without marking them as inferred.
- Redistributing Valve assets or committing extracted textures.
- Building a general-purpose photogrammetry or mesh-extraction system.
- Guaranteeing pixel identity from a baked-lit icon; raw icon projection remains prohibited.
- Replacing the existing generic object/character tracks.

## Decisions

### 1. Use a canonical `cs2-intake.json` manifest

All stages SHALL read/write a versioned manifest containing source views, admission results, identity, family/subtype, finish, route, evidence references, texture provenance, camera/de-light outputs, assumptions, confidence, warnings, and exactness tier. The manifest SHALL define schema version 1, required/optional fields by route, atomic writes, resume behavior, unknown-field policy, and terminal states `proceed`, `request-input`, `fallback`, and `rejected`. Existing standalone tools become adapters around this contract.

Alternative considered: continue passing independent CLI flags and files. Rejected because it permits metadata, texture, and finish decisions to diverge and makes provenance impossible to validate at build time.

### 2. Separate routing signals from authoritative identity

`detect_cs2.py` remains a cheap routing heuristic. The authoritative item family and identity SHALL come from explicit user metadata, resolved metadata, or vision/agent classification, in that precedence order. A confident contradiction from intake-correctness SHALL halt the pipeline with `request-input`.

Alternative considered: make the heuristic detector authoritative. Rejected because aspect ratio and raw byte statistics cannot distinguish a rifle, knife, or non-CS2 object reliably.

### 3. Register geometry families, but ship knife first

Introduce a family registry whose adapters provide component tree, subtype/template key, topology rules, painted/unpainted regions, materials, review targets, and default viewpoints. This change SHALL implement and activate `knife` only. Pistol, rifle, SMG, sniper, heavy, and glove SHALL resolve to `unsupported-family` until separate fixture-backed changes activate them. Unknown knife subtypes SHALL resolve to `unsupported-subtype` rather than a generic tree.

Alternative considered: expand the existing knife template with conditionals. Rejected because it would preserve incorrect topology and surface mapping for firearms and gloves.

### 4. Make finish route and evidence tier explicit

The manifest SHALL carry independent `route` and `exactnessTier` fields. `route` SHALL be one of `reference-projection`, `authored-texture`, or `procedural-finish`; `exactnessTier` SHALL be one of `image-only`, `metadata-assisted`, or `exact-texture`.

- `reference-projection` is the default for matching a supplied patterned reference: solve camera, de-light, project, bake, and review.
- `exact-texture` is selected only when authored maps are acquired from the user's legal local install and mapped to independent PBR channels.
- `procedural-finish` is an explicit fallback or a deliberate live-environment choice.

Missing projection evidence SHALL produce `request-input` by default. An explicit fallback policy may change only the route to `procedural-finish`, must preserve the evidence tier, and must append a provenance warning. Alternative considered: always use procedural CS2 finish profiles. Rejected because procedural Doppler/Fade patterns visibly diverge from the input image.

### 5. Use exactness tiers and provenance instead of silent approximation

Every generated spec SHALL carry `exactnessTier` and per-field `approximated`/`confidence` metadata. Missing float, paint seed, hidden views, or authored maps SHALL produce warnings and review annotations, not fabricated values.

### 6. Own the render runtime and validate before/after generation

Add `runtime/cs2-preview/` as the named browser host. It SHALL pin Three.js and renderer settings, expose commands for preview, projection/UV bake, fixed-view capture, and two orbit captures, and be testable headlessly with Playwright. Validation SHALL reject a manifest/spec when the selected route lacks its required evidence, when an item family/subtype has no adapter, when exact maps are not mapped independently, or when a view-dependent finish has no environment. Stage 4 SHALL additionally check family silhouette, painted-region placement, projection coverage, multi-angle non-degeneracy, and calibrated critical feature scores.

The review scene SHALL be versioned and record camera, object transform, environment hash, exposure, tone mapping, output resolution, background, and renderer version. The initial golden knife fixture SHALL calibrate and freeze thresholds before CS2 gates become blocking: silhouette IoU >= 0.85, aspect-ratio delta <= 0.05, scale delta <= 0.08, every critical feature at or above its declared threshold, all annotated painted-region masks passing their threshold, and no degenerate orbit view. Color/pattern/wear thresholds SHALL be stored per annotated region in the golden fixture rather than left as caller-supplied prose.

### 7. Define the classification boundary

The live vision/agent layer SHALL emit the same deterministic classification JSON accepted by the CLI. It SHALL contain `itemFamily`, optional `subtype`, optional item/skin identity, confidence, evidence references, and a provider/version. Missing or timed-out classification SHALL produce `request-input`; heuristic detection alone SHALL never select a geometry adapter.

### 8. Keep acquisition optional and local

Metadata lookup may use a pinned external index, but the default path cannot require network access. VPK extraction SHALL remain best-effort, write only to gitignored `cs2_textures/`, and return an explicit fallback manifest state when the VPK or extractor is unavailable.

### 9. Reconcile multi-view ownership

The existing `multi-view-reference-input` proposal owns generic view roles and view association. This change SHALL consume that contract rather than redefine it; CS2 adds only family-specific minimum coverage and hidden-region confidence rules. A single knife view may proceed when visible identity features pass the fixture policy; otherwise the manifest SHALL enter `request-input`.

## Risks / Trade-offs

- [Single-view ambiguity] → Record per-region confidence and unseen-region strategy; request additional views when hidden geometry materially affects the target.
- [Family coverage increases scope] → Use a registry contract and implement family adapters independently, with knife as the first vertical fixture and explicit gaps for unsupported subtypes.
- [Projection remains runtime-heavy] → Keep the Python stage deterministic and descriptor-based, but make the runtime bake a required, observable build step for the projection route.
- [Texture/IP risk] → Keep extracted assets outside tracked source, validate paths, and never embed or redistribute Valve pixels.
- [Metadata drift] → Support pinned local indexes and record source URL/commit in manifest provenance.
- [False confidence from visual similarity] → Treat deterministic gates and critical feature review as acceptance criteria; do not allow a global score to hide a wrong identity-defining feature.

## Migration Plan

1. Add manifest schema and adapters without changing generic object behavior.
2. Add the orchestrator and preserve existing CLIs as individually testable commands.
3. Add the rights-safe knife golden fixture, named browser runtime, review-scene preset, and knife adapter.
4. Connect texture-map normalization and projection runtime inputs to generated specs.
5. Enable the new CS2 gates in staged mode, calibrate against positive/negative renders, then make them blocking for the knife pipeline.
6. Add future family adapters only through separate fixture-backed changes.

Rollback is configuration-level: invoke the existing standalone stage commands and omit the new CS2 orchestrator/manifest. No existing generic spec schema needs destructive migration.

## Open Questions

- Is `assets/knife_reference/knife_front.png` rights-safe and suitable as the committed golden fixture, or must a new fixture be supplied?
- Which exact projection implementation should the new `runtime/cs2-preview/` host use: a custom Three.js shader or a pinned projective-material library?
- Which additional views, if any, are available for the golden knife target? A single view may proceed only with explicit hidden-region confidence.
