## ADDED Requirements

### Requirement: Knife-specific CS2 reconstruction
The system SHALL select the registered `knife` geometry adapter for a supported knife subtype, and the adapter SHALL define component hierarchy, topology strategy, painted/unpainted regions, material assignments, attachment rules, identity features, and review viewpoints. Unsupported families/subtypes SHALL be rejected before spec generation.

#### Scenario: Knife reconstruction uses knife anatomy
- **WHEN** the manifest resolves to a knife
- **THEN** the generated spec SHALL use knife-specific components and topology rather than a generic box tree, and SHALL expose blade, edge/spine, handle, guard or quillon, fasteners, and pommel features where observed

#### Scenario: Firearm reconstruction does not use a knife template
- **WHEN** the manifest resolves to a pistol, rifle, SMG, sniper, or heavy weapon
- **THEN** intake SHALL return `unsupported-family` and SHALL not generate a knife-shaped spec

#### Scenario: Glove reconstruction is deferred explicitly
- **WHEN** the manifest resolves to gloves
- **THEN** intake SHALL return `unsupported-family` until a fixture-backed glove adapter is activated

### Requirement: Image-matched geometry and surface evidence
The generated spec SHALL represent the identity-defining silhouette, proportions, macro/meso/micro geometry, painted areas, bare-metal areas, decals/stickers, wear, and fine surface details observed in the input views, with each critical detail mapped to a component or material override.

#### Scenario: Critical silhouette mismatch blocks acceptance
- **WHEN** a rendered model fails the family silhouette or proportion threshold at the required review viewpoint
- **THEN** the review gate SHALL reject continuation even if the global visual score passes

#### Scenario: Golden knife thresholds are applied
- **WHEN** the rendered knife is compared in the versioned review scene
- **THEN** silhouette IoU SHALL be at least 0.85, aspect-ratio delta SHALL be at most 0.05, scale delta SHALL be at most 0.08, and every critical feature and annotated surface region SHALL meet its fixture-declared threshold

#### Scenario: Painted and bare-metal boundaries are preserved
- **WHEN** the reference distinguishes painted, anodized, bare-metal, rubber, polymer, fabric, or leather regions
- **THEN** the spec SHALL assign separate region/material evidence and SHALL not apply one finish uniformly across the entire item

### Requirement: Explicit finish and texture route
The system SHALL choose an independent `route` (`reference-projection`, `authored-texture`, or `procedural-finish`) and `exactnessTier` (`image-only`, `metadata-assisted`, or `exact-texture`), and SHALL enforce the evidence required by the selected route.

#### Scenario: Patterned skin uses de-lit reference projection by default
- **WHEN** the target is a specific patterned CS2 skin reconstructed from a reference image
- **THEN** the system SHALL prefer camera matching, de-lighting, projective texturing, UV bake, and rendered comparison over a purely procedural pattern

#### Scenario: Projection route lacks required evidence
- **WHEN** a projection route has no usable camera or de-lit source
- **THEN** validation SHALL return `request-input` by default; only an explicit fallback policy may change the route to `procedural-finish`, preserve the exactness tier, and append a provenance warning

#### Scenario: Authored texture route maps independent channels
- **WHEN** authored maps are available from the user's legal local install
- **THEN** the generated material SHALL decode packed channels where necessary and map albedo, normal, roughness, and metalness independently; AO/height may be derived only when recorded as derived, while missing required channels SHALL prevent an `exact-texture` claim

### Requirement: Physically coherent CS2 material response
The generated model SHALL use independent PBR channels, finish-specific metalness/roughness/clearcoat behavior, wear response, and an environment/tonemapping setup appropriate to view-dependent finishes.

#### Scenario: Doppler-like finish receives environment response
- **WHEN** the selected finish is anodized or anodized-multicolored
- **THEN** the material SHALL use low roughness/high metalness, the configured environment, and filmic/sRGB renderer settings; validation SHALL reject an explicitly missing environment

#### Scenario: Wear is evidence-labeled
- **WHEN** the float is unavailable
- **THEN** wear SHALL be estimated from visible evidence or a documented default and SHALL be marked approximated; when float is supplied, the wear mapping SHALL record the source value and clamp behavior

### Requirement: Observable multi-angle quality gate
The pipeline SHALL render and review at least the required reference-matched view plus two orbit/self-consistency views in a versioned review scene, and SHALL gate acceptance on family identity, silhouette, material/finish, projection coverage, critical details, and non-degenerate 3D form. The review record SHALL include camera, environment hash, exposure, tone mapping, resolution, renderer version, screenshots, metrics, and per-region confidence.

#### Scenario: Flat-card fake is rejected
- **WHEN** an orbit view collapses the item silhouette or exposes a projection-only plane without volume
- **THEN** the multi-angle gate SHALL reject the build as degenerate-view

#### Scenario: Accepted model reports limitations
- **WHEN** all blocking gates pass but hidden regions were inferred from one view
- **THEN** the final review record SHALL include per-region confidence, unseen-region strategy, exactness tier, and remaining approximation notes

### Requirement: Named browser runtime
The system SHALL provide a `runtime/cs2-preview/` browser host that owns Three.js loading, projective texture/UV baking, fixed-view rendering, orbit capture, and headless smoke testing with pinned dependencies.

#### Scenario: Generated knife is rendered through the owned host
- **WHEN** a valid knife spec and manifest are passed to the preview runtime
- **THEN** the host SHALL produce the fixed reference-view render, two orbit renders, a baked texture/coverage result for projection routes, and a machine-readable review artifact
