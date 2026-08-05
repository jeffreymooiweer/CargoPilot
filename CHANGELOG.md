# Changelog

All notable changes are documented here, following [Semantic Versioning](https://semver.org/).

## [1.30.1] — 2026-08-05

A release-metadata and documentation cleanup following v1.30.0.

### Fixed

- Synchronise the frontend lockfile version with the canonical application version before a release tag is created.
- Restore the changelog to one continuous file; the temporary archive through v1.29.5 is merged back before tagging.
- Update the dangerous-goods coverage assessment: a missing IATA Q calculation is no longer silent since v1.30.0, although n and M still require manual input because CargoPilot does not contain IATA quantity tables.

### Changed

- Release preparation now normalises derived metadata before tagging, preventing the application version and npm lockfile from drifting apart again.
- LQ/EQ application is documented as the next data-supported dangerous-goods priority.

## [1.30.0] — 2026-08-05

The compliance boundary, authentication boundary and build boundary are now explicit instead of relying on the browser or deployment convention to do the right thing.

### Fixed

- **The IATA compliance contract now uses one canonical profile name.** `IATA_DGR` is accepted end to end by the wizard, API and calculation engine. The previous `IATA` value remains a temporary compatibility alias, while unknown profiles still fail with HTTP 422.
- **An absent IATA Q calculation no longer looks like approval.** Compliance results say whether Q was checked, incomplete, exceeded or not checked, and the panel warns when all-packed-in-one may apply but n/M data is absent.
- **Changing a password now ends every existing session for that user.** Tokens carry a one-way fingerprint of the current password hash; after a password change old cookies no longer authenticate and the current cookie is cleared.
- **Interrupted export cleanup covers the formats CargoPilot actually creates.** PDF, ZIP, XLSX and temporary files are removed case-insensitively at startup; one undeletable file no longer stops the rest, and unrelated files and directories are untouched.

### Added

- **Strict authentication and administrator safety rules.** Login cookies automatically use `Secure` for HTTPS or trusted `X-Forwarded-Proto=https`, with `COOKIE_SECURE` as an explicit override. Roles are limited to `admin` and `user`; an administrator cannot remove their own administrator access or remove the last active administrator.
- **Bounded spreadsheet and remap imports.** Raw uploads are limited to 10 MB, imports to 20,000 rows, 100 columns and 10,000 characters per cell, and XLSX archives to 50 MB after decompression. The limits apply to wizard and equipment imports and nested remap JSON.
- **Executable API contract coverage for dangerous goods.** FastAPI integration tests cover air and multimodal wizard profiles, the legacy IATA alias, unknown profiles and Q-status behaviour.

### Changed

- **Production dependencies are now audited and reproducible.** Docker uses Node 22 and `npm ci`; Python runtime packages are separated from pytest-only dependencies; `pip check`, version consistency and a blocking `npm audit --omit=dev --audit-level=high` run in CI.
- **The frontend moved to React 19.2.8 and React Router 8.3.0.** This removes the vulnerable Router 7 dependency chain while retaining the existing wizard behaviour and frontend test suite.
- **Pull-request Docker builds prove both AMD64 and ARM64 images without publishing them.** Release and main builds retain the publishing path.

### Tests

- The combined release was validated with backend tests, frontend tests, TypeScript and Vite build, production dependency audit, Python dependency validation, version consistency and a multi-architecture Docker build.

## Previous releases

The complete changelog through version 1.29.5 is preserved in [CHANGELOG-1.29.5-and-earlier.md](CHANGELOG-1.29.5-and-earlier.md).
