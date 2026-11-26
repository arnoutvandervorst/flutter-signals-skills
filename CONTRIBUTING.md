# Contributing

## Adding a skill

1. `skills/<kebab-name>/SKILL.md` with frontmatter `name` (= directory) and a
   `description` that says what it governs **and when to use it** ("Use when …") — the
   description is what makes the agent load it.
2. Body: non-negotiable rules, each with its *why*; anti-patterns; a definition of done;
   the reference implementation path in the reference app.
3. Only general rules belong here. App-specific domain rules live in the app's own
   `.claude/skills/`.
4. Side-effecting runbooks get `disable-model-invocation: true`.
5. Add it to the table in `README.md` and the routing table in
   `skills/signals-flutter-conventions/SKILL.md`.

## Adding a check

1. Add a `Rule` to `RULES` in `scripts/flutter_signals_check.py`: a stable `id`, a `why`
   the agent can act on, a narrow `scope`, and a regex anchored to a structure (an import,
   a call shape) — or a `file_check` for whole-file rules.
2. Add an offender to `fixtures/app/` and an `expect` line to `scripts/test_checks.sh`
   (update the expected total).
3. Run it against the reference app; fix or baseline what it finds before shipping.
   A rule with false positives gets disabled — keep only textually decidable promises.

## Before committing

`scripts/test_checks.sh` and `claude plugin validate --strict` on the manifest, the
marketplace and `skills/`.

## Releasing

Every change that reaches users gets a version:

1. Bump `version` in `.claude-plugin/plugin.json` (patch for a fix, minor for a new rule,
   check or runbook, major when a check starts refusing code it used to allow).
2. Add a `## [x.y.z] - <date>` section at the top of `CHANGELOG.md`.
3. Commit, tag `vx.y.z` and push the tag.
4. `gh release create vx.y.z --title "x.y.z: <summary>" --notes-file <that section>`.

Skills, checks and examples stay app-neutral: no app names, hosts, addresses or personal
paths. Point to the app's own `OPERATIONS.md` / release docs for its scripts.
