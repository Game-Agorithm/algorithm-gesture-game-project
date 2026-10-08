from yt_dlp import YoutubeDL

url = input("Enter URL: ")
you_options = {}
with YoutubeDL(you_options) as ydl:
    ydl.download([url])
print("Download completed!")

import tkinter as tk
from yt_dlp import YoutubeDL

def download_video():
    url = url_input.get()
    yv = YoutubeDL({
        "format": "best"
    })
    yv.download([url])
    url_input.delete(0, tk.END)

def download_audio():
    pass

window = tk.Tk()
window.title("YouTube Downloader")
window.geometry("400x300")
url_input = tk.Entry(window, width=50)
url_input.pack(pady=10)
video_button = tk.Button(window, 
                         text="Download Video", 
                         command=download_video)
video_button.pack(pady=5)
audio_button = tk.Button(window, 
                         text="Download Audio", 
                         command=download_audio)
audio_button.pack(pady=5)

window.mainloop()

from yt_dlp import YoutubeDL

url = input("Enter URL: ")
you_options = {
    "format": "bestaudio/best",
    "postprocessors": [{
        "key": "FFmpegExtractAudio",
        "preferredcodec": "mp3",
        "preferredquality": "192",
    }],
}
with YoutubeDL(you_options) as ydl:
    ydl.download([url])
print("Download completed!")