---
name: store-media
description: Manual runbook to produce and publish the media of a Flutter app — store screenshots, demo videos, journey recordings and the private media site — from the demo world on the emulators, regenerating only what changed, then uploading to App Store Connect and Play.
disable-model-invocation: true
---

# Store media

The app's `OPERATIONS.md` and `docs/` (RELEASE, MEDIA, DEMO_VIDEO, DEMO_WORLD) name its scripts,
flags and output folders; follow them where they differ from the defaults below. Read the
header of a script before running it: the flags live there.

These jobs take the whole Mac for minutes. **Run one heavy job at a time, in its own pane, and
run the smallest piece that shows the change.** A full set only when the owner asks for it.

1. **Decide the smallest run.** Which screens, which chapter, which locale changed? Dutch
   first; the second locale only after the first set is approved.
   - Screens: filter to the screens and the account that changed when the script allows it
     (for example `SCREENS_ONLY=<names> ACCOUNTS=<account>`); a second run shortly after, same
     locale, can skip seeding the demo world again (not after a video run that changed it).
     Without a per-screen filter, capture a single shot (prepare / capture one / process).
   - Video: record only the chapter that changed (recordings are kept per chapter, so the
     others are reused), or only re-cut when just the cut list or captions changed.
2. **Check the prerequisites the script names**: the simulator it insists on, `magick`,
   `ffmpeg`, the emulator ports (some apps give media runs their own ports, others use the
   default ports with the demo world). Do not start a media run next to an integration run on
   the same ports.
3. **Run it in a pane** and wait for the exit code. A take or screenshot run that hits its
   time cap is retried once by the script; a second failure is a real failure, read the log.
4. **Look at the result before going on**: open a few of the new images, or a few frames of
   the new chapter. Check the status bar, the locale, and that no debug banner or push
   prompt is in the shot.
5. **Store sets.** Store screenshots have fixed sizes: iPhone 1320x2868, Play 1080x2160.
   Play refuses screenshots longer than 2:1 and takes at most 8 per phone listing.
   Build them from the app screens with the app's store-set script, or let the capture run
   write them directly when it does.
6. **Commit** the screenshot sets that live in git, on the owner's word. Videos stay out of
   git (a GitHub release as storage, or local only).
7. **Upload the screenshots**, after the owner has seen them:
   - App Store: `cd ios && fastlane ios screenshots` (or `bundle exec fastlane …`).
     It needs an editable App Store version with the version name from `pubspec.yaml`.
     **Uploading a locale activates that locale on the version**: its description, keywords
     and support URL must be filled in before the release is submitted.
   - Play: `cd android && fastlane android screenshots locales:nl`, or the release workflow
     when the Play key lives only on the CI runner (`-f screenshots=true`). Play refuses the
     whole upload when one locale has no listing title, so name only locales that have a
     listing.
   - "The caller does not have permission": the Play service account lacks *Manage store presence*.
   - App preview videos go into App Store Connect by hand.
8. **Media site**: `make media-deploy` from the Mac, not from CI, because the videos are
   local. Cloudflare refuses a file over 25 MiB: re-encode it smaller (the app's media
   target usually has a max-size option). A new video must be listed in the site's
   manifest to be published.
9. **Report**: what was regenerated, what was reused, what was uploaded where, and what the
   owner still has to do by hand.
