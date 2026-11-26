---
name: run-integration-gate
description: Manual runbook to run the emulator integration suites (the local release gate) on iOS and Android and interpret failures.
disable-model-invocation: true
---

# Run the integration gate

1. Make sure no emulators are already running on the ports (`lsof -i :8080`).
2. Run the app's gate target (for example `make integration` = iOS simulator + Android AVD,
   starting and stopping the emulators itself). Allow ~15 minutes.
3. Both platforms must end in `All tests passed!`.
4. On a failure, read the first `EXCEPTION CAUGHT` block: an expectation that encodes
   behaviour you changed on purpose is a test to update (say so explicitly); anything else
   is a regression to fix.
5. Never mark a release ready with a red or unrun gate.
