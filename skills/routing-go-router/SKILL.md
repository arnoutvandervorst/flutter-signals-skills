---
name: routing-go-router
description: Routing in a go_router + signals Flutter app — one router built in lib/signals/common/router.dart that rebuilds on auth/maintenance changes, route names and paths only via RouteData constants from lib/routes/route_data.dart (never raw path strings), redirect logic as a pure tested function, parked deep links through a pending-location signal, UI branching on the app's auth gate variants instead of raw Firebase auth, pushes opened only for the current viewer, StatefulShellRoute tab rules. Use when adding a route or screen, navigating (context.go / push / goNamed), writing a redirect or guard, handling a deep link or push-notification tap, or touching auth-dependent navigation.
---

# Routing (go_router)

## Non-negotiable rules

1. **Routes by constant.** Every route is a `RouteData(name:, path:)` constant in
   `lib/routes/route_data.dart`; navigation uses `context.goNamed(kXRoute.name, …)` /
   `pushNamed`. Never a raw path string in `context.go('/…')`. The one exception is the
   pure redirect and the router itself, which work on paths and may compare against `'/'`.
2. **The router is rebuilt from auth/maintenance signals** and clears the stack on a gate
   change; unauthenticated users are redirected to the root.
3. **Redirects are pure functions** of (gate state, location) → new location or null, with
   unit tests for every branch. No I/O inside a redirect.
4. **Deep links arriving before the gate is ready are parked** in a pending-location signal
   and replayed once the gate resolves — never dropped, never raced. A session that ends
   (sign-out, viewer change) clears the parked location with it.
5. **Branch on the app's auth gate variants** (guest / onboarding / ready / disabled …),
   never on raw `FirebaseAuth` state in widgets.
6. **Push-notification routes are built by one pure function** from the payload and tested
   against the router's real paths (a parity test catches a route that doesn't exist).
7. **A push opens only for the viewer it was sent to.** The payload names its recipient;
   the client drops the tap when `recipientId` ≠ the current viewer, so a stale device token
   never opens another account's screen (`isForCurrentViewer`).
8. **Tabs (`StatefulShellRoute`):** every route below a tab root that should cover the tab
   bar sets `parentNavigatorKey: rootNavigatorKey` (pinned by a route-tree test); tab
   switches go through the shell's own scope (`TabShellScope.open`), not a raw `goNamed`;
   tab roots are keyed by viewer so a new account never sees the previous one's stack.

## Definition of done

- [ ] New route constant; navigation uses it; redirect tests updated.
- [ ] Deep link / push target resolves in a test.

Reference: `lib/routes/route_data.dart`, `lib/routes/redirect.dart`,
`lib/signals/common/router.dart`, `lib/services/remote_message.dart` (push targets,
`isForCurrentViewer`), `lib/presentation/common/tab_shell_scope.dart`,
`test/routes/route_tree_test.dart`, `lib/auth/` (gate),
`lib/signals/common/push_navigation.dart`.
