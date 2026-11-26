---
name: release-beta
description: Manual runbook to ship a beta build of a Flutter app to Play open testing and TestFlight — bump only the build number, write CHANGELOG + store notes, run the lanes one after the other, then promote to external testers after a device check.
disable-model-invocation: true
---

# Release a beta

The app's `CLAUDE.md` / release doc names its lanes, store-notes paths and commit order;
follow it where it differs from the defaults below.

1. Backend first: deploy functions / indexes / rules the build depends on.
2. `pubspec.yaml`: bump **only** `+<build>` (see `release-versioning`).
3. `CHANGELOG.md`: a section `## [<version> (<build>)] - <date>`.
4. Store notes per locale for that build — Play "What's new" ≤ 500 characters, TestFlight
   "What to Test" ≤ 4000. (Typically `android/fastlane/metadata/android/<locale>/changelogs/<build>.txt`
   and `ios/fastlane/metadata/<build>.txt` or `ios/fastlane/metadata/<build>/<locale>.txt`.)
5. Commit (on the owner's word) — before the lanes, or after them as `Release <version>+<build>`.
   A lane that builds from the remote (an Android release on a self-hosted CI runner that
   builds `main`) needs the version and notes pushed first.
6. Android lane, wait for it to finish; then the iOS lane. **Never both at once.**
7. After a device sanity check, release to external testers (a distribute lane, or by hand
   in App Store Connect).
8. Raise the minimum supported build (Remote Config) when older builds would break.
