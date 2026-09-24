# Snoopy for Ubuntu and Debian — 1.1.1

For Ubuntu 24.04 or newer and Debian 12 or newer, with Python 3.11+ and Qt 6.4+.
The same **all** package runs on Intel/AMD 64-bit and ARM64. Native Qt and video libraries are installed from your distribution for your processor. No Windows emulator is used.

## Automatic Ubuntu/Debian install

Run these commands as your normal desktop user (the installer requests sudo for packages):

```bash
sudo apt-get update && sudo apt-get install -y curl
curl -fL https://github.com/iliamch/snoopy-updates/releases/download/v2026.09.24.1/SnoopyUbuntuInstall.py -o SnoopyUbuntuInstall.py && python3 SnoopyUbuntuInstall.py
```

This downloads about 4.2 GB of animations, verifies SHA-256 checksums and each extracted media file, installs the correct native dependencies, and configures the media folder automatically. Allow at least 8 GB free during installation. It creates the Snoopy applications-menu entry; run `snoopy-linux` to open settings. Automatic idle playback remains an optional setting. It preserves other Snoopy preferences and the desktop lock configuration.

## Manual install

1. Copy `snoopy-linux_1.1.1_all.deb` and `SnoopyLinux-Media-1.zip` to Linux.
2. In a terminal in that folder, run `sudo apt install ./snoopy-linux_1.1.1_all.deb`.
3. Extract `SnoopyLinux-Media-1.zip` to a permanent folder. Open **Snoopy** from the applications menu. Choose its **Media** folder (containing Videos, IdleAssets and scenes.json), then Save settings and Preview.

An alternative per-user installer is included in `SnoopyLinux-1.1.1.tar.gz`: extract it, install the dependencies below, then run `sh install.sh` without sudo. Application updates after installation do not require administrator access.

Dependencies: `python3-pyqt6 python3-pyqt6.qtmultimedia python3-lunardate qt6-wayland gstreamer1.0-libav gstreamer1.0-plugins-good gstreamer1.0-plugins-bad libxss1 libglib2.0-bin libnotify-bin`. On Ubuntu these are in the normal distribution repositories, including Universe. Older Ubuntu releases are not supported by this package.

## Included

- Original regular videos and all 39 idle houses/objects, four animated Snoopy poses, weather effects and palettes.
- Holiday, season, hemisphere, time-of-day and weather selection, including Halloween, Christmas and New Year.
- IANA travel time zone selector and optional date/time display.
- Weather by city search, or desktop location through GeoClue where available and permitted. If location/weather is unavailable, scenes fall back to date and time.
- Repeat, Span, and Rotate on selected displays. Inactive displays show black pixels. Rotation uses 1–90 whole minutes and waits for the scene to finish. Manual picture resolution in Repeat leaves monitor modes unchanged.
- Doghouse duration in 1-minute steps from 1–90 minutes. The house remains fixed; Snoopy changes pose every 40 seconds. A regular movie separates doghouse sections.
- Corrected cloud opening: damaged source frames are skipped and the clean clouds fade in. Each composed idle frame is presented as a complete image.
- GitHub Check for an update, Update now and Keep old, plus optional daily checks. Linux updates use a separate `SnoopyLinuxUpdate-<version>.tar.gz` asset and never consume a Windows update. Linux packages and the automatic installer are available in the September 20 second release.

## Desktop integration and limits

Manual fullscreen and preview use Qt on X11 or Wayland. Automatic idle launch uses XScreenSaver on X11, or GNOME's Mutter idle interface where it is exposed on Wayland. If that interface is unavailable, use manual playback or an X11 session. Settings changes to automatic startup take effect at next login; status is written to `~/.config/snoopy/automatic-playback.txt` if idle detection is unavailable.

Snoopy is an animation application, **not a security lock screen**. It does not disable or replace Ubuntu/Debian locking. Your desktop's lock/blanking policy can cover or end playback. A power-inhibit request is released on exit; whether it is honored depends on the desktop. Non-GNOME Wayland automatic launch, permission prompts for GeoClue, mixed-DPI multi-monitor layouts and hardware video decoding require testing on the target desktop.

This build's rules, media renderer, movie playback, package integrity and update selection were tested on the Windows development computer using the portable Qt implementation. Native Ubuntu/Debian integration and ARM hardware have not been run here. Use Preview first on each target machine.

Preferences live in `~/.config/snoopy`; user updates in `~/.local/share/SnoopyLinux`. Updates atomically select a verified version directory and retain earlier directories. Media stays separate. Launchers use the user-updated version when present; otherwise the system .deb copy. A distro upgrade of the .deb does not replace a previously selected user update.

## Development / verification

Run `python3 -m unittest discover -s tests -v`. With the media folder available: `python3 main.py --smoke 8 --doghouse --weather cloudy --media /path/to/Media --report cloud-test.json` and `python3 main.py --smoke 8 --media /path/to/Media --report movie-test.json`.

`build_packages.py` creates the portable installer, architecture-independent .deb, and source-only updater tarball. The .deb declares native dependencies. No personal preferences or account credentials are packaged. The media bundle is produced separately from the existing local assets.

References: [Ubuntu Qt Multimedia package](https://packages.ubuntu.com/noble/python3-pyqt6.qtmultimedia), [Debian Qt Multimedia package](https://packages.debian.org/bookworm/python3-pyqt6.qtmultimedia), [Qt video-frame API](https://doc.qt.io/qt-6/qvideoframe.html).

Apple/Peanuts artwork remains the property of its respective owners. No ownership of the original artwork is claimed.

## Doghouse variety

119 validated interaction assets include authored character moments, visitors and four additional generic/environment reaction cycles. A shared timeline alternates sleeping with complete events, returns to sleep between them, avoids repeats, and preserves time/weather/calendar rules. Two damaged visitors remain excluded.

The new idle library downloads as two verified parts and is installed only after all files pass checksum checks. Updating from Linux 1.0.1: reopen Snoopy settings after updating; the new library downloads automatically there. Future updates prepare their media before selecting the new version.

Linux 1.1.1 corrects the pinned media-manifest checksum used by the 1.1.0 installer.
