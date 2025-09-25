from django.db import models
import uuid

class Video(models.Model):
    PROCESSING_CHOICES = [
        ('uploading', 'Uploading'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='videos/')
    duration = models.FloatField(help_text="Duration in seconds")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed = models.BooleanField(default=False)
    processing_status = models.CharField(
        max_length=20,
        choices=PROCESSING_CHOICES,
        default='uploading',
        help_text="Current processing status"
    )

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return self.title

class Transcript(models.Model):
    video = models.OneToOneField(Video, on_delete=models.CASCADE, related_name='transcript')
    full_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Transcript for {self.video.title}"

class TranscriptSegment(models.Model):
    transcript = models.ForeignKey(Transcript, on_delete=models.CASCADE, related_name='segments')
    text = models.TextField()
    start_time = models.FloatField(help_text="Start time in seconds")
    end_time = models.FloatField(help_text="End time in seconds")
    embedding = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ['start_time']

    def __str__(self):
        return f"{self.start_time:.1f}s - {self.end_time:.1f}s: {self.text[:50]}..."

class SearchQuery(models.Model):
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='searches')
    query = models.TextField()
    result_timestamp = models.FloatField(null=True, blank=True)
    result_text = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Search: {self.query[:50]}..."

class ChatMessage(models.Model):
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='chat_messages')
    message = models.TextField()
    response = models.TextField(null=True, blank=True)
    timestamp = models.FloatField(null=True, blank=True, help_text="Related video timestamp")
    segment_text = models.TextField(null=True, blank=True, help_text="Text content from the video segment")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Chat message for {self.video.title}: {self.message[:50]}..."
