# nautilus-smart-extractor

Archive extraction productivity suite for GNOME featuring a Nautilus Python context menu extension, redundant folder hierarchy flattener, and background inotify downloads watcher.

## Overview

nautilus-smart-extractor simplifies archive handling on Linux desktops:

1. Nautilus Extension (`extension/extract_to_folder.py`): Adds an "Extract to Folder" context menu entry mimicking 7-Zip/WinRAR desktop behavior.
2. Smart Extraction Engine (`bin/extract-archive`): Detects archive formats (`zip`, `tar.gz`, `tar.xz`, `7z`, `rar`) and automatically prevents redundant nested directory creation (if the archive already contains a single root folder, it avoids duplicating the directory name).
3. Background Downloads Watcher (`bin/auto-extract-downloads`): Uses inotify to automatically unpack completed archive downloads in the background with zero idle CPU overhead.

## Requirements

- GNOME Files (Nautilus 4+)
- python3-nautilus
- inotify-tools
- Archive backends: `unar`, `p7zip-full`, `tar`, `unzip`

```bash
sudo apt install python3-nautilus inotify-tools unar p7zip-full
```

## Installation

1. Install the Nautilus Python extension:

```bash
mkdir -p ~/.local/share/nautilus-python/extensions
cp extension/extract_to_folder.py ~/.local/share/nautilus-python/extensions/
nautilus -q
```

2. Install extraction binaries:

```bash
mkdir -p ~/.local/bin
cp bin/extract-archive ~/.local/bin/
cp bin/auto-extract-downloads ~/.local/bin/
chmod +x ~/.local/bin/extract-archive ~/.local/bin/auto-extract-downloads
```

3. Enable the background downloads extractor service:

```bash
mkdir -p ~/.config/systemd/user
cp systemd/auto-extract-downloads.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now auto-extract-downloads.service
```

## License

MIT
