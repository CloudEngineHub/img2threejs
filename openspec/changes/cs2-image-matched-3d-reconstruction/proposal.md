## Why

The current CS2 support contains useful but disconnected pieces: heuristic intake, optional metadata lookup, local texture extraction, CS2 finish profiles, procedural geometry, projection descriptors, and visual review gates. Because these pieces do not share one item contract or an orchestrated execution path, the system can generate a valid spec while still using the wrong item family, approximating the finish unintentionally, or silently losing exact texture evidence.

This change creates a complete, evidence-driven vertical path for a CS2 knife from an input image to a reviewable Three.js model. “Complete” means the path is executable and measurable; it targets maximum observable agreement with the supplied image for silhouette, proportions, geometry, painted and bare-metal regions, color, material response, pattern, wear, and fine identity details, while explicitly reporting what a single view cannot prove. Other CS2 families are follow-up adapters, not silently supported by the knife path.

## What Changes

- Add a canonical `cs2-intake.json` manifest that carries admitted references, item-family classification, identity metadata, finish evidence, acquired maps, camera/de-light assets, assumptions, confidence, warnings, and exactness tier across all stages.
- Add an orchestrated CS2 intake path that connects reference admission, technical probing, CS2 routing, objectness/intake correctness, optional skin metadata, optional local VPK texture extraction, and image-first fallback behavior.
- Add explicit exactness tiers (`image-only`, `metadata-assisted`, and `exact-texture`) so generated output cannot imply an exact paint seed, float, or Valve texture when those inputs are unavailable.
- Add a family-adapter boundary with a fully implemented knife adapter in this change; pistol, rifle, SMG, sniper, heavy, and glove adapters remain unsupported until they have their own fixtures and gates.
- Connect the selected geometry family and painted/unpainted surface map to the CS2 finish material, projection/de-lighting workflow, texture-map channels, environment setup, and generated Three.js factory.
- Turn the projection descriptor into a validated build input: projection routes require camera/de-light evidence and record unseen-region confidence; procedural routes remain an explicit fallback.
- Extend validation and review to gate item-family correctness, projection coverage, material-channel provenance, multi-angle shape integrity, and calibrated finish/wear fidelity before accepting the model.
- Add a named browser runtime and reproducible review-scene preset that owns GPU projection, UV baking, render capture, and orbit capture.
- Consume the generic view-role and view-association contract from `multi-view-reference-input`; add only CS2-specific coverage and hidden-region rules here.
- Preserve the existing IP boundary: extracted Valve textures remain local under gitignored `cs2_textures/` and are never committed or redistributed.

## Capabilities

### New Capabilities

- `cs2-item-intake`: Canonical CS2 intake manifest, identity resolution, evidence provenance, exactness tiers, and graceful fallback orchestration.
- `cs2-image-matched-reconstruction`: Knife-first image-matched surface/finish reconstruction, projection and PBR integration, and quality-gated Three.js output; future families must enter through separate fixture-backed adapters.

### Modified Capabilities

- None. No existing OpenSpec capability requirements are present; this change introduces the first formal CS2 reconstruction contracts.

## Impact

- Affected code: `forge/stage1_intake/`, `forge/stage2_spec/`, `forge/stage3_build/`, `forge/stage4_review/`, and the CS2 intake/build guidance under `grimoire/` and `SKILL.md`.
- New pipeline boundary: a manifest-driven CS2 orchestrator and schema shared by intake, spec authoring, texture acquisition, projection, generation, and review.
- New geometry/material contracts: item-family registries, painted-region maps, exactness/provenance metadata, and projection requirements.
- Tests will add end-to-end offline fixtures for image-only, metadata-assisted, and texture-extraction fallback paths, plus family-specific validation and review-gate failures.
- No required network service is introduced. Network metadata lookup and local Source 2 extraction remain optional; the default knife path works from a reference image plus a deterministic classification record. A render-capable browser runtime is required for the final fidelity gate.
