#!/usr/bin/env python3
"""
Nautilus extension: "Extrair para /nome_do_arquivo/"
Adds a context menu item to extract archive files into a dedicated subfolder
named after the archive, mimicking WinRAR / 7-Zip behavior.
"""

import os
import shutil
import subprocess
import threading
from typing import List
import urllib.parse
import gi

gi.require_version('Nautilus', '4.1')
from gi.repository import GObject, Nautilus

ARCHIVE_EXTENSIONS = (
    '.tar.gz', '.tar.bz2', '.tar.xz', '.tar.zst',
    '.tar.lz', '.tar.lzma', '.tar.lzo',
    '.tgz', '.tbz', '.tbz2', '.txz', '.tzst',
    '.zip', '.7z', '.rar', '.tar', '.iso',
    '.deb', '.rpm', '.gz', '.bz2', '.xz',
    '.zst', '.cbz', '.cbr', '.jar',
)

ARCHIVE_MIME_TYPES = {
    'application/zip',
    'application/x-zip-compressed',
    'application/x-7z-compressed',
    'application/x-rar',
    'application/vnd.rar',
    'application/x-tar',
    'application/gzip',
    'application/x-gzip',
    'application/x-bzip2',
    'application/x-bzip',
    'application/x-xz',
    'application/x-compressed-tar',
    'application/x-bzip-compressed-tar',
    'application/x-xz-compressed-tar',
    'application/x-zstd-compressed-tar',
    'application/zstd',
    'application/x-iso9660-image',
    'application/x-archive',
    'application/x-cpio',
    'application/vnd.debian.binary-package',
    'application/x-rpm',
    'application/x-cd-image',
}


def get_clean_stem(filename: str) -> str:
    """Removes extensions including compound extensions like .tar.gz."""
    lower = filename.lower()
    compound_exts = (
        '.tar.gz', '.tar.bz2', '.tar.xz', '.tar.zst',
        '.tar.lz', '.tar.lzma', '.tar.lzo',
    )
    for ext in compound_exts:
        if lower.endswith(ext):
            return filename[:-len(ext)]
    
    base, _ = os.path.splitext(filename)
    return base


def is_archive(file_info: Nautilus.FileInfo) -> bool:
    """Checks if the file is an archive by mime type or extension."""
    if file_info.is_directory():
        return False
    
    mime = (file_info.get_mime_type() or "").lower()
    if (
        mime in ARCHIVE_MIME_TYPES
        or "compressed" in mime
        or "archive" in mime
        or "tar" in mime
        or "zip" in mime
    ):
        return True
    
    name = file_info.get_name().lower()
    return any(name.endswith(ext) for ext in ARCHIVE_EXTENSIONS)


def get_file_path(file_info: Nautilus.FileInfo) -> str:
    """Extracts real filesystem path from Nautilus.FileInfo."""
    loc = file_info.get_location()
    if loc:
        path = loc.get_path()
        if path:
            return path
    uri = file_info.get_uri() or ""
    if uri.startswith("file://"):
        return urllib.parse.unquote(uri[7:])
    return ""


def extract_single_archive(archive_path: str) -> bool:
    """Extracts an archive into a directory named after the archive stem."""
    if not os.path.exists(archive_path):
        return False

    parent_dir = os.path.dirname(archive_path)
    filename = os.path.basename(archive_path)
    stem = get_clean_stem(filename)
    dest_dir = os.path.join(parent_dir, stem)

    os.makedirs(dest_dir, exist_ok=True)

    unar_path = shutil.which("unar")
    sevenz_path = shutil.which("7z")
    file_roller_path = shutil.which("file-roller")

    # 1. Try unar
    if unar_path:
        try:
            res = subprocess.run(
                [unar_path, "-f", "-D", "-o", dest_dir, archive_path],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=300,
            )
            if res.returncode == 0:
                return True
        except Exception:
            pass

    # 2. Try 7z
    if sevenz_path:
        try:
            res = subprocess.run(
                [sevenz_path, "x", "-y", f"-o{dest_dir}", archive_path],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=300,
            )
            if res.returncode == 0:
                return True
        except Exception:
            pass

    # 3. Try file-roller (handles graphical password prompt if protected)
    if file_roller_path:
        try:
            res = subprocess.run(
                [file_roller_path, f"--extract-to={dest_dir}", "--force", archive_path],
                timeout=600,
            )
            if res.returncode == 0:
                return True
        except Exception:
            pass

    return False


def run_extraction_worker(paths: List[str]):
    """Worker thread function to extract all files without freezing Nautilus."""
    success_count = 0
    last_stem = ""

    for path in paths:
        filename = os.path.basename(path)
        last_stem = get_clean_stem(filename)
        if extract_single_archive(path):
            success_count += 1

    # Desktop Notification
    notify_send = shutil.which("notify-send")
    if notify_send and success_count > 0:
        if len(paths) == 1:
            title = "Extração concluída"
            msg = f"Conteúdo extraído na pasta:\n{last_stem}/"
        else:
            title = "Extração concluída"
            msg = f"{success_count} arquivo(s) extraído(s) em suas respectivas pastas."

        subprocess.run([
            notify_send,
            "-a", "Arquivos",
            "-i", "package-x-generic",
            title,
            msg,
        ])


class ExtractToFolderExtension(GObject.GObject, Nautilus.MenuProvider):
    def __init__(self):
        super().__init__()

    def _on_extract_activate(self, menu_item, paths: List[str]):
        threading.Thread(target=run_extraction_worker, args=(paths,), daemon=True).start()

    def get_file_items(
        self,
        files: List[Nautilus.FileInfo],
    ) -> List[Nautilus.MenuItem]:
        if not files:
            return []

        # Check that all selected items are archives
        archive_paths = []
        for f in files:
            if is_archive(f):
                path = get_file_path(f)
                if path:
                    archive_paths.append(path)
            else:
                # If any selected item is not an archive, don't show the option
                return []

        if not archive_paths:
            return []

        if len(archive_paths) == 1:
            filename = os.path.basename(archive_paths[0])
            stem = get_clean_stem(filename)
            label = f'Extrair para "{stem}/"'
            tip = f'Cria a pasta "{stem}/" e extrai o conteúdo dentro dela'
        else:
            label = f'Extrair para pastas individuais ({len(archive_paths)})'
            tip = 'Extrai cada arquivo compactado para uma pasta com seu próprio nome'

        item = Nautilus.MenuItem(
            name="NautilusPython::ExtractToSubfolder",
            label=label,
            tip=tip,
            icon="package-x-generic",
        )
        item.connect("activate", self._on_extract_activate, archive_paths)

        return [item]

    def get_background_items(
        self,
        current_folder: Nautilus.FileInfo,
    ) -> List[Nautilus.MenuItem]:
        return []
