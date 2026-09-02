import os
import re
import yt_dlp
from pydub import AudioSegment
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound

DOWNLOAD_DIR = 'downloades'
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def extract_video_id(url: str) -> str:
    """Extract YouTube Video ID from various URL formats."""
    match = re.search(r"(?:v=|\/|vi=|\/v\/|e\/|embed\/|shorts\/)([0-9A-Za-z_-]{11})", url)
    return match.group(1) if match else url

def fetch_youtube_transcript_text(video_id: str) -> str:
    """Fallback method: Fetch transcript text directly via youtube_transcript_api using cookies."""
    cookie_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'cookies.txt')

    try:
        # Pass cookies if available to bypass datacenter IP blocks
        if os.path.exists(cookie_path):
            transcript_list = YouTubeTranscriptApi.get_transcript(
                video_id,
                languages=['en', 'en-US', 'hi'],
                cookies=cookie_path
            )
        else:
            transcript_list = YouTubeTranscriptApi.get_transcript(
                video_id,
                languages=['en', 'en-US', 'hi']
            )

        return " ".join([item['text'] for item in transcript_list])

    except Exception as e:
        raise RuntimeError(f"Transcript extraction failed: {e}")

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
            print("Chunking audio...")
            return chunk_audio(wav_path)
        except RuntimeError as err:
            if "DRM_OR_DOWNLOAD_FAILED" in str(err):
                video_id = str(err).split(":")[-1]
                print(f"Fetching transcripts via fallback for video ID: {video_id}...")
                transcript_text = fetch_youtube_transcript_text(video_id)
                return transcript_text
            else:
                raise err
    else:
        print("Detected local file. Converting to WAV...")
        wav_path = convert_to_wav(source)
        return chunk_audio(wav_path)