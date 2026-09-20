# Snoopy updates

Public updates for existing Snoopy Windows and Snoopy Displays installations. No GitHub sign-in or token is required.

## Current release

- Snoopy Windows **1.5.5**
- Snoopy Displays **1.4.5**

Multi-monitor playback keeps inactive screens powered with black pixels. Rotation moves the animation inside a stationary desktop window. Videos load paused and start from zero when ready; doghouse timing begins after artwork loading.

Rotation accepts 1–90 whole minutes and waits until a video or doghouse section ends. Doghouse sections accept 1–90 minutes (default 5): the house stays fixed while Snoopy changes pose, followed by one regular animation before another doghouse. Date/time display is optional. Existing travel time zone, weather, calendar, 39 idle houses, original animations, Repeat and Span remain available.

## Update an existing PC

Open Snoopy settings > Check for an update > Update now. Keep old skips that version's reminders; a manual check can offer it again. The updater closes playback/settings and handles windowless older players only in the target installation. Settings, Videos, Windows resolution and screensaver registration are preserved. No administrator elevation is requested; company application or network policies can still block an update.

For manual updating, download the matching **UpdaterSetup** ZIP from [Releases](https://github.com/iliamch/snoopy-updates/releases/latest), extract all files and run **InstallUpdate.exe**. Select the existing Snoopy folder if asked. The smaller SnoopyUpdate / SnoopyDisplaysUpdate ZIPs are intended for the built-in updater. These packages update existing installations; they are not fresh installers.

Missing idle media is downloaded and verified automatically from the existing SnoopyIdleAssets-1.zip in the September 13 release (about 1.1 GB). No new media pack is needed for this version. Cancel keeps the current installation. No personal settings or credentials are included in these packages.

## Publish future updates

Publish the edition's generated update and UpdaterSetup ZIPs to a stable release. Keep the pinned media pack available among the newest 100 releases. The updater validates GitHub digests, pinned media hashes, package paths and payload hashes, and rejects wrong editions and downgrades. A source commit alone does not publish an installable update.

## Ubuntu and Debian Linux

Snoopy Linux **1.0.1** is an initial Linux build for Ubuntu 24.04+ / Debian 12+, on Intel/AMD 64-bit and ARM64. The same installer supports both processors.

Run as your normal desktop user:

```bash
sudo apt-get update && sudo apt-get install -y curl
curl -fL https://github.com/iliamch/snoopy-updates/releases/download/v2026.09.20.2/install-snoopy-linux-1.0.1.sh -o install-snoopy-linux-1.0.1.sh && bash install-snoopy-linux-1.0.1.sh
```

The installer downloads about 2 GB, verifies the application and media, installs native dependencies, adds the Snoopy menu entry and configures the animation folder automatically. Allow 5 GB free during installation. Open `snoopy-linux` afterward. Automatic idle startup is optional in Settings; the desktop lock stays unchanged. See [Linux instructions and desktop compatibility](linux/README.md).

The cloud fix skips damaged opening frames and fades in clean cloud artwork on both platforms. Linux automatic startup, GeoClue permissions and physical multi-monitor behavior depend on the desktop. Native Ubuntu CI checks are attached to this repository for amd64 and arm64.
