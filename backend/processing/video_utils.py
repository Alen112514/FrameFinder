import subprocess
import tempfile
import os
from pathlib import Path

def extract_video_segment(video_path, start_time, end_time):
    """
    Extract a segment from a video file using FFmpeg.

    Args:
        video_path: Path to the input video file
        start_time: Start time in seconds
        end_time: End time in seconds

    Returns:
        bytes: The video segment as bytes
    """
    duration = end_time - start_time

    # Create a temporary file for the output
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp_file:
        tmp_path = tmp_file.name

    try:
        # FFmpeg command to extract segment
        # -ss: seek to start time (before input for fast seeking)
        # -i: input file
        # -t: duration
        # -c:v copy: copy video codec (no re-encoding)
        # -c:a copy: copy audio codec (no re-encoding)
        # -avoid_negative_ts make_zero: fix timestamp issues
        cmd = [
            'ffmpeg',
            '-ss', str(start_time),  # Seek to start time
            '-i', video_path,         # Input file
            '-t', str(duration),      # Duration
            '-c:v', 'copy',          # Copy video codec
            '-c:a', 'copy',          # Copy audio codec
            '-avoid_negative_ts', 'make_zero',  # Fix timestamps
            '-f', 'mp4',             # Force mp4 format
            '-movflags', '+faststart',  # Optimize for web streaming
            '-y',                    # Overwrite output
            tmp_path                 # Output file
        ]

        # Run FFmpeg
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30  # 30 second timeout
        )

        if result.returncode != 0:
            print(f"FFmpeg error: {result.stderr}")
            raise Exception(f"FFmpeg failed: {result.stderr}")

        # Read the segment file
        with open(tmp_path, 'rb') as f:
            segment_bytes = f.read()

        return segment_bytes

    finally:
        # Clean up temporary file
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def extract_video_segment_stream(video_path, start_time, end_time):
    """
    Extract a segment from a video file using FFmpeg and stream it as a generator.
    This version yields chunks of fragmented MP4 data for direct streaming to HTTP response.

    Args:
        video_path: Path to the input video file
        start_time: Start time in seconds
        end_time: End time in seconds

    Yields:
        bytes: Chunks of the video segment as fragmented MP4
    """
    duration = end_time - start_time

    # FFmpeg command to extract and stream segment
    cmd = [
        'ffmpeg',
        '-ss', str(start_time),  # Seek to start time
        '-i', video_path,         # Input file
        '-t', str(duration),      # Duration
        '-c:v', 'copy',          # Copy video codec
        '-c:a', 'copy',          # Copy audio codec
        '-avoid_negative_ts', 'make_zero',  # Fix timestamps
        '-f', 'mp4',             # Force mp4 format
        '-movflags', 'frag_keyframe+empty_moov+faststart',  # Fragmented MP4 for streaming
        '-'                      # Output to stdout
    ]

    try:
        # Start FFmpeg process
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0  # Unbuffered for immediate streaming
        )

        # Stream the output in chunks
        chunk_size = 8192
        while True:
            chunk = process.stdout.read(chunk_size)
            if not chunk:
                break
            yield chunk

        # Wait for process to complete and check for errors
        process.wait()
        if process.returncode != 0:
            stderr_output = process.stderr.read().decode()
            raise Exception(f"FFmpeg failed: {stderr_output}")

    except Exception as e:
        if 'process' in locals():
            process.kill()
        raise Exception(f"Video segment streaming failed: {str(e)}")