## ADDED Requirements

### Requirement: Canonical CS2 intake manifest
The system SHALL produce a versioned `cs2-intake.json` manifest (`schemaVersion: 1`) that records source views, admission/probe results, item identity, item family/subtype, finish evidence, asset provenance, exactness tier, route, assumptions, confidence, warnings, and state. The manifest SHALL validate required fields by route, write atomically, preserve unknown fields under an extension namespace, and support `proceed`, `request-input`, `fallback`, and `rejected` states.

#### Scenario: Image-only intake produces a usable manifest
- **WHEN** a valid reference image is supplied without metadata or a local CS2 install
- **THEN** the system SHALL produce a manifest with `exactnessTier: image-only`, a selected item family and finish route, explicit approximations for unavailable float/seed/texture data, and enough references for downstream spec authoring

#### Scenario: Manifest resumes after an optional-stage fallback
- **WHEN** texture acquisition returns a documented fallback
- **THEN** the system SHALL persist the fallback reason and resume from the next stage without changing the evidence tier or deleting prior evidence

#### Scenario: Invalid reference is rejected before CS2 classification
- **WHEN** reference admission or technical probing reports an undecodable, empty, duplicate, or unusable image
- **THEN** the system SHALL stop before spec authoring and return a machine-readable rejection reason

### Requirement: Evidence-based identity resolution
The system SHALL resolve CS2 identity using explicit user metadata first, resolved metadata second, and a classification record third; heuristic detection SHALL only route or raise a candidate signal. The classification record SHALL contain an allowed `itemFamily`, optional `subtype`, confidence, evidence references, and provider/version.

#### Scenario: Heuristic signal is not treated as final identity
- **WHEN** `detect_cs2.py` reports a CS2 candidate but no authoritative family or item classification exists
- **THEN** the manifest SHALL record the candidate signal and SHALL require classification evidence before selecting a family-specific component adapter

#### Scenario: Classification provider is unavailable
- **WHEN** no classification record is supplied or the live provider times out
- **THEN** the system SHALL return `request-input` and SHALL not select a geometry family from heuristics alone

### Requirement: Explicit supported-family boundary
The initial change SHALL activate the `knife` family only. Pistol, rifle, SMG, sniper, heavy, glove, and unknown knife subtypes SHALL return `unsupported-family` or `unsupported-subtype` before spec generation rather than receiving a generic knife tree.

#### Scenario: Non-knife item is rejected explicitly
- **WHEN** the manifest resolves to `rifle`
- **THEN** intake SHALL finish with `unsupported-family`, preserve the classification evidence, and avoid creating a misleading reconstruction spec

#### Scenario: Confident contradiction halts intake
- **WHEN** the declared item class conflicts with an objectness verdict at or above the configured confidence threshold
- **THEN** the pipeline SHALL return `request-input`/halt and SHALL preserve both the declared assumption and the contradictory evidence

### Requirement: Optional metadata and texture acquisition with explicit fallback
The system SHALL optionally resolve paint index, float range, rarity, and image metadata, and SHALL optionally extract local CS2 maps; no-match, ambiguous metadata, missing VPK, missing extractor, or extractor failure SHALL produce an explicit fallback or request-input state rather than a silent guess.

#### Scenario: Ambiguous skin metadata is not guessed
- **WHEN** a metadata query matches multiple records without a unique phase or paint index
- **THEN** the system SHALL stop the metadata resolution step, list candidate identifiers, and require disambiguation or continue in image-only mode

#### Scenario: Local texture extraction degrades safely
- **WHEN** no legal local VPK or `Source2Viewer-CLI` is available
- **THEN** the system SHALL continue with `textureSource: image-only`, mark authored texture exactness unavailable, and keep the failure reason in the manifest

### Requirement: Provenance and exactness claims
The manifest SHALL mark each identity, finish, texture, float, paint seed, and unseen-region decision with provenance and confidence; unavailable values SHALL be represented as unknown or approximated, never invented. `route` and `exactnessTier` SHALL remain independent when a route falls back.

#### Scenario: Missing float and paint seed are transparent
- **WHEN** the reference shows wear or a pattern but no exact float or paint seed is supplied
- **THEN** the manifest SHALL preserve the observed visual evidence, mark the numeric values unavailable, and label derived wear/pattern placement as approximated

#### Scenario: Extracted Valve assets remain local
- **WHEN** authored maps are extracted from a user's local install
- **THEN** the system SHALL write them only under the gitignored texture workspace and SHALL not include them in tracked source or redistributed artifacts

### Requirement: View and input policy
The system SHALL associate each input view with a stable role, path/hash, resolution, coverage, and duplicate status. Single-view intake MAY proceed for the knife only when visible identity features are sufficiently covered and hidden-region inference is recorded; otherwise it SHALL return `request-input`.

#### Scenario: Duplicate or insufficient view coverage
- **WHEN** all supplied views are duplicates or fail the configured resolution/coverage policy
- **THEN** intake SHALL reject or request additional input with a machine-readable reason
