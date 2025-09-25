import whisper
import torch
from sentence_transformers import SentenceTransformer
import numpy as np
from api.models import Video, Transcript, TranscriptSegment
import os
import tempfile
from django.conf import settings
from langchain_google_genai import GoogleGenerativeAI
import json
from openai import OpenAI
import ffmpeg

# Initialize models
whisper_model = None
embedding_model = None

def get_whisper_model():
    global whisper_model
    if whisper_model is None:
        whisper_model = whisper.load_model("base")
    return whisper_model

def get_embedding_model():
    global embedding_model
    if embedding_model is None:
        embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    return embedding_model

def extract_audio_to_mp3(video_path):
    """Extract audio from video file to MP3 format for OpenAI API"""
    print(f"   Extracting audio from video...")

    # Create temporary MP3 file
    temp_fd, temp_audio_path = tempfile.mkstemp(suffix='.mp3')
    os.close(temp_fd)  # Close the file descriptor, we just need the path

    try:
        # Extract audio using ffmpeg
        (
            ffmpeg
            .input(video_path)
            .output(temp_audio_path, acodec='mp3', audio_bitrate='128k')
            .overwrite_output()
            .run(quiet=True)
        )

        # Get file size for logging
        audio_size = os.path.getsize(temp_audio_path) / (1024*1024)
        print(f"   Audio extracted: {audio_size:.1f}MB MP3")

        return temp_audio_path

    except Exception as e:
        # Clean up temp file if extraction failed
        if os.path.exists(temp_audio_path):
            os.unlink(temp_audio_path)
        raise Exception(f"Audio extraction failed: {str(e)}")

def cleanup_temp_file(file_path):
    """Safely remove temporary file"""
    try:
        if file_path and os.path.exists(file_path):
            os.unlink(file_path)
            print(f"   Cleaned up temporary file")
    except Exception as e:
        print(f"   Warning: Could not clean up temp file: {e}")

def transcribe_with_openai_api(video_path):
    """Transcribe video using OpenAI Whisper API"""
    print(f"   Creating OpenAI client...")
    client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

    # Check if we need to extract audio (video formats not supported by OpenAI API)
    file_ext = os.path.splitext(video_path)[1].lower()
    video_formats = ['.mov', '.avi', '.mkv', '.wmv', '.flv']
    temp_audio_path = None

    try:
        if file_ext in video_formats:
            # Extract audio for video files
            temp_audio_path = extract_audio_to_mp3(video_path)
            file_to_upload = temp_audio_path
        else:
            # Use original file if it's already in a supported format
            file_to_upload = video_path

        print(f"   Uploading file to OpenAI Whisper API...")
        with open(file_to_upload, 'rb') as audio_file:
            response = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="verbose_json",
                timestamp_granularities=["segment"]
            )

        print(f"   Received response from OpenAI API")

    finally:
        # Always clean up temporary audio file if it was created
        if temp_audio_path:
            cleanup_temp_file(temp_audio_path)

    # Convert OpenAI API response to match local Whisper format
    result = {
        'text': response.text,
        'segments': []
    }

    # Handle segments if they exist in the response
    if hasattr(response, 'segments') and response.segments:
        print(f"   Processing {len(response.segments)} segments from API response")
        for i, segment in enumerate(response.segments):
            result['segments'].append({
                'start': segment.start,
                'end': segment.end,
                'text': segment.text
            })
            print(f"      Segment {i+1}: {segment.start:.1f}s-{segment.end:.1f}s")
    else:
        print(f"   Warning: No segments in API response, creating single segment")
        # If no segments, create a single segment for the whole text
        result['segments'] = [{
            'start': 0.0,
            'end': 60.0,  # Default duration, will be updated later
            'text': response.text
        }]

    print(f"   Total segments created: {len(result['segments'])}")
    return result

def transcribe_with_local_whisper(video_path):
    """Transcribe video using local Whisper model"""
    model = get_whisper_model()
    return model.transcribe(video_path, language='en', verbose=False)

def get_video_duration(video_path):
    """Get video duration using FFmpeg"""
    import ffmpeg
    try:
        probe = ffmpeg.probe(video_path)
        duration = float(probe['streams'][0]['duration'])
        return duration
    except Exception as e:
        # Fallback: try to get duration from format
        try:
            duration = float(probe['format']['duration'])
            return duration
        except:
            print(f"Could not determine video duration: {e}")
            return None

def process_video(video_id):
    """Process video: validate duration, extract audio, transcribe, and create segments with embeddings"""
    try:
        video = Video.objects.get(id=video_id)
        video_path = video.file.path

        # Check video duration first
        duration = get_video_duration(video_path)
        if duration is None:
            raise Exception("Could not determine video duration - file may be corrupted")

        max_duration = getattr(settings, 'MAX_VIDEO_DURATION', 180)  # 3 minutes default
        if duration > max_duration:
            raise Exception(f"Video duration ({duration:.1f}s) exceeds maximum allowed duration ({max_duration}s)")

        print(f"Video duration: {duration:.1f}s (within {max_duration}s limit)")

        # Update video duration in database
        video.duration = duration
        video.save()

        # Transcribe with OpenAI API or local Whisper
        use_openai = os.getenv('USE_OPENAI_WHISPER', 'False').lower() == 'true'

        if use_openai and os.getenv('OPENAI_API_KEY') and os.getenv('OPENAI_API_KEY') != 'your-openai-api-key-here':
            try:
                print(f"Attempting transcription of '{video.title}' with OpenAI Whisper API...")
                print(f"   File: {video_path}")
                print(f"   Size: {os.path.getsize(video_path) / (1024*1024):.1f}MB")
                result = transcribe_with_openai_api(video_path)
                print(f"   OpenAI API transcription successful!")
            except Exception as e:
                print(f"   OpenAI API failed with error: {type(e).__name__}: {str(e)}")
                print(f"   Falling back to local Whisper...")
                result = transcribe_with_local_whisper(video_path)
                print(f"   Local Whisper transcription successful!")
        else:
            print(f"Using local Whisper for '{video.title}' (OpenAI disabled or no API key)")
            result = transcribe_with_local_whisper(video_path)

        # Create transcript
        transcript = Transcript.objects.create(
            video=video,
            full_text=result['text']
        )

        # Get segments with timestamps
        segments_data = result.get('segments', [])

        # Create overlapping segments (5-10s with 2s overlap)
        embedding_model = get_embedding_model()
        processed_segments = []

        for i, segment in enumerate(segments_data):
            start_time = segment['start']
            end_time = segment['end']
            text = segment['text'].strip()

            if text:
                # Generate embedding for the segment
                embedding = embedding_model.encode(text).tolist()

                segment_obj = TranscriptSegment.objects.create(
                    transcript=transcript,
                    text=text,
                    start_time=start_time,
                    end_time=end_time,
                    embedding=embedding
                )
                processed_segments.append(segment_obj)

        # Mark video as processed (duration was already set during validation)
        video.processed = True
        video.processing_status = 'completed'
        video.save()

        print(f"Video {video_id} processing completed successfully")
        return True
    except Exception as e:
        print(f"Error processing video {video_id}: {str(e)}")

        # Mark video as failed
        try:
            video = Video.objects.get(id=video_id)
            video.processing_status = 'failed'
            video.save()
        except Exception:
            pass

        return False

def search_video(video_id, query):
    """Search for relevant timestamp in video using semantic search and Gemini judgment"""
    try:
        print(f"Starting search for video {video_id} with query: '{query}'")

        video = Video.objects.get(id=video_id)
        transcript = video.transcript
        segments = transcript.segments.all()

        print(f"Found {segments.count()} segments in transcript")
        if segments.count() == 0:
            print("No segments found in transcript")
            return {'timestamp': None, 'text': None, 'window': None}

        # Embed the query
        embedding_model = get_embedding_model()
        query_embedding = embedding_model.encode(query)
        print(f"Query embedded with shape: {query_embedding.shape}")

        # Calculate similarities
        similarities = []
        for segment in segments:
            segment_embedding = np.array(segment.embedding)
            similarity = np.dot(query_embedding, segment_embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(segment_embedding)
            )
            similarities.append((segment, similarity))

        # Get top-10 segments by relevance
        top_segments = sorted(similarities, key=lambda x: x[1], reverse=True)[:10]
        print(f"Top similarity scores: {[f'{s[1]:.3f}' for s in top_segments[:5]]}")

        # Sort these top segments by time order for presentation to LLM
        top_segments_by_time = sorted(top_segments, key=lambda x: x[0].start_time)
        print(f"Sending {len(top_segments_by_time)} segments to LLM in chronological order")

        # Check if we have Google API key
        google_api_key = os.getenv('GOOGLE_API_KEY')
        if not google_api_key or google_api_key == 'your-google-api-key-here':
            print("Google API key not found or invalid")
            return {'timestamp': None, 'text': None, 'window': None}

        # Send to Gemini to select which segments to play
        print("Sending to Gemini for analysis...")
        result = judge_segments_with_gemini(query, top_segments_by_time)
        print(f"Gemini result: {result}")

        # If no result, fall back to full transcript search
        if not result or result.get('not_found'):
            print("Falling back to full transcript search...")
            result = search_full_transcript(query, transcript.full_text, segments)
            print(f"Full transcript search result: {result}")

        return result
    except Exception as e:
        print(f"Error searching video {video_id}: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'timestamp': None, 'text': None, 'window': None}

def search_video_for_chat(video_id, user_message):
    """
    Search video for chat responses - uses same logic as search_video but returns conversational response
    """
    print(f"Chat search for video {video_id} with message: '{user_message}'")

    # Use the same proven search logic
    search_result = search_video(video_id, user_message)

    if not search_result or search_result.get('timestamp') is None:
        return {
            'text': "I couldn't find specific information about that in the video. Could you try rephrasing your question?",
            'timestamp': None,
            'window': None,
            'segment_text': None
        }

    # Create conversational response
    timestamp = search_result['timestamp']
    segment_text = search_result['text']
    window = search_result['window']

    # Format timestamp for display
    minutes = int(timestamp // 60)
    seconds = int(timestamp % 60)
    time_str = f"{minutes}:{seconds:02d}"

    # Generate conversational response based on the found content
    if segment_text:
        # Create a conversational response that incorporates the found content
        response_text = f"I found relevant information at {time_str} in the video. {segment_text[:100]}{'...' if len(segment_text) > 100 else ''}"
    else:
        response_text = f"I found something relevant at {time_str} in the video."

    return {
        'text': response_text,
        'timestamp': timestamp,
        'window': window,
        'segment_text': segment_text
    }

def judge_segments_with_gemini(query, segments_with_scores):
    """Use Gemini to determine the exact time range to play from video segments"""
    llm = GoogleGenerativeAI(
        model="gemini-1.5-flash",
        google_api_key=os.getenv('GOOGLE_API_KEY'),
        temperature=0
    )

    # Prepare segments for Gemini
    segments_data = []
    for i, (segment, score) in enumerate(segments_with_scores):
        segments_data.append({
            'segment_number': i + 1,
            'time_range': f"{segment.start_time:.1f}s - {segment.end_time:.1f}s",
            'text': segment.text,
            'relevance_score': f"{score:.3f}"
        })

    prompt = f"""You are analyzing segments from a video transcript. Based on the user's question, determine the exact time range of the video to play.

User Question: {query}

Here are the top 10 most relevant segments from the video, sorted by time:
{json.dumps(segments_data, indent=2)}

Task: Determine which portion of the video best answers the question. You should specify a continuous time range to play.
Consider that:
- You can select a single segment or span multiple segments
- Choose the minimal time range that fully answers the question
- The time range should be continuous (no gaps)

Return strict JSON:
{{
    "found": true/false,
    "play_start_time": <start time in seconds>,
    "play_end_time": <end time in seconds>,
    "explanation": "<brief explanation of what content in this time range answers the question>"
}}"""

    try:
        response = llm.invoke(prompt)
        cleaned_response = clean_gemini_response(response.content)
    except Exception as e:
        print(f"Gemini API error: {e}")
        return {'not_found': True}

    try:
        result = json.loads(cleaned_response)
    except json.JSONDecodeError as e:
        print(f"Failed to parse Gemini JSON response: {e}")
        print(f"Cleaned response was: '{cleaned_response}'")
        return {'not_found': True}

    if result.get('found') and result.get('play_start_time') is not None and result.get('play_end_time') is not None:
        play_start = float(result['play_start_time'])
        play_end = float(result['play_end_time'])

        # Find the segments that fall within this range for text extraction
        relevant_text = []
        for segment, score in segments_with_scores:
            if segment.start_time <= play_end and segment.end_time >= play_start:
                relevant_text.append(segment.text)

        combined_text = ' '.join(relevant_text)

        return {
            'timestamp': play_start,
            'text': result.get('explanation', combined_text[:200] + '...'),
            'window': {
                'start': play_start,
                'end': play_end
            }
        }

    return {'not_found': True}

def merge_segments(segments_with_scores):
    """Merge overlapping segments into windows"""
    if not segments_with_scores:
        return []

    # Sort by score (highest first) to start with the most relevant segment
    sorted_segments = sorted(segments_with_scores, key=lambda x: x[1], reverse=True)

    windows = []
    # Use the highest-scoring segment as the reference for start_time
    best_segment = sorted_segments[0][0]
    best_score = sorted_segments[0][1]

    current_window = {
        'segments': [sorted_segments[0][0]],
        'start_time': sorted_segments[0][0].start_time,
        'end_time': sorted_segments[0][0].end_time,
        'text': sorted_segments[0][0].text,
        'score': sorted_segments[0][1],
        'best_segment': best_segment  # Track the most relevant segment
    }

    for segment, score in sorted_segments[1:]:
        # Check if segments overlap or are adjacent (within 3s)
        if segment.start_time <= current_window['end_time'] + 3:
            # Merge - keep the earliest start time and extend the end time
            current_window['segments'].append(segment)
            current_window['start_time'] = min(current_window['start_time'], segment.start_time)
            current_window['end_time'] = max(current_window['end_time'], segment.end_time)
            current_window['text'] += ' ' + segment.text

            # Track the highest-scoring segment for reference but don't change timestamps
            if score > current_window['score']:
                current_window['score'] = score
                current_window['best_segment'] = segment
            else:
                current_window['score'] = max(current_window['score'], score)
        else:
            # Add completed window (timestamps already set correctly)
            windows.append(current_window)

            current_window = {
                'segments': [segment],
                'start_time': segment.start_time,
                'end_time': segment.end_time,
                'text': segment.text,
                'score': score,
                'best_segment': segment
            }

    # Add the final window
    windows.append(current_window)
    return windows

def clean_gemini_response(response):
    """Clean markdown formatting from Gemini response"""
    if not response:
        return response

    # Remove markdown code blocks
    response = response.strip()
    if response.startswith('```json'):
        response = response[7:]  # Remove ```json
    if response.startswith('```'):
        response = response[3:]  # Remove ```
    if response.endswith('```'):
        response = response[:-3]  # Remove ```

    return response.strip()


def search_full_transcript(query, full_text, segments):
    """Fallback: search entire transcript with Gemini"""
    llm = GoogleGenerativeAI(
        model="gemini-1.5-flash",
        google_api_key=os.getenv('GOOGLE_API_KEY'),
        temperature=0
    )

    # Prepare segments with timestamps
    transcript_with_times = []
    for segment in segments:
        transcript_with_times.append({
            'start_s': segment.start_time,
            'end_s': segment.end_time,
            'text': segment.text
        })

    prompt = f"""You are analyzing a complete video transcript to find when specific content is mentioned.

Question: {query}

Full transcript with timestamps:
{json.dumps(transcript_with_times, indent=2)}

Task: Find the earliest moment that answers the question. Return strict JSON:
{{
    "found": true/false,
    "start_time": <seconds or null>,
    "end_time": <seconds or null>,
    "text": "<relevant text excerpt or null>"
}}"""

    response = llm.invoke(prompt)
    print(f"Raw Gemini response from full transcript: '{response}'")

    # Clean and handle response
    cleaned_response = clean_gemini_response(response)
    print(f"Cleaned full transcript response: '{cleaned_response}'")

    if not cleaned_response:
        print("Empty response from Gemini (full transcript)")
        return {'timestamp': None, 'text': None, 'window': None}

    try:
        result = json.loads(cleaned_response)
    except json.JSONDecodeError as e:
        print(f"Failed to parse Gemini JSON response (full transcript): {e}")
        print(f"Cleaned response was: '{cleaned_response}'")
        return {'timestamp': None, 'text': None, 'window': None}

    if result.get('found'):
        # Use the actual time range from Gemini's response if available
        if result.get('end_time'):
            # Gemini provided both start and end times - use the full range
            play_start = result['start_time']
            play_end = result['end_time']
        else:
            # Fallback to reasonable context window around the timestamp
            if any(query.lower().startswith(word) for word in ['when', 'where', 'who']):
                # Concise window for "when" questions
                play_start = max(0, result['start_time'] - 2.0)
                play_end = result['start_time'] + 4.0
            else:
                # Broader context for "what/how" questions
                play_start = max(result['start_time'] - 3.0, 0)
                play_end = result['start_time'] + 8.0

        return {
            'timestamp': result['start_time'],
            'text': result['text'],
            'window': {
                'start': play_start,
                'end': play_end
            }
        }

    return {'timestamp': None, 'text': None, 'window': None}