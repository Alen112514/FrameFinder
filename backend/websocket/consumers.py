import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from api.models import Video, ChatMessage
from processing.tasks import search_video_for_chat
import uuid
from django.core.cache import cache

class ChatConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.video_id = None
        self.room_group_name = None

    async def connect(self):
        self.video_id = self.scope['url_route']['kwargs'].get('video_id')

        # Handle case where no video_id is provided
        if not self.video_id:
            self.video_id = 'general'

        self.room_group_name = f'chat_{self.video_id}'

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        # Send initial connection message
        connection_message = 'Connected to video chat' if self.video_id != 'general' else 'Connected to general chat (no video selected)'
        await self.send(text_data=json.dumps({
            'type': 'connection',
            'message': connection_message
        }))

    async def disconnect(self, close_code):
        # Leave room group
        if self.room_group_name:
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json.get('message', '')

        if not message:
            return

        # Send user message immediately
        await self.send(text_data=json.dumps({
            'type': 'user_message',
            'message': message,
            'id': str(uuid.uuid4())
        }))

        # Process message with simplified search function
        try:
            if self.video_id != 'general':
                response = await database_sync_to_async(search_video_for_chat)(
                    self.video_id,
                    message
                )
                print(f"Search response: {response}")

                # Create clip URL if we have window data
                segment_url = None
                if response.get('window'):
                    window = response['window']
                    print(f"Using window from search: {window}")
                    segment_url = f'/api/clip/?video_id={self.video_id}&start={window["start"]}&end={window["end"]}'

                # Send AI response with segment URL and text if available
                await self.send(text_data=json.dumps({
                    'type': 'ai_message',
                    'message': response['text'],
                    'timestamp': response.get('timestamp'),
                    'segment_url': segment_url,
                    'segment_text': response.get('segment_text'),
                    'id': str(uuid.uuid4())
                }))

                # Save to database
                await self.save_message(message, response)
            else:
                # No video selected
                await self.send(text_data=json.dumps({
                    'type': 'ai_message',
                    'message': 'Sorry, I need a valid video to be able to chat about it. Please select a video first.',
                    'timestamp': None,
                    'id': str(uuid.uuid4())
                }))

        except Exception as e:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'Error processing message: {str(e)}'
            }))


    @database_sync_to_async
    def save_message(self, user_message, response):
        """Save chat message to database"""
        try:
            if self.video_id != 'general':
                video = Video.objects.get(id=self.video_id)
                ChatMessage.objects.create(
                    video=video,
                    message=user_message,
                    response=response['text'],
                    timestamp=response.get('timestamp'),
                    segment_text=response.get('segment_text')
                )
        except Exception as e:
            print(f"Error saving message: {e}")