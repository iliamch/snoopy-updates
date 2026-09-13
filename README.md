# Snoopy updates

Public updates for existing Snoopy Windows and Snoopy Displays installations. No GitHub sign-in or token is required.

## Current release

- Snoopy Windows **1.5.1**
- Snoopy Displays **1.4.1**

Includes all 39 idle houses and objects, four resting poses, 84 palettes, and weather effects. Calendar and time-of-day selection follows the chosen time zone; weather uses a fresh matching location. Repeat, spanning, 30-minute screen rotation, travel settings and original animations remain available.

## Update an existing PC

Open Snoopy settings > Check for an update > Update now. The small program package starts an updated helper, which downloads and verifies the required idle media before installing. The one-time media download is about **1.1 GB**. Cancel keeps the old installation. Settings, original Videos, Windows resolution and screensaver registration are preserved. No administrator elevation is requested; company app or network policies can still block the update.

If the old app has no updater button, open [Releases](https://github.com/iliamch/snoopy-updates/releases/latest), download the matching **UpdaterSetup** ZIP, extract it and run **InstallUpdate.exe**. Select the existing Snoopy folder if asked. These small ZIPs update an existing installation; they are not fresh installers.

The shared `SnoopyIdleAssets-1.zip` is downloaded automatically. Do not unpack it manually. This public release contains the shared idle media pack and program updates, but no personal settings or credentials. Application source remains in the original repositories.

## Publish future updates

Publish the generated `SnoopyUpdate-VERSION.zip` and/or `SnoopyDisplaysUpdate-VERSION.zip` to a stable release. Keep the pinned media pack available in a stable release among the newest 100 releases. Changing media requires updating both package and manifest digests in MediaUpdate.cs. The updater validates GitHub digests, the pinned media hash, file hashes and package paths, and rejects wrong editions and downgrades. A source commit alone does not publish an installable update.
