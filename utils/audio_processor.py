import os
import re
import yt_dlp
from pydub import AudioSegment
from gtts import gTTS
from youtube_transcript_api import YouTubeTranscriptApi

DOWNLOAD_DIR = 'downloades'
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def extract_video_id(url: str) -> str:
    """Extract YouTube Video ID from various URL formats."""
    match = re.search(r"(?:v=|\/|vi=|\/v\/|e\/|embed\/|shorts\/)([0-9A-Za-z_-]{11})", url)
    return match.group(1) if match else url

def fetch_youtube_transcript_text(video_id: str) -> str:
    """Fallback method: Fetch transcript text directly via youtube_transcript_api safely across versions."""
    cookie_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'cookies.txt')
    languages = ['en', 'en-US', 'hi']
    transcript_list = None

    # Strategy 1: Modern object instance call (.fetch)
    try:
        api = YouTubeTranscriptApi()
        if hasattr(api, "fetch"):
            try:
                fetched = api.fetch(video_id, languages=languages)
            except TypeError:
                fetched = api.fetch(video_id)

            if isinstance(fetched, list):
                return " ".join([item['text'] for item in fetched])
            return " ".join([snippet.text for snippet in fetched])
    except Exception:
        pass

    # Strategy 2: Class method with cookies parameter
    if transcript_list is None and os.path.exists(cookie_path):
        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=languages, cookies=cookie_path)
        except Exception:
            pass

    # Strategy 3: Class method without cookies parameter
    if transcript_list is None:
        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=languages)
        except Exception:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)

    if transcript_list:
        return " ".join([item['text'] for item in transcript_list])

    raise RuntimeError("Failed to retrieve transcript using any available YouTubeTranscriptApi method signature.")

def convert_text_to_wav(text: str, video_id: str) -> str:
    """Convert extracted transcript text into a standard WAV audio file using gTTS."""
    mp3_path = os.path.join(DOWNLOAD_DIR, f"{video_id}_transcript.mp3")
    wav_path = os.path.join(DOWNLOAD_DIR, f"{video_id}_transcript.wav")

    # Generate synthesized speech from transcript text
    tts = gTTS(text=text[:3000], lang='en') # Truncated to first 3000 chars for processing efficiency
    tts.save(mp3_path)

    # Convert generated MP3 into standard 16kHz WAV format for Whisper/audio pipelines
    sound = AudioSegment.from_mp3(mp3_path)
    sound = sound.set_channels(1).set_frame_rate(16000)
    sound.export(wav_path, format="wav")

    if os.path.exists(mp3_path):
        os.remove(mp3_path)

    return wav_path

def download_youtube_audio(url: str) -> str:
    output_template = os.path.join(DOWNLOAD_DIR, "%(id)s.%(ext)s")
    cookie_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'cookies.txt')

    ydl_opts = {
        "format": "m4a/bestaudio/best",
        "outtmpl": output_template,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
                "preferredquality": "192",
            }
        ],
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": 30,
        "retries": 10,
        "fragment_retries": 10,
        "nocheckcertificate": True,
        "extractor_args": {
            "youtube": {
                "player_client": ["ios", "mweb", "android", "web"]
            }
        },
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
    }

    if os.path.exists(cookie_path):
        ydl_opts["cookiefile"] = cookie_path

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_id = info.get("id")
            final_filename = os.path.join(DOWNLOAD_DIR, f"{video_id}.wav")

            if not os.path.exists(final_filename) or os.path.getsize(final_filename) == 0:
                raise ValueError("Downloaded audio file is missing or empty.")

            return final_filename

    except Exception as e:
        video_id = extract_video_id(url)
        print(f"yt-dlp failed ({e}). Attempting transcript extraction fallback for ID: {video_id}")
        raise RuntimeError(f"DRM_OR_DOWNLOAD_FAILED:{video_id}")

def convert_to_wav(input_path: str) -> str:
    """Convert any audio/video file to WAV format using pydub."""
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")

    output_path = os.path.splitext(input_path)[0] + "_converted.wav"
    audio = AudioSegment.from_file(input_path)

    if len(audio) == 0:
        raise ValueError("Source media file contains no audio tracks.")

    audio = audio.set_channels(1).set_frame_rate(16000)
    audio.export(output_path, format="wav")
    return output_path

def chunk_audio(wav_path: str, chunk_minutes: int = 10) -> list:
    """Chunk WAV file into segments."""
    audio = AudioSegment.from_wav(wav_path)

    if len(audio) < 1000:
        raise ValueError("Extracted audio duration is too short or corrupted.")

    chunk_ms = chunk_minutes * 60 * 1000
    chunks = []

    for i, start in enumerate(range(0, len(audio), chunk_ms)):
        chunk = audio[start : start + chunk_ms]
        if len(chunk) < 500:
            continue

        chunk_path = f"{wav_path}_chunk_{i}.wav"
        chunk.export(chunk_path, format="wav")
        chunks.append(chunk_path)

    if not chunks:
        raise ValueError("No valid non-empty audio chunks could be created.")

    return chunks

def process_input(source: str):
    if source.startswith("http://") or source.startswith("https://"):
        print("Detected YouTube URL. Downloading audio...")
        try:
            wav_path = download_youtube_audio(source)
        except RuntimeError as err:
            if "DRM_OR_DOWNLOAD_FAILED" in str(err):
                video_id = str(err).split(":")[-1]
                print(f"Fetching transcripts via fallback for video ID: {video_id}...")
                transcript_text = fetch_youtube_transcript_text(video_id)
                # Convert the transcript text into an audio file so pydub/ffmpeg can process it seamlessly
                wav_path = convert_text_to_wav(transcript_text, video_id)
            else:
                raise err
    else:
        print("Detected local file. Converting to WAV...")
        wav_path = convert_to_wav(source)

    print("Chunking audio...")
    return chunk_audio(wav_path)