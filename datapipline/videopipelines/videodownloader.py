import os
import yt_dlp
from transcriber import run_local_transcription

def download_and_transcribe(url):
  FFMPEG_PATH = r"C:\ffmpeg\bin"
  
  ydl_opts = {
    'format': 'bestvideo+bestaudio/best',
    'outtmpl': 'downloads/%(title)s.%(ext)s',
    'noplaylist': False,
    'ffmpeg_location': FFMPEG_PATH, 
    'postprocessors': [{
      'key': 'FFmpegExtractAudio',
      'preferredcodec': 'mp3',
      'preferredquality': '192',
      'keepvideo': True, 
    }],
  }

  try:
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
      info = ydl.extract_info(url, download=True)
      entries = info.get('entries', [info])
      
      for entry in entries:
        video_title = entry.get('title')
        audio_filename = f"{video_title}.mp3"
        
        if os.path.exists(audio_filename):
          run_local_transcription(audio_filename, video_title)
        else:
          print(f"Could not locate audio file for: {video_title}")

  except Exception as e:
    print(f"An error occurred during download/transcription: {e}")

target_url = "https://youtu.be/oJTvjhuzJEg?list=RDMM"
download_and_transcribe(target_url)
