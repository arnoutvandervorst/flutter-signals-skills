---
name: update-deps
description: Manual runbook to check, apply and explain pub + npm package updates in one Flutter project or all of them (`/flutter-signals:update-deps [project…|all]`) — takes the in-range updates, verifies, and reports every blocked or major update with the reason and what unblocks it.
disable-model-invocation: true
---

# Update dependencies

The mechanical part is `scripts/deps_update.py` in this plugin. It classifies every outdated
package per root (the Flutter app plus each `package.json` up to one level deep), takes the
in-range updates and asks the solvers why the rest does not resolve. Your job is the part a
solver cannot do: find out who has to move, and whether the native build agrees.

```bash
S="${CLAUDE_PLUGIN_ROOT}/scripts/deps_update.py"
python3 "$S" [PROJECT …]                        # report only (default: the current dir)
python3 "$S" --all ~/Projects                   # every project with a pubspec.yaml
python3 "$S" --apply --verify [PROJECT …]       # in-range updates + analyze/test/lint/build
python3 "$S" --apply --majors --native PROJECT  # try majors + iOS SPM + Android build
```

## Steps

1. **Scope.** Arguments are project paths; `all` means `--all ~/Projects`. Without
   arguments: the current project.
2. **Report first.** Run without `--apply`. If it flags lockfiles that were already dirty,
   say so: the update would mix with someone's uncommitted work.
   The report opens with the **Flutter SDK**: installed version and channel, a newer release
   on that channel, and the latest stable. On beta/master every project line says whether
   stable meets its `environment:` floor. For a newer patch release it lists the commits
   since the installed revision (cherry-picks): name the ones that touch this project's
   platforms or tooling (Gradle, iOS/macOS, native assets, web). Never run `flutter upgrade` or `flutter channel`
   yourself: the SDK is shared by every project on the machine. Report it and ask.
   **CI must run the same SDK.** For every project in scope, find where CI pins Flutter
   (`FLUTTER_VERSION` in a runner Dockerfile, `flutter-version` in a workflow, `.fvmrc`,
   `.tool-versions`) and compare it with the installed SDK. Report a difference even when
   nothing else is updated: tests can pass locally and fail in CI on the older SDK alone
   (one app, 2026-11: the Mac on 3.51, the runner on 3.49, CI red for days on one test).
   When the user upgrades the SDK, the pin moves in the same change and the runner is
   rebuilt (for example `ops/ci_runner/Dockerfile`, then `make nuc-runner`; see the project's
   OPERATIONS.md). Rebuilding a runner is shared infrastructure: ask first.
2b. **Own packages first.** Shared code lives in the owner's git packages (`auth_engine`,
   `signals_kit`, `invite_kit`, … in `~/Projects/<name>`; git dependencies pinned by tag). Their
   `pubspec.yaml` constraints hold the apps' nested packages (Firebase, `mobile_scanner`,
   `dlibphonenumber`, …): an app cannot move such a package past its package's constraint.
   The report lists each app's own packages (pinned `ref`, newest tag, untagged local commits)
   and marks a blocked item whose solver chain names one ("held by own package X").
   Order: run the script on every package (`--all` puts them first), take the updates there,
   `flutter analyze` + `flutter test` in the package, commit, tag (`vX.Y.Z`, patch for in-range,
   minor for a constraint bump) and push the tag (each its own yes from the user); then raise
   `ref` in every app that uses it and update the apps. A package's `pubspec.lock` is not
   committed, so the lock the apps resolve is what counts: verify in the apps.
   A package names no app in its code, docs or commits (they are public).
3. **Apply in range.** `--apply --verify`. These are lockfile-only changes, so they need no
   confirmation. Verification can take minutes per project; run it where the user can watch
   it if the project's instructions ask for that (a terminal pane the user can see). If verification
   fails, show the failing output and leave the change in place for the user to judge.
   Never revert silently.
4. **When a package with native code moved** (any Firebase/FlutterFire, `google_sign_in`,
   `image_picker`, `camera`, …), also run `--native`. Pub never sees Swift Package Manager
   or Gradle. That caused the FlutterFire 5 rollback: Dart resolved, the Swift packages did
   not, because FlutterFire 5 needs GoogleSignIn-iOS 10 and the `Package.swift` of
   `google_sign_in_ios` 6.3.8 declares `from: "9.0.0"` (below 10).
   iOS is **SPM only**: never add a Podfile, never run `pod install`, never suggest CocoaPods
   as a workaround. A project the script flags with `ios/Podfile` gets migrated, not patched.
   An Android failure that passes on the script's retry was stale Gradle state, not the update.
5. **Explain every blocked item.** The script prints the solver's chain. Turn it into who
   holds the package and what unblocks it:
   - **Pub chain** ("X depends on Y ^4"): X is the holder. Check whether X already has a
     release that allows the new Y (`curl -s https://pub.dev/api/packages/X`). If not,
     look for the upstream PR or issue (`gh search prs --repo <owner>/<repo> "<Y> <major>"`)
     and report its state (open, review, merged but unreleased).
   - **SPM** ("Dependencies could not be resolved because …"): open the plugin's
     `ios/<plugin>/Package.swift` in `~/.pub-cache/hosted/pub.dev/<plugin>-<version>/`. The
     `.package(url:, from:)` / `.upToNextMajor` line that caps the native SDK names the
     holder. Look for its upstream PR the same way.
   - **npm peer** (`peer typescript@"<6.1.0" from typescript-eslint`): run
     `npm view <holder>@latest peerDependencies` (and `@next`). If no release allows it,
     look for the upstream issue.
   - **SDK pins** (`flutter_test from sdk depends on test_api …`, `flutter from sdk depends
     on material_color_utilities …`): no action. They move with the next Flutter SDK.
   - **Transitive items with the same holder**: report them once under the direct package
     that causes them (`build` + `build_config` → `build_runner`).
6. **Global Firebase CLI.** The `firebase` command most deploy and emulator scripts call is the
   global `firebase-tools`, which no lockfile covers. Once per run (not per project): compare
   `npm ls -g firebase-tools --depth=0` with `npm view firebase-tools version`, and when it is
   behind run `npm install -g --allow-scripts=protobufjs,re2 firebase-tools@latest`, then
   `firebase --version` to confirm. Without `--allow-scripts` npm skips those two install
   scripts and `re2` (native regex module) is not built (owner allowed both, 2026-11-05).
   A new major changes CLI behaviour the deploy scripts rely on: read its release notes
   (https://github.com/firebase/firebase-tools/releases) and name the breaking changes in the
   report. A project that pins `firebase-tools` in a `package.json` (e.g. a rules-test root)
   shows up as an npm root above; that pin moves only with the user's yes.
7. **Majors.** Never take them silently. For each family (FlutterFire, go_router, …), read
   the changelog's breaking changes. Only after the user agrees, try
   `--apply --majors --native` on a branch. When it fails, restore `pubspec.yaml` +
   `pubspec.lock` (+ `ios/Runner.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved`)
   to their committed state. Report the failure as
   a blocker with its native reason.
8. **Report.** First the SDK line: channel, newer release (or up to date), and on beta
   whether stable would do. Then the global Firebase CLI: old → new version, or up to date. Per project: what was updated and the verification result.
   Then one table across all projects:

   | Package | Current → latest | Held by | Why | Unblocks when |
   |---|---|---|---|---|

   Name the upstream link for every row. Give one line per project that is up to date.
9. **Never commit.** Lockfile changes wait for the user's "commit". Then commit them per
   project, separately from feature work, naming what stayed blocked and why.

## Definition of done

- [ ] Every project in scope: updated list + verify result (or the reason it was skipped).
- [ ] Flutter SDK: channel, newer release, stable fit reported; no SDK upgrade without the user.
- [ ] CI's Flutter pin equals the installed SDK in every project (or the difference is reported);
      after an SDK upgrade the pin is bumped and the runner rebuilt.
- [ ] Global `firebase-tools` on the latest release (`npm install -g --allow-scripts=protobufjs,re2`), version reported.
- [ ] Own packages updated, tagged and pushed before the apps; every app's `ref` on the newest tag
      (or the gap reported); items held by an own package fixed there.
- [ ] Every blocked item: holder, reason and upstream link. Native majors tried only with
      the user's agreement.
- [ ] Nothing committed or reverted without the user.
