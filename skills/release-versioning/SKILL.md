---
name: release-versioning
description: Release discipline for a Flutter app shipped to Google Play and the App Store — version <year>.<month>.<sequence>+<build> in pubspec.yaml as the single source of truth, betas bump only the build number (a new version name triggers a fresh Apple beta review), a build number is never reused, a CHANGELOG entry plus per-locale store notes before any lane runs, production promotes the tested artifact and never rebuilds, Android staged rollout and iOS phased manual release, never run the Android and iOS lanes concurrently, backend deploys land before the build that needs them. Use when bumping a version, writing release notes, preparing a beta or production release, or answering "can we ship".
---

# Release versioning

## Non-negotiable rules

1. **Version = `<year>.<month>.<sequence>+<build>`** in `pubspec.yaml` (single source of
   truth; Gradle reads it). The build number always increases and is never reused — both
   stores reject a duplicate, and a failed-looking upload may have landed (check the store
   before retrying).
2. **Betas bump only the build number.** A changed version name is a new version to Apple
   and re-triggers Beta App Review for external testers. The `<sequence>` bumps only for a
   production release; a new month resets it (`<year>.<month>.0`).
3. **No lane runs without a CHANGELOG entry** (engineer-facing, source of truth) and store
   copy derived from it per locale (Play: ≤ 500 characters each).
4. **Production promotes the artifact already on the testing track — never rebuilds.**
   A rebuild is a different binary from the one testers validated.
5. **Android starts at a small staged rollout; iOS uses a phased, manual release** so a human
   picks the moment — which matters when a backend deploy must land first. **Except the
   first public release, which goes to 100% on Android**: a staged first release hands the
   other new installs the older production build, which is below the minimum build, and its
   "please update" screen loops back to the same listing.
6. **Never run the Android and iOS lanes concurrently** (shared build directory races).
7. **Backend first:** functions, indexes and rules that a build depends on are deployed
   before the build ships; raise the minimum supported build when old builds would break.
8. **The minimum-build gate only moves up.** A Remote Config template deploy must carry the
   live `MIN_BUILD_NUMBER` (compare before deploying, or the deploy lowers the gate). The
   client check fails open: no value or no build number is "not outdated".
9. **Lanes guard themselves:** they refuse a version whose `year.month` is not the current
   month, and stop before building when the build's store notes are missing.

## Definition of done

- [ ] Build number bumped (and nothing else, for a beta).
- [ ] CHANGELOG section + store notes present.
- [ ] Backend dependencies deployed; minimum build raised if required.

See the manual runbook `release-beta`; the app's own `CLAUDE.md` / release doc lists its lanes.
Reference: the app's `OPERATIONS.md` (go-live order) and `docs/RELEASE.md`,
`lib/signals/common/remote_config.dart` (`isOutdatedBuild`).
