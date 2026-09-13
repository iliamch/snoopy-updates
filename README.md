# Snoopy updates

Public program-only updates for existing Snoopy Windows and Snoopy Displays installations. No GitHub sign-in or token is required.

## Current versions

- Snoopy Windows **1.3.0**
- Snoopy Displays **1.2.0**

Both include Repeat, Span (Fit/Fill), and Rotate screens every 30 minutes. Rotate shows animation and clock on one selected monitor, keeps the others black, then moves playback to the next. Every new screensaver session starts on the primary selected display. Spanning and rotation use one video player. Existing settings, time zone, weather and animations are preserved. Repeat remains the default.

## Update an existing PC

Open Snoopy settings > Check for an update > Update now. Keep old skips that version's notifications; a manual check can offer it again. Daily checks can be disabled.

If the old app has no updater, open [Releases](https://github.com/iliamch/snoopy-updates/releases/latest), download the matching **UpdaterSetup** ZIP, extract all files and run **InstallUpdate.exe** once. Select the existing Snoopy folder if asked. Program-only ZIPs do not include animation media and are not full fresh installations.

Full installers and source remain in the original private repositories. This public feed never includes animation media, personal settings or credentials.

## Publish future updates

Increase the edition's version, build it, and attach its generated `SnoopyUpdate-VERSION.zip` or `SnoopyDisplaysUpdate-VERSION.zip` to a published stable release here. Both editions can share a release. The updater selects the highest matching version among the latest 100 releases, verifies GitHub SHA-256 and individual payload hashes, and rejects wrong-edition packages and downgrades. A source commit alone does not publish an installable update.
