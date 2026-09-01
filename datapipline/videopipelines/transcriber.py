from faster_whisper import WhisperModel

def run_local_transcription(audio_path, output_name):
  model = WhisperModel("base", device="cuda", compute_type="float32")

  segments, info = model.transcribe(audio_path, beam_size=5)
  print(f"Detected language: '{info.language}' with probability {info.language_probability:.2f}")

  transcript_filename = f"{output_name}_transcript.txt"
  with open(transcript_filename, "w", encoding="utf-8") as f:
    for segment in segments:
      timestamp = f"[{int(segment.start)//60:02d}:{int(segment.start)%60:02d}] "
      f.write(f"{timestamp}{segment.text}\n")
          
  print(f"Saved transcript to: {transcript_filename}\n")