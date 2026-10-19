"""Small GUI for downloading audio the user is authorized to save."""

from pathlib import Path
import queue
import shutil
import threading
from urllib.parse import urlparse

import tkinter as tk
from tkinter import filedialog, messagebox, ttk


def is_youtube_url(url):
    """Return whether a URL points to YouTube or a YouTube subdomain."""
    try:
        parsed = urlparse(url.strip())
    except ValueError:
        return False
    host = (parsed.hostname or "").lower()
    return (
        parsed.scheme in ("http", "https")
        and (host == "youtu.be" or host == "youtube.com" or host.endswith(".youtube.com"))
        and bool(parsed.path.strip("/"))
    )


def main():
    window = tk.Tk()
    window.title("YouTube Audio Downloader")
    window.resizable(False, False)

    events = queue.Queue()
    url_value = tk.StringVar()
    folder_value = tk.StringVar(value=str(Path.home() / "Music"))
    authorized_value = tk.BooleanVar(value=False)
    status_value = tk.StringVar(value="Ready")

    frame = ttk.Frame(window, padding=16)
    frame.grid(sticky="nsew")
    ttk.Label(frame, text="YouTube video URL").grid(row=0, column=0, sticky="w")
    url_entry = ttk.Entry(frame, textvariable=url_value, width=54)
    url_entry.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(4, 12))

    ttk.Label(frame, text="Save audio to").grid(row=2, column=0, sticky="w")
    folder_entry = ttk.Entry(frame, textvariable=folder_value, width=42)
    folder_entry.grid(row=3, column=0, sticky="ew", pady=(4, 12))

    def choose_folder():
        selected = filedialog.askdirectory(initialdir=folder_value.get() or str(Path.home()))
        if selected:
            folder_value.set(selected)

    browse_button = ttk.Button(frame, text="Browse...", command=choose_folder)
    browse_button.grid(row=3, column=1, padx=(8, 0), pady=(4, 12))

    authorization = ttk.Checkbutton(
        frame,
        text="I own this audio or have permission to download it.",
        variable=authorized_value,
    )
    authorization.grid(row=4, column=0, columnspan=2, sticky="w", pady=(0, 12))

    progress = ttk.Progressbar(frame, mode="determinate", maximum=100)
    progress.grid(row=5, column=0, columnspan=2, sticky="ew")
    status_label = ttk.Label(frame, textvariable=status_value, wraplength=380)
    status_label.grid(row=6, column=0, columnspan=2, sticky="w", pady=(8, 12))

    def set_busy(value):
        state = "disabled" if value else "normal"
        url_entry.configure(state=state)
        folder_entry.configure(state=state)
        browse_button.configure(state=state)
        authorization.configure(state=state)
        download_button.configure(state=state)

    def download():
        url = url_value.get().strip()
        if not is_youtube_url(url):
            messagebox.showerror("Invalid URL", "Enter a valid YouTube video URL.", parent=window)
            return
        if not authorized_value.get():
            messagebox.showwarning(
                "Permission required",
                "Confirm that you own the audio or have permission to download it.",
                parent=window,
            )
            return
        if shutil.which("ffmpeg") is None:
            messagebox.showerror(
                "FFmpeg is required",
                "MP3 conversion requires FFmpeg. Install FFmpeg and add it to PATH, "
                "then restart this application.",
                parent=window,
            )
            return

        output_dir = Path(folder_value.get()).expanduser()
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            messagebox.showerror("Save folder error", str(error), parent=window)
            return

        set_busy(True)
        progress.configure(value=0)
        status_value.set("Starting download...")

        def progress_hook(data):
            if data.get("status") == "downloading":
                total = data.get("total_bytes") or data.get("total_bytes_estimate")
                percent = data.get("downloaded_bytes", 0) * 100 / total if total else 0
                events.put(("progress", (percent, f"Downloading... {percent:.1f}%")))
            elif data.get("status") == "finished":
                events.put(("progress", (100, "Converting audio to MP3...")))

        def download_worker():
            try:
                from yt_dlp import YoutubeDL

                with YoutubeDL() as downloader:
                    downloader.params["format"] = "bestaudio/best"
                    downloader.params["outtmpl"] = str(output_dir / "%(title)s.%(ext)s")
                    downloader.params["noplaylist"] = True
                    downloader.params["quiet"] = True
                    downloader.params["no_warnings"] = True
                    downloader.params["progress_hooks"] = [progress_hook]
                    downloader.params["postprocessors"] = [{
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }]
                    result = downloader.download([url])
                if result:
                    raise RuntimeError("yt-dlp could not complete the download.")
            except Exception as error:
                events.put(("error", str(error)))
            else:
                events.put(("complete", str(output_dir)))

        try:
            threading.Thread(target=download_worker, name="audio-download", daemon=True).start()
        except RuntimeError as error:
            set_busy(False)
            status_value.set("Could not start the download.")
            messagebox.showerror("Download error", str(error), parent=window)

    download_button = ttk.Button(frame, text="Download MP3", command=download)
    download_button.grid(row=7, column=0, columnspan=2, sticky="ew")
    frame.columnconfigure(0, weight=1)

    def process_events():
        while True:
            try:
                kind, value = events.get_nowait()
            except queue.Empty:
                break
            if kind == "progress":
                percentage, text = value
                progress.configure(value=percentage)
                status_value.set(text)
            elif kind == "complete":
                set_busy(False)
                status_value.set("Download complete.")
                messagebox.showinfo(
                    "Download complete",
                    f"MP3 saved in:\n{value}",
                    parent=window,
                )
            elif kind == "error":
                set_busy(False)
                status_value.set("Download failed.")
                messagebox.showerror("Download failed", value, parent=window)
        if window.winfo_exists():
            window.after(100, process_events)

    window.after(100, process_events)
    window.mainloop()


if __name__ == "__main__":
    main()
