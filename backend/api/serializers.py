from rest_framework import serializers
from .models import Video, Transcript, TranscriptSegment, SearchQuery, ChatMessage

class TranscriptSegmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TranscriptSegment
        fields = ['id', 'text', 'start_time', 'end_time']

class TranscriptSerializer(serializers.ModelSerializer):
    segments = TranscriptSegmentSerializer(many=True, read_only=True)

    class Meta:
        model = Transcript
        fields = ['id', 'full_text', 'segments', 'created_at']

class VideoSerializer(serializers.ModelSerializer):
    transcript = TranscriptSerializer(read_only=True)

    class Meta:
        model = Video
        fields = ['id', 'title', 'file', 'duration', 'uploaded_at', 'processed', 'transcript']
        read_only_fields = ['processed', 'transcript']

class SearchQuerySerializer(serializers.ModelSerializer):
    class Meta:
        model = SearchQuery
        fields = ['id', 'query', 'result_timestamp', 'result_text', 'created_at']

class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ['id', 'message', 'response', 'timestamp', 'created_at']