from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.conf import settings
from django.http import HttpResponse, StreamingHttpResponse
from .models import Video, SearchQuery
from .serializers import VideoSerializer, SearchQuerySerializer
from processing.tasks import process_video, search_video
from processing.video_utils import extract_video_segment_stream
import os
import json
import time

class VideoViewSet(viewsets.ModelViewSet):
    queryset = Video.objects.all()
    serializer_class = VideoSerializer
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def create(self, request, *args, **kwargs):
        file = request.FILES.get('file')
        if not file:
            return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)

        # Note: Duration validation is handled during processing
        # File size is no longer limited - only duration matters

        title = request.data.get('title', file.name)
        video = Video.objects.create(
            title=title,
            file=file,
            duration=0,  # Will be updated during processing
            processing_status='processing'  # Start processing immediately after upload
        )

        # Start processing in background thread
        import threading
        processing_thread = threading.Thread(
            target=process_video,
            args=(str(video.id),)
        )
        processing_thread.daemon = True
        processing_thread.start()

        serializer = self.get_serializer(video)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def search(self, request, pk=None):
        video = self.get_object()
        query = request.data.get('query')

        if not query:
            return Response({'error': 'Query is required'}, status=status.HTTP_400_BAD_REQUEST)

        if not video.processed:
            return Response({'error': 'Video is still processing'}, status=status.HTTP_400_BAD_REQUEST)

        # Trigger search
        result = search_video(str(video.id), query)

        # Save search query
        search_query = SearchQuery.objects.create(
            video=video,
            query=query,
            result_timestamp=result.get('timestamp'),
            result_text=result.get('text')
        )

        return Response({
            'timestamp': result.get('timestamp'),
            'text': result.get('text'),
            'window': result.get('window'),
            'segment_url': f'/api/clip/?video_id={video.id}&start={result["window"]["start"]}&end={result["window"]["end"]}' if result.get('window') else None
        }, status=status.HTTP_200_OK)

@api_view(['GET', 'HEAD'])
def clip(request):
    """Stream video clip with start/end parameters"""
    video_id = request.GET.get('video_id')
    start = request.GET.get('start')
    end = request.GET.get('end')

    print(f"Clip request - video_id: {video_id}, start: {start}, end: {end}")

    if not all([video_id, start, end]):
        print(f"Missing parameters - video_id: {video_id}, start: {start}, end: {end}")
        return Response(
            {'error': 'Missing required parameters: video_id, start, end'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        video = Video.objects.get(id=video_id)
        start_time = float(start)
        end_time = float(end)

        print(f"Found video: {video.title}, path: {video.file.path}")
        print(f"Extracting segment: {start_time}s to {end_time}s")

        if start_time >= end_time:
            print(f"Invalid time range: start {start_time} >= end {end_time}")
            return Response(
                {'error': 'Start time must be less than end time'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if video file exists
        import os
        if not os.path.exists(video.file.path):
            print(f"Video file not found: {video.file.path}")
            return Response(
                {'error': 'Video file not found on disk'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Handle HEAD vs GET requests
        if request.method == 'HEAD':
            # For HEAD requests, return headers without body
            print(f"HEAD request - returning headers only")
            response = HttpResponse(content_type='video/mp4')
            response['Accept-Ranges'] = 'bytes'
            response['Content-Disposition'] = f'inline; filename="clip_{start_time}_{end_time}.mp4"'
            return response
        else:
            # For GET requests, stream the video segment
            def video_stream():
                try:
                    print(f"Starting FFmpeg stream for {video.file.path}")
                    return extract_video_segment_stream(video.file.path, start_time, end_time)
                except Exception as stream_error:
                    print(f"FFmpeg streaming error: {stream_error}")
                    raise

            response = StreamingHttpResponse(
                video_stream(),
                content_type='video/mp4'
            )
            response['Accept-Ranges'] = 'bytes'
            response['Content-Disposition'] = f'inline; filename="clip_{start_time}_{end_time}.mp4"'

            print(f"GET request - streaming response created successfully")
            return response

    except Video.DoesNotExist:
        print(f"Video not found in database: {video_id}")
        return Response(
            {'error': 'Video not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except (ValueError, TypeError) as e:
        print(f"Invalid parameters: {e}")
        return Response(
            {'error': f'Invalid start or end time: {str(e)}'},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        print(f"Error streaming clip: {e}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return Response(
            {'error': f'Failed to stream video clip: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

def video_status_stream(request, video_id):
    """Stream processing status updates via Server-Sent Events"""
    if request.method != 'GET':
        return HttpResponse(status=405)  # Method not allowed

    try:
        video = Video.objects.get(id=video_id)
    except Video.DoesNotExist:
        return HttpResponse('Video not found', status=404)

    def event_stream():
        """Generator function for SSE stream"""
        last_status = None

        while True:
            try:
                # Refresh video from database
                video.refresh_from_db()
                current_status = video.processing_status

                # Only send update if status changed
                if current_status != last_status:
                    event_data = {
                        'status': current_status,
                        'processed': video.processed,
                        'timestamp': time.time()
                    }

                    yield f"data: {json.dumps(event_data)}\n\n"
                    last_status = current_status

                    # Close stream when processing is complete or failed
                    if current_status in ['completed', 'failed']:
                        break

                # Wait before next check
                time.sleep(1)

            except Exception as e:
                print(f"SSE stream error: {e}")
                break

    response = StreamingHttpResponse(
        event_stream(),
        content_type='text/event-stream'
    )
    response['Cache-Control'] = 'no-cache'
    response['Connection'] = 'keep-alive'
    response['Access-Control-Allow-Origin'] = '*'
    response['Access-Control-Allow-Headers'] = 'Cache-Control'

    return response
