---
name: nuc-ci-runner
description: Manual runbook for the self-hosted GitHub Actions runner on the NUC that runs an app's CI and Android release — check that it is online, rebuild it after a Flutter, Android SDK or plugin change, copy the Android signing keys, and start a release or screenshot upload on it.
disable-model-invocation: true
---

# CI runner on the NUC

Each app has its own runner container on the NUC (`<app>-ci-runner`, runner name and label
`nuc`), built from `ops/ci_runner/Dockerfile` and started by `make nuc-runner`
(`scripts/nuc_runner.sh`). The app's `OPERATIONS.md` ("CI on the NUC") is leading where it
differs from this list.

1. **Is it online?**
   `gh api repos/<owner>/<repo>/actions/runners --jq '.runners[]|.name+" "+.status'`
   Offline, or a job that stays queued: go to step 3.
2. **Division of work.** With the runner online, run locally only `flutter analyze` on the
   touched folder and the touched tests, then push; the NUC runs the full CI. Run `make ci`
   on the Mac only when the NUC or the VPN is down, once, at the end. Check that the NUC run
   is green (`gh run list --limit 3`) before deploying or releasing.
3. **Rebuild and restart: `make nuc-runner`** from the Mac, on the LAN or VPN. Needed after:
   - a Flutter bump: change `FLUTTER_VERSION` in `ops/ci_runner/Dockerfile` in the same commit;
   - an Android SDK, NDK or build-tools change;
   - an update of the flutter-signals plugin (the runner mounts a copy of its checker);
   - any change under `ops/ci_runner/`;
   - the runner showing offline on GitHub.
   A first build takes about 15 minutes. The script waits until GitHub reports the runner
   online; if it does not, read `ssh <user>@<runner-host> docker logs <app>-ci-runner`.
4. **Android signing keys** (apps that release from the NUC):
   `scripts/nuc_android_keys.sh [/path/to/play-service-account.json]` copies the upload
   keystore, `key.properties` and the Play key to the NUC (folder 700, files 600). Without
   the Play key only build-only runs work. The keys are never in the repo or in GitHub
   secrets; never print them. `make nuc-runner` keeps the folder.
5. **Android release or store upload on the NUC**. The workflow builds `main`,
   so push the version bump and store notes first:
   - build only: `gh workflow run release-android.yml`
   - upload to Play: `gh workflow run release-android.yml -f upload=true`
   - screenshots / listing texts: `-f screenshots=true` / `-f listing=true`
   Follow it with `gh run watch`. "Missing /opt/secrets/android/…" means step 4.
6. **Android integration gate**: it did not work on the NUC in one app. The emulator exited
   a few seconds into the first test that rendered the app; GPU mode, memory, the Docker
   sandbox and the system image were ruled out. Run `make integration-android` on the Mac.
   `make integration-android-nuc` exists for retrying and needs a pushed branch.
7. **Report**: runner status, what was rebuilt and why, and the result of the run that was
   started.

The runner's registration token and the signing keys are secrets. Pass the token through a
file that is mounted read-only and emptied once the runner is online, not through an
environment variable: `docker inspect` shows environment variables.
