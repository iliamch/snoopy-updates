# Snoopy updates

Public program-only updates for existing Snoopy Windows and Snoopy Displays installations. No GitHub account or token is required on your PCs. Animation media is not included.

## Add updates to an existing installation

Open [Releases](https://github.com/iliamch/snoopy-updates/releases/latest), download the matching **UpdaterSetup** ZIP, extract it, and run **InstallUpdate.exe** once on each PC. Select the existing Snoopy folder if asked.

- Snoopy Windows: SnoopyWindowsUpdaterSetup-1.2.0.zip
- Snoopy Displays: SnoopyDisplaysUpdaterSetup-1.1.0.zip

Then open Snoopy settings and choose **Check for an update**. Daily background checks are enabled by default and can be turned off. **Update now** installs the offered version; **Keep old** skips its notifications. A manual check can offer it again. Settings, time zone, display preferences, and animations stay in place. Previous program files are backed up inside the installation folder.

## Publishing future updates

Build the matching edition, increase its version, and attach the generated SnoopyUpdate-VERSION.zip or SnoopyDisplaysUpdate-VERSION.zip to a published stable release here. Both editions may share a release. The updater selects the highest matching version among the latest 100 releases, verifies GitHub SHA-256 and package file hashes, and rejects wrong-edition packages and downgrades. A source commit alone does not publish an installable update.

Full installers and source remain in their original private repositories. This feed contains only program update packages and one-time updater setup packages, never personal settings or animation media.
