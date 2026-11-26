---
name: testing-strategy
description: Test strategy for a signals + Firebase Flutter app — pick the lowest layer that can catch the bug, extract a pure function instead of adding a mock, fromStream/preview seams for state classes, Firebase platform fakes for code touching Firebase singletons, contract tests for anything mirrored between Dart, TypeScript and rules (enums, constants, field names, indexes, backend-owned keys), rules tests both ways, vitest for backend pure functions, emulator integration suites as the local release gate polling with eventually() (never sleep), index tests per query shape (the emulator ignores composite indexes), layout smoke tests, journeys over a seeded demo world, a capped integration run, and never editing a test just to make it pass. Use when writing or fixing tests, adding a contract test, a rules spec or an integration test, or deciding how to test a change.
---

# Testing strategy

## Non-negotiable rules

1. **Lowest layer that can catch the bug.** Pure function → unit test; state class →
   `fromStream` seam test; widget → widget test; rules → rules spec; cross-system flow →
   emulator integration test. Extract a pure function rather than adding a mock.
2. **State classes are tested through their seam** (`XState.fromStream(id, stream)`), all
   four `LoadPhase`s.
3. **Code that touches Firebase singletons** calls the platform-fakes installer in
   `setUpAll` so tests never reach a real backend.
4. **Anything mirrored across Dart / TypeScript / rules gets a contract test**: shared enum
   wire values, numeric constants, field names used in queries, composite indexes for
   compound queries, backend-owned keys vs rules pins. Also: validation rules (a handle's
   pattern and length) in Dart, TS and rules; backend time windows vs what the UI copy
   promises; push targets vs real routes; a list held by rules, Dart, TS and the demo seed;
   and a source scan as a lint-as-test for an upstream bug (no plain `futureSignal`). When a
   contract test fails, fix the side that drifted — not the test.
5. **Rules tests go both ways** for every tier and every backend-owned field.
6. **Backend decisions are pure TS functions with vitest cases**; handlers stay thin.
7. **Emulator integration suites are the release gate, run locally** (both platforms);
   they drive the real endpoints, triggers and rules. They poll with `eventually()` —
   never `sleep`. Emulators on `127.0.0.1`, not `localhost`.
8. **Never edit or weaken an existing test to make it pass** without the owner's
   explicit authorization; if behaviour changed on purpose, say which test changed and why.
9. **A new shared widget joins the gallery test** (light and dark); a new presentation-only
   page gets a pump in the layout smoke test.
10. **The emulator does not enforce composite indexes** (nor their direction): every query
    shape gets an index test next to its feature that finds the matching entry in
    `firestore.indexes.json`.
11. **Integration runs never hang silently.** Time-travel test hooks instead of waiting for
    a schedule; a cap on the whole run (`flutter drive` can hang after "All tests passed!");
    a timeout reports the step it stalled on; native prompts are off in automated runs
    (`kAutomatedRun`).
12. **Journeys walk whole user paths over the seeded demo world**, keep going after a failed
    check, report every failure at the end, and verify what was persisted — they find the
    rules and flow bugs unit tests can't.

## Definition of done

- [ ] New logic has a test at the lowest layer that exercises it.
- [ ] Mirrored values have (or extend) a contract test.
- [ ] Release changes: `make integration` (or the app's gate) green on iOS and Android.

Reference: `docs/TESTING.md`, `test/contract/`, `test/helpers/firebase_platform_fakes.dart`,
`rules_test/`, `integration_test/helpers/firebase_test_harness.dart`, `integration_test/journeys/`,
`docs/DEMO_WORLD.md`, `test/widget/page_layout_smoke_test.dart`, `lib/services/automated_run.dart`.
Also: `test/contract/*_indexes_test.dart`, `integration_test/journey_harness.dart`.
