#!/usr/bin/env python3
"""Check, apply and explain package updates for Flutter projects (pub + npm).

Usage:
  deps_update.py [PROJECT ...]            report only (default: the current directory)
  deps_update.py --all ~/Projects         every Flutter/Dart project one level below DIR
  deps_update.py --apply                  in-range updates: `flutter pub upgrade` + `npm update`
  deps_update.py --apply --majors         also bump pubspec constraints (`--major-versions`)
  deps_update.py --apply --verify         then analyze + test (pub) and lint/build/test (npm)
  deps_update.py --native                 iOS SPM resolve + Android debug build (catches native pins)
  deps_update.py --json                   machine-readable report

Before the projects it checks the installed Flutter SDK (machine-wide, once per run): its
channel, whether that channel has a newer release, and, on beta/master, whether the latest
stable meets each project's `environment:` floor. Report only; it never runs `flutter upgrade`.

Per package root it sorts every outdated package into:
  updated   moved by --apply (lockfile only, unless --majors)
  in-range  newer version inside the current constraint (what --apply takes)
  major     newer version that resolves, but needs a constraint edit in pubspec/package.json
  blocked   newest version does NOT resolve; the reason is the solver's own explanation
            (`pub add --dry-run` chain, `npm install --dry-run` peer conflict)

The solver sees only Dart/JS constraints. A major that resolves can still break the native
build (Swift Package Manager / Gradle pins, e.g. a plugin's Package.swift capping a native
SDK that FlutterFire needs newer): try majors on a branch with --native before calling them
unblocked. iOS is SPM only: a project that still has an ios/Podfile gets flagged.
Own packages (git dependencies, e.g. a shared auth or invite package) are listed per app with
the ref it pins, the newest tag of that repo and, when the package is checked out next to the
app, commits not tagged yet. Their pubspec constraints hold the app's transitive packages: a
blocked item whose solver chain names one is marked to fix in that package (bump, tag, raise
`ref` in every app). Run the packages first, then the apps.
Never touches pubspec.yaml or package.json without --majors; never commits.
Exit code 1 when --verify fails.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path

SKIP_DIRS = {"node_modules", ".dart_tool", "build", ".git", "ios", "android", "macos", "web", "linux", "windows"}


@dataclass
class Item:
    name: str
    current: str
    target: str
    kind: str = ""  # pub: direct / dev / transitive; npm: dependencies / devDependencies
    reason: list[str] = field(default_factory=list)


@dataclass
class Root:
    tool: str  # "pub" or "npm"
    path: str
    updated: list[Item] = field(default_factory=list)
    in_range: list[Item] = field(default_factory=list)
    major: list[Item] = field(default_factory=list)
    blocked: list[Item] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)
    verify: list[tuple[str, bool]] = field(default_factory=list)
    error: str = ""


def run(cmd: list[str], cwd: Path, timeout: int = 900) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)


def ver(entry: dict | None) -> str:
    return (entry or {}).get("version") or ""


# ---------------------------------------------------------------- pub

def is_flutter(project: Path) -> bool:
    return bool(re.search(r"^\s*sdk:\s*flutter\b", (project / "pubspec.yaml").read_text(), re.M))


def pub_outdated(project: Path, pub: list[str]) -> list[dict]:
    res = run(pub + ["pub", "outdated", "--json", "--show-all"], project)
    if res.returncode != 0:
        lines = [l for l in (res.stderr + res.stdout).splitlines() if l.strip() and "Failed to update" not in l]
        raise RuntimeError(lines[-1] if lines else "pub outdated failed")
    return json.loads(res.stdout)["packages"]


def pub_explain(project: Path, pub: list[str], pkg: dict) -> list[str]:
    spec = f"{pkg['package']}:{ver(pkg['latest'])}"
    if pkg["kind"] == "dev":
        spec = "dev:" + spec
    res = run(pub + ["pub", "add", spec, "--dry-run"], project, timeout=300)
    lines = [l.strip() for l in (res.stdout + res.stderr).splitlines()]
    chain = [l for l in lines if re.match(r"(Because|And because|So,? because|Thus|Since)\b", l)]
    return chain or [l for l in lines if l and not l.startswith(("Resolving", "Downloading"))][-3:]


def check_pub(project: Path, args: argparse.Namespace) -> Root:
    pub = ["flutter"] if is_flutter(project) else ["dart"]
    root = Root("pub", ".")
    if pub == ["flutter"] and (project / "ios" / "Podfile").is_file():
        root.flags.append("ios/Podfile present: iOS should resolve through Swift Package Manager, not CocoaPods")
    try:
        try:
            before = {p["package"]: p for p in pub_outdated(project, pub)}
        except RuntimeError as e:
            if not args.apply:
                raise RuntimeError(f"{e} (lockfile out of step with this SDK? `--apply` runs pub get first)")
            run(pub + ["pub", "get"], project)  # e.g. a lockfile written by another Flutter SDK
            before = {p["package"]: p for p in pub_outdated(project, pub)}
        if args.apply:
            cmd = pub + ["pub", "upgrade"] + (["--major-versions"] if args.majors else [])
            res = run(cmd, project)
            if res.returncode != 0:
                root.error = (res.stderr or res.stdout).strip().splitlines()[-1]
        after = pub_outdated(project, pub)
    except (RuntimeError, subprocess.TimeoutExpired, json.JSONDecodeError) as e:
        root.error = str(e).strip().splitlines()[-1] if str(e).strip() else type(e).__name__
        return root

    now = {p["package"]: p for p in after}
    for name, old in before.items():
        new_cur = ver(now[name]["current"]) if name in now else None
        if args.apply and new_cur != ver(old["current"]) and ver(old["current"]):
            root.updated.append(Item(name, ver(old["current"]), new_cur or "(latest)", old["kind"]))

    for p in after:
        cur, upg, res_, lat = ver(p["current"]), ver(p["upgradable"]), ver(p["resolvable"]), ver(p["latest"])
        if not cur:
            continue  # not in the lockfile (e.g. an unused platform package)
        if p.get("isDiscontinued"):
            root.flags.append(f"{p['package']} is discontinued" + (f", replaced by {p['replacedBy']}" if p.get("replacedBy") else ""))
        if p.get("isCurrentRetracted"):
            root.flags.append(f"{p['package']} {cur} is retracted")
        if p.get("isCurrentAffectedByAdvisory"):
            root.flags.append(f"{p['package']} {cur} has a security advisory")
        if lat and res_ and lat != res_:
            root.blocked.append(Item(p["package"], cur, lat, p["kind"]))
        if res_ and upg and res_ != upg:
            root.major.append(Item(p["package"], cur, res_, p["kind"]))
        if upg and upg != cur:
            root.in_range.append(Item(p["package"], cur, upg, p["kind"]))

    if args.explain:
        for item in root.blocked:
            item.reason = pub_explain(project, pub, now[item.name])

    if args.verify:
        root.verify.append(("analyze", run(pub + ["analyze"], project).returncode == 0))
        if (project / "test").is_dir():
            root.verify.append(("test", run(pub + ["test"], project, timeout=3600).returncode == 0))
    if args.native and pub == ["flutter"]:
        # The pub solver never sees Swift packages or Gradle: a plugin that pins a native SDK
        # resolves fine in Dart and fails here.
        if (project / "ios").is_dir() and sys.platform == "darwin":
            # --config-only regenerates FlutterGeneratedPluginSwiftPackage and resolves it
            # (ios/Runner.xcodeproj/.../swiftpm/Package.resolved).
            ios = run(["flutter", "build", "ios", "--config-only", "--no-codesign"], project, timeout=1800)
            root.verify.append(("ios spm", ios.returncode == 0))
            if ios.returncode != 0:
                root.flags.append("ios: " + " | ".join(l.strip() for l in (ios.stdout + ios.stderr).splitlines() if re.search(r"could not be resolved|because|requires|conflict|error", l, re.I))[:600])
        if (project / "android").is_dir():
            apk = run(["flutter", "build", "apk", "--debug"], project, timeout=3600)
            if apk.returncode != 0:
                # A plugin that moved to a new pub-cache path can leave a half-updated
                # incremental Gradle state (classes jar missing the plugin class); the second
                # build repairs it. Only a failure that survives the retry is real.
                apk = run(["flutter", "build", "apk", "--debug"], project, timeout=3600)
                if apk.returncode == 0:
                    root.flags.append("android: first debug build failed on stale Gradle state, passed on retry")
            root.verify.append(("android build", apk.returncode == 0))
            if apk.returncode != 0:
                root.flags.append("android: " + " | ".join(l.strip() for l in (apk.stdout + apk.stderr).splitlines() if re.search(r"What went wrong|Could not resolve|requires|error:", l))[:600])
    return root


# ---------------------------------------------------------------- flutter sdk

RELEASES = "https://storage.googleapis.com/flutter_infra_release/releases/releases_{os}.json"
COMPARE = "https://api.github.com/repos/flutter/flutter/compare/{base}...{head}"


def vtuple(v: str) -> tuple[int, ...]:
    return tuple(int(n) for n in re.findall(r"\d+", v))


def flutter_sdk() -> dict:
    """The installed SDK against the newest stable and beta release. Machine-wide: an
    upgrade moves every project on this machine, so it is reported, never applied."""
    sdk = {"channel": "", "version": "", "dart": "", "revision": "", "latest": {}, "changes": {}, "error": ""}
    try:
        res = run(["flutter", "--version", "--machine"], Path.cwd(), timeout=300)
        local = json.loads(res.stdout[res.stdout.index("{"):])  # a first run prints a banner first
        sdk.update(channel=local.get("channel", ""), version=local.get("frameworkVersion", ""),
                   dart=local.get("dartSdkVersion", "").split(" ")[0], revision=local.get("frameworkRevision", ""))
        feed = RELEASES.format(os={"darwin": "macos", "win32": "windows"}.get(sys.platform, "linux"))
        with urllib.request.urlopen(feed, timeout=30) as r:
            data = json.load(r)
        by_hash = {rel["hash"]: rel for rel in data["releases"]}
        for ch in ("stable", "beta"):
            rel = by_hash.get(data["current_release"].get(ch, ""))
            if rel:
                sdk["latest"][ch] = {"version": rel["version"], "date": rel["release_date"][:10],
                                     "dart": rel.get("dart_sdk_version", "").split(" ")[0], "hash": rel["hash"]}
        latest = sdk["latest"].get(sdk["channel"])
        if latest and sdk["revision"] and vtuple(latest["version"]) > vtuple(sdk["version"]):
            sdk["changes"] = flutter_changes(sdk["revision"], latest["hash"])
    except (OSError, ValueError, KeyError, subprocess.TimeoutExpired) as e:
        sdk["error"] = str(e).strip().splitlines()[-1] if str(e).strip() else type(e).__name__
    return sdk


def flutter_changes(base: str, head: str) -> dict:
    """Commits between the installed framework and the newer release. A patch release on a
    channel is a handful of cherry-picks ([CP-beta], [beta], [CP-stable]) worth reading; a
    jump to a new minor is thousands, so only the count and the link."""
    url = COMPARE.format(base=base, head=head)
    changes = {"url": url.replace("api.github.com/repos", "github.com"), "total": 0, "commits": [], "error": ""}
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.load(r)
        changes["total"] = data.get("total_commits", 0)
        if changes["total"] <= 50:
            for c in data.get("commits", []):
                subject = c["commit"]["message"].splitlines()[0]
                if not re.search(r"Sync engine\.version", subject):  # bookkeeping, no change of its own
                    changes["commits"].append(f"{c['sha'][:9]} {subject}")
    except (OSError, ValueError, KeyError) as e:
        changes["error"] = str(e).strip().splitlines()[-1] if str(e).strip() else type(e).__name__
    return changes


def sdk_report(sdk: dict) -> str:
    out = ["## Flutter SDK"]
    if sdk["version"]:
        out.append(f"  installed: {sdk['version']} ({sdk['channel']}, Dart {sdk['dart']})")
    if sdk["error"]:
        out.append(f"  error: {sdk['error']}")
    latest = sdk["latest"].get(sdk["channel"])
    if latest and vtuple(latest["version"]) > vtuple(sdk["version"]):
        out.append(f"  ! newer {sdk['channel']}: {latest['version']} (Dart {latest['dart']}, {latest['date']})"
                   " — `flutter upgrade` moves every project on this machine")
        ch = sdk["changes"]
        if ch.get("commits"):
            out.append(f"    {ch['total']} commits since the installed revision ({ch['url']}):")
            out.extend(f"      {c[:120]}" for c in ch["commits"])
        elif ch.get("total"):
            out.append(f"    {ch['total']} commits since the installed revision: read the release notes"
                       f" (https://docs.flutter.dev/release/release-notes) and {ch['url']}")
        elif ch.get("error"):
            out.append(f"    changes: {ch['error']} ({ch['url']})")
    elif latest:
        out.append(f"  {sdk['channel']} is up to date")
    elif sdk["channel"] and not sdk["error"]:
        out.append(f"  no release feed for channel {sdk['channel']}")
    stable = sdk["latest"].get("stable")
    if stable and sdk["channel"] != "stable":
        out.append(f"  stable: {stable['version']} (Dart {stable['dart']}, {stable['date']})")
    return "\n".join(out)


def env_floor(project: Path, key: str) -> str:
    """Lower bound of `environment: <key>:` in pubspec.yaml (`^3.13.0` / `>=3.13.0 <4.0.0`)."""
    m = re.search(r"^environment:[ \t]*\n((?:[ \t]+.*\n?)*)", (project / "pubspec.yaml").read_text(), re.M)
    c = re.search(rf"^[ \t]+{key}:[ \t]*['\"]?([^'\"\n]*)", m.group(1), re.M) if m else None
    f = re.search(r"(?:\^|>=)\s*(\d[\w.+-]*)", c.group(1)) if c else None
    return f.group(1) if f else ""


def stable_fit(project: Path, sdk: dict) -> str:
    """On beta/master: does the latest stable satisfy this project's SDK floor?"""
    stable = sdk["latest"].get("stable")
    if not stable or sdk["channel"] in ("", "stable"):
        return ""
    short = []
    for key, have in (("sdk", stable["dart"]), ("flutter", stable["version"])):
        floor = env_floor(project, key)
        # major.minor.patch only: a prerelease floor (3.14.0-10.beta) is met by its release
        if floor and have and vtuple(have)[:3] < vtuple(floor)[:3]:
            short.append(f"{'Dart' if key == 'sdk' else 'Flutter'} {have} < {floor}")
    if short:
        return f"stable {stable['version']} is below the SDK floor ({', '.join(short)}): needs {sdk['channel']}"
    return f"stable {stable['version']} meets the SDK floor: {sdk['channel']} is a choice, not a requirement"


# ---------------------------------------------------------------- npm

def npm_roots(project: Path) -> list[Path]:
    found = []
    for pkg in [project / "package.json", *project.glob("*/package.json")]:
        if pkg.is_file() and not (set(pkg.relative_to(project).parts[:-1]) & SKIP_DIRS):
            found.append(pkg.parent)
    return found


def npm_outdated(d: Path) -> dict:
    res = run(["npm", "outdated", "--json", "--long"], d)  # exit 1 just means "something is outdated"
    try:
        return json.loads(res.stdout or "{}")
    except json.JSONDecodeError:
        raise RuntimeError((res.stderr or res.stdout).strip())


def npm_explain(d: Path, name: str, latest: str) -> list[str]:
    res = run(["npm", "install", f"{name}@{latest}", "--dry-run", "--no-audit", "--no-fund", "--ignore-scripts"], d, timeout=300)
    lines = [re.sub(r"^npm (warn|error|ERR!)\s?", "", l).rstrip() for l in (res.stdout + res.stderr).splitlines()]
    out, grab = [], False
    for l in lines:
        if l.startswith(("Could not resolve dependency", "Conflicting peer dependency")):
            grab = True
            continue
        if grab and (not l.strip() or l.startswith(("ERESOLVE", "Fix the upstream", "While resolving"))):
            grab = False
        if grab and l.strip().startswith("peer ") and l.strip() not in out:
            out.append(l.strip())
    if not out and res.returncode != 0:
        out = [l for l in lines if l.strip()][-2:]
    return out


def check_npm(project: Path, d: Path, args: argparse.Namespace) -> Root:
    root = Root("npm", str(d.relative_to(project)) or ".")
    if not (d / "node_modules").is_dir():
        root.error = "no node_modules (run npm install first)"
        return root
    try:
        before = npm_outdated(d)
        if args.apply:
            res = run(["npm", "update", "--no-audit", "--no-fund"], d)
            if res.returncode != 0:
                root.error = (res.stderr or res.stdout).strip().splitlines()[-1]
        after = npm_outdated(d)
    except (RuntimeError, subprocess.TimeoutExpired) as e:
        root.error = str(e).splitlines()[-1] if str(e) else type(e).__name__
        return root

    for name, old in before.items():
        new = after.get(name)
        if args.apply and old.get("current") and (new is None or new.get("current") != old["current"]):
            root.updated.append(Item(name, old["current"], new["current"] if new else old.get("wanted", ""), old.get("type", "")))
    for name, info in after.items():
        cur, wanted, latest = info.get("current", ""), info.get("wanted", ""), info.get("latest", "")
        if not cur:
            continue
        if wanted and wanted != cur:
            root.in_range.append(Item(name, cur, wanted, info.get("type", "")))
        if latest and latest != wanted:
            reason = npm_explain(d, name, latest) if args.explain else []
            (root.blocked if reason else root.major).append(Item(name, cur, latest, info.get("type", ""), reason))

    if args.verify:
        scripts = json.loads((d / "package.json").read_text()).get("scripts", {})
        for s in ("lint", "build", "test"):
            if s in scripts:
                root.verify.append((s, run(["npm", "run", s], d, timeout=3600).returncode == 0))
    return root


# ---------------------------------------------------------------- report


@dataclass
class GitDep:
    name: str
    url: str
    ref: str
    latest: str = ""  # newest tag on the remote
    local: str = ""  # path of a checkout next to the app
    untagged: int = 0  # local commits after the newest tag
    dirty: bool = False


VERSION_TAG = re.compile(r"^v?\d+(\.\d+)*([-+][0-9A-Za-z.]+)?$")


def git_deps(project: Path) -> list[GitDep]:
    """The git dependencies in pubspec.lock (own packages): name, url and pinned ref."""
    lock = project / "pubspec.lock"
    if not lock.is_file():
        return []
    deps, name, block = [], None, []
    for line in lock.read_text().splitlines() + ["  end:"]:
        m = re.match(r"^  ([A-Za-z0-9_]+):\s*$", line)
        if m:
            text = "\n".join(block)
            if name and re.search(r"^\s+source: git\s*$", text, re.M):
                url = re.search(r'url: "?([^"\n]+)"?', text)
                ref = re.search(r'^\s+ref: "?([^"\n]+)"?', text, re.M)
                deps.append(GitDep(name, url.group(1) if url else "", ref.group(1) if ref else ""))
            name, block = m.group(1), []
        elif name:
            block.append(line)
    for d in deps:
        #* The url comes from the lockfile and the tags from the remote: neither may reach git
        #* as an option (`--` before the url, only plain version tags kept).
        if not re.match(r"^(https://|ssh://|git@|git://)", d.url):
            continue
        res = run(["git", "ls-remote", "--tags", "--refs", "--", d.url], project, timeout=60)
        tags = [t for t in (l.split("refs/tags/")[-1] for l in res.stdout.splitlines() if "refs/tags/" in l)
                if VERSION_TAG.match(t)]
        if tags:
            d.latest = max(tags, key=lambda t: vtuple(t.lstrip("v")))
        local = project.parent / d.name
        if (local / ".git").exists():
            d.local = str(local)
            if d.latest:
                count = run(["git", "rev-list", "--count", "--end-of-options", f"refs/tags/{d.latest}..HEAD"], local)
                d.untagged = int(count.stdout.strip() or 0) if count.returncode == 0 else 0
            d.dirty = bool(run(["git", "status", "--porcelain"], local).stdout.strip())
    return deps


def mark_own_holders(roots: list[Root], deps: list[GitDep]) -> None:
    """A blocked item whose solver chain names an own package is fixed in that package."""
    names = {d.name for d in deps}
    for r in roots:
        for i in r.blocked:
            held = sorted(n for n in names if re.search(rf"\b{n}\b", " ".join(i.reason)))
            if held:
                i.reason.append(f"held by own package {', '.join(held)}: bump the constraint there, test, tag, raise `ref` in every app")


def git_report(deps: list[GitDep]) -> list[str]:
    out = []
    for d in deps:
        line = f"    {d.name} {d.ref or '(no ref)'}"
        if d.latest and d.latest != d.ref:
            line += f" → {d.latest} on the remote (raise `ref`)"
        elif d.latest:
            line += " (newest tag)"
        if d.untagged:
            line += f"; {d.untagged} commit(s) in {d.local} after {d.latest}: tag before an app can use them"
        if d.dirty:
            line += f"; uncommitted changes in {d.local}"
        out.append(line)
    return out


def lock_dirty(project: Path) -> list[str]:
    res = run(["git", "status", "--porcelain", "--", "pubspec.lock", "**/package-lock.json", "package-lock.json"], project)
    return [l[3:] for l in res.stdout.splitlines()] if res.returncode == 0 else []


def fmt(items: list[Item]) -> str:
    """Direct and dev packages by name; transitive ones (platform interfaces that follow
    their plugin, SDK-pinned packages) only as a count."""
    shown = [i for i in items if i.kind != "transitive"] or items
    text = ", ".join(f"{i.name} {i.current} → {i.target}" for i in shown)
    hidden = len(items) - len(shown)
    return text + (f" (+{hidden} transitive)" if hidden else "")


def report(project: Path, roots: list[Root], dirty: list[str], fit: str = "", deps: list[GitDep] | None = None) -> str:
    out = [f"## {project.name}"]
    if fit:
        out.append(f"  sdk: {fit}")
    if deps:
        out.append("  own packages (git):")
        out.extend(git_report(deps))
    if dirty:
        out.append(f"  ! lockfiles already had uncommitted changes before this run: {', '.join(dirty)}")
    for r in roots:
        out.append(f"\n  [{r.tool}] {r.path}")
        if r.error:
            out.append(f"    error: {r.error}")
        if r.updated:
            out.append(f"    updated:  {fmt(r.updated)}")
        if r.in_range:
            out.append(f"    in range: {fmt(r.in_range)}  (--apply)")
        if r.major:
            note = "constraint edit; --majors" if r.tool == "pub" else "range edit in package.json"
            out.append(f"    major:    {fmt(r.major)}  ({note}; check native build)")
        direct = [i for i in r.blocked if i.kind != "transitive"]
        trans = [i for i in r.blocked if i.kind == "transitive"]
        for label, group in (("blocked", direct), ("blocked (transitive)", trans)):
            if group:
                out.append(f"    {label}:")
                for i in group:
                    out.append(f"      {i.name} {i.current} → {i.target}")
                    out.extend(f"        {l}" for l in i.reason)
        for f in r.flags:
            out.append(f"    ! {f}")
        if r.verify:
            out.append("    verify:   " + "  ".join(f"{n} {'ok' if ok else 'FAILED'}" for n, ok in r.verify))
        if not any((r.error, r.updated, r.in_range, r.major, r.blocked, r.flags)):
            out.append("    up to date")
    return "\n".join(out)


def projects(args: argparse.Namespace) -> list[Path]:
    if args.all:
        base = Path(args.all).expanduser()
        #* Packages (no ios/ or android/) first: an app picks up their fix only after a tag.
        return sorted((p.parent for p in base.glob("*/pubspec.yaml")),
                      key=lambda p: ((p / "ios").exists() or (p / "android").exists(), p.name))
    return [Path(p).expanduser().resolve() for p in (args.projects or ["."])]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("projects", nargs="*")
    ap.add_argument("--all", metavar="DIR", help="every project with a pubspec.yaml one level below DIR")
    ap.add_argument("--apply", action="store_true", help="take in-range updates (lockfiles only)")
    ap.add_argument("--majors", action="store_true", help="with --apply: also `pub upgrade --major-versions`")
    ap.add_argument("--verify", action="store_true", help="analyze/test (pub), lint/build/test (npm)")
    ap.add_argument("--native", action="store_true", help="flutter: iOS SPM resolve (--config-only) + Android debug build")
    ap.add_argument("--no-explain", dest="explain", action="store_false", help="skip the dry-run explanations")
    ap.add_argument("--no-npm", dest="npm", action="store_false")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    if args.majors and not args.apply:
        ap.error("--majors needs --apply")

    failed, results = False, {}
    todo = [p for p in projects(args) if (p / "pubspec.yaml").is_file()]
    sdk = flutter_sdk() if any(is_flutter(p) for p in todo) else None
    if sdk and not args.json:
        print(sdk_report(sdk) + "\n", flush=True)
    for project in projects(args):
        if not (project / "pubspec.yaml").is_file():
            print(f"skip {project}: no pubspec.yaml", file=sys.stderr)
            continue
        print(f"… {project.name}", file=sys.stderr)
        dirty = lock_dirty(project)
        roots = [check_pub(project, args)]
        if args.npm:
            roots += [check_npm(project, d, args) for d in npm_roots(project)]
        fit = stable_fit(project, sdk) if sdk and is_flutter(project) else ""
        deps = git_deps(project)
        mark_own_holders(roots, deps)
        failed |= any(not ok for r in roots for _, ok in r.verify)
        results[project.name] = {"path": str(project), "dirtyLockfiles": dirty, "flutterSdk": sdk, "stableFit": fit,
                                 "ownPackages": [asdict(d) for d in deps], "roots": [asdict(r) for r in roots]}
        if not args.json:
            print(report(project, roots, dirty, fit, deps) + "\n", flush=True)
    if args.json:
        print(json.dumps(results, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
