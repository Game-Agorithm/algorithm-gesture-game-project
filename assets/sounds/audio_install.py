"""CustomTkinter GUI for downloading audio the user is authorized to save."""

from pathlib import Path
import queue
import shutil
import threading
from urllib.parse import urlparse


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
    try:
        import customtkinter as ctk
    except ImportError as error:
        raise RuntimeError(
            "CustomTkinter is required for the audio downloader. "
            "Install project requirements with: python -m pip install -r requirements.txt"
        ) from error

    import tkinter as tk
    from tkinter import filedialog

    ctk.set_appearance_mode("system")
    ctk.set_default_color_theme("blue")
    window = ctk.CTk()
    window.title("YouTube Audio Downloader")
    window.geometry("620x390")
    window.minsize(560, 360)

    events = queue.Queue()
    frame = ctk.CTkFrame(window, corner_radius=14)
    frame.pack(fill="both", expand=True, padx=24, pady=24)
    frame.grid_columnconfigure(0, weight=1)
    frame.grid_columnconfigure(1, weight=0)

    ctk.CTkLabel(frame, text="YouTube video URL").grid(
        row=0, column=0, sticky="w", padx=(20, 8), pady=(20, 4)
    )
    url_entry = ctk.CTkEntry(
        frame, placeholder_text="https://www.youtube.com/watch?v=..."
    )
    url_entry.grid(row=1, column=0, sticky="ew", padx=(20, 8), pady=(0, 14))

    ctk.CTkLabel(frame, text="Save audio to").grid(
        row=2, column=0, columnspan=2, sticky="w", padx=20, pady=(0, 4)
    )
    folder_entry = ctk.CTkEntry(frame)
    folder_entry.insert(0, str(Path.home() / "Music"))
    folder_entry.grid(row=3, column=0, sticky="ew", padx=(20, 8), pady=(0, 14))

    def show_message(title, text):
        dialog = ctk.CTkToplevel(window)
        dialog.title(title)
        dialog.transient(window)
        dialog.resizable(False, False)
        dialog.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            dialog, text=text, wraplength=390, justify="left"
        ).grid(row=0, column=0, padx=20, pady=(20, 12), sticky="ew")
        ctk.CTkButton(
            dialog, text="OK", command=dialog.destroy, width=100
        ).grid(row=1, column=0, padx=20, pady=(0, 16))
        dialog.update_idletasks()
        dialog.grab_set()
        dialog.focus_force()

    def paste_link():
        try:
            text = window.clipboard_get()
        except tk.TclError as error:
            show_message("Paste failed", f"Could not read text from the clipboard: {error}")
            return "break"

        if url_entry.select_present():
            start = url_entry.index("sel.first")
            end = url_entry.index("sel.last")
            url_entry.delete(start, end)
            cursor = start
        else:
            cursor = url_entry.index("insert")

        url_entry.insert(cursor, text)
        url_entry.icursor(cursor + len(text))
        url_entry.focus_set()
        return "break"

    paste_button = ctk.CTkButton(
        frame, text="Paste", command=paste_link, width=100
    )
    paste_button.grid(row=1, column=1, padx=(0, 20), pady=(0, 14))

    def choose_folder():
        selected = filedialog.askdirectory(
            parent=window,
            initialdir=folder_entry.get() or str(Path.home()),
        )
        if selected:
            folder_entry.delete(0, "end")
            folder_entry.insert(0, selected)

    browse_button = ctk.CTkButton(
        frame, text="Browse...", command=choose_folder, width=100
    )
    browse_button.grid(row=3, column=1, padx=(0, 20), pady=(0, 14))

    authorization = ctk.CTkCheckBox(
        frame,
        text="I own this audio or have permission to download it.",
    )
    authorization.grid(
        row=4, column=0, columnspan=2, sticky="w", padx=20, pady=(0, 16)
    )

    progress = ctk.CTkProgressBar(frame)
    progress.set(0)
    progress.grid(row=5, column=0, columnspan=2, sticky="ew", padx=20, pady=(0, 8))
    status_label = ctk.CTkLabel(frame, text="Ready", anchor="w", wraplength=520)
    status_label.grid(
        row=6, column=0, columnspan=2, sticky="ew", padx=20, pady=(0, 14)
    )

    def set_busy(value):
        state = "disabled" if value else "normal"
        url_entry.configure(state=state)
        folder_entry.configure(state=state)
        paste_button.configure(state=state)
        browse_button.configure(state=state)
        authorization.configure(state=state)
        download_button.configure(state=state)

    def download():
        url = url_entry.get().strip()
        if not is_youtube_url(url):
            show_message("Invalid URL", "Enter a valid YouTube video URL.")
            return
        if not authorization.get():
            show_message(
                "Permission required",
                "Confirm that you own the audio or have permission to download it.",
            )
            return
        if shutil.which("ffmpeg") is None:
            show_message(
                "FFmpeg is required",
                "MP3 conversion requires FFmpeg. Install FFmpeg and add it to PATH, "
                "then restart this application.",
            )
            return

        output_dir = Path(folder_entry.get()).expanduser()
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            show_message("Save folder error", str(error))
            return

        set_busy(True)
        progress.set(0)
        status_label.configure(text="Starting download...")

        def progress_hook(data):
            if data.get("status") == "downloading":
                total = data.get("total_bytes") or data.get("total_bytes_estimate")
                percent = data.get("downloaded_bytes", 0) * 100 / total if total else 0
                events.put(("progress", (percent / 100, f"Downloading... {percent:.1f}%")))
            elif data.get("status") == "finished":
                events.put(("progress", (1, "Converting audio to MP3...")))

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
            status_label.configure(text="Could not start the download.")
            show_message("Download error", str(error))

    download_button = ctk.CTkButton(frame, text="Download MP3", command=download)
    download_button.grid(
        row=7, column=0, columnspan=2, sticky="ew", padx=20, pady=(0, 20)
    )

    def process_events():
        while True:
            try:
                kind, value = events.get_nowait()
            except queue.Empty:
                break
            if kind == "progress":
                fraction, text = value
                progress.set(fraction)
                status_label.configure(text=text)
            elif kind == "complete":
                set_busy(False)
                status_label.configure(text="Download complete.")
                show_message(
                    "Download complete",
                    f"MP3 saved in:\n{value}",
                )
            elif kind == "error":
                set_busy(False)
                status_label.configure(text="Download failed.")
                show_message("Download failed", value)
        if window.winfo_exists():
            window.after(100, process_events)

    window.after(100, process_events)
    window.mainloop()


if __name__ == "__main__":
    main()
