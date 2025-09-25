# FrameFinder

A full-stack web application for intelligent video search and conversation using natural language processing, semantic search, and AI-powered analysis.

## Features

### 1. **Smart Video Upload**

- Upload videos up to 3 minutes in duration
- Real-time processing status via Server-Sent Events (SSE)
- Automatic transcription with dual Whisper support
- Processing progress indicators and error handling

### 2. **Semantic Video Search**

- Natural language queries (e.g., "When does the presenter mention AI?")
- SentenceTransformer embeddings with cosine similarity
- Intelligent segment merging and temporal window analysis
- Google Gemini AI for precise timestamp judgment
- Fallback to full-transcript search for comprehensive coverage

### 3. **Interactive Video Chat**

- Real-time WebSocket-based chat interface
- Context-aware responses about video content
- Automatic video segment playback for relevant answers
- LangGraph-powered conversational AI agent

### 4. **Advanced Video Playback**

- Server-side FFmpeg integration for precise video clips
- Dynamic segment streaming with start/end parameters
- Automatic playback of relevant video portions
- Responsive video player with metadata support

### 5. **Real-time Communication**

- Server-Sent Events for processing status updates
- WebSocket connections for instant chat responses
- Connection management with automatic reconnection
- Live status indicators for all operations

## Tech Stack

### Backend

- **Framework**: Django 5.2+ with Django REST Framework
- **WebSockets**: Django Channels with Daphne ASGI server
- **AI/ML**: Google Gemini 2.5 Flash, SentenceTransformers, LangGraph
- **Transcription**: OpenAI Whisper API + Local Whisper fallback
- **Media Processing**: FFmpeg-python for video manipulation
- **Database**: SQLite (development), PostgreSQL-ready
- **Data Processing**: NumPy, Pandas for embeddings and analysis

### Frontend

- **Framework**: Next.js 15+ with TypeScript
- **UI**: Tailwind CSS, responsive design
- **HTTP Client**: Axios for API communication
- **Real-time**: Native WebSocket + EventSource (SSE)
- **Video**: HTML5 video with custom controls

### AI Pipeline

- **Speech-to-Text**: OpenAI Whisper API (primary) + Local Whisper (fallback)
- **Embeddings**: all-MiniLM-L6-v2 SentenceTransformer model
- **Language Model**: Google Gemini 2.5 Flash with structured output
- **Agent Framework**: LangGraph for conversational AI

## Quick Start

### Prerequisites

- **Python 3.11+** with `uv` package manager
- **Node.js 18+** with npm
- **FFmpeg** (for video processing)
- **Google API Key** (for Gemini)
- **OpenAI API Key** (optional, for Whisper API)

### Installation

1. **Clone and setup**:

   ```bash
   git clone <repository-url>
   cd FrameFinder
   ./setup.sh
   ```

2. **Configure environment**:

   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

3. **Required environment variables**:
   ```env
   SECRET_KEY=your-django-secret-key
   DEBUG=True
   GOOGLE_API_KEY=your-gemini-api-key
   OPENAI_API_KEY=your-openai-key  # Optional
   USE_OPENAI_WHISPER=True  # False for local Whisper only
   ```

### Running the Application

1. **Start Django backend**:

   ```bash
   cd backend
   uv run python manage.py runserver
   ```

2. **Start Next.js frontend** (new terminal):

   ```bash
   cd frontend
   npm run dev
   ```

3. **Access**: http://localhost:3000

## Architecture

### Processing Pipeline

```
Video Upload → Django Validation → Background Processing → ASR Transcription
    ↓                                                            ↓
SSE Status Updates ← Processing Status ← Segment Analysis ← Whisper Output
    ↓                                                            ↓
UI Updates       ← WebSocket Chat    ← Semantic Search   ← Embedding Storage
```

### Search Algorithm

1. **Query Processing**: User question → SentenceTransformer embedding
2. **Similarity Search**: Cosine similarity against transcript segments
3. **Segment Merging**: Top-12 segments → ≤5 temporal windows (5-10s with 2s overlap)
4. **AI Judgment**: Gemini analyzes windows → selects earliest relevant moment
5. **Fallback**: Full transcript search if no specific matches found
6. **Playback Window**: Smart duration based on query type:
   - "When/Where/Who" → Concise: [timestamp-1.2s, timestamp+3s]
   - "What/How/Why" → Contextual: ~12s centered window

### WebSocket Communication

```
Frontend ←→ Django Channels ←→ LangGraph Agent ←→ Video Search
    ↓              ↓                    ↓              ↓
UI Updates    Message Routing    AI Processing    Semantic Analysis
```

## API Reference

### REST Endpoints

- `POST /api/videos/` - Upload video file
- `GET /api/videos/{id}/` - Get video details
- `POST /api/videos/{id}/search/` - Search video content
- `GET /api/clip/?video_id={id}&start={s}&end={s}` - Stream video segment

### Real-time Endpoints

- `GET /api/videos/{id}/status-stream/` - Server-Sent Events for processing status
- `ws://localhost:8000/ws/chat/{video_id}/` - WebSocket chat connection

### Response Formats

```json
{
  "search_result": {
    "timestamp": 45.2,
    "text": "relevant transcript excerpt",
    "window": { "start": 44.0, "end": 48.4 },
    "segment_url": "/api/clip/?video_id=123&start=44.0&end=48.4"
  }
}
```

## Development

### Backend Development

```bash
cd backend

# Database operations
uv run manage.py makemigrations
uv run manage.py migrate
uv run manage.py createsuperuser

# Run server with auto-reload
uv run manage.py runserver

# Run tests
uv run manage.py test
```

### Frontend Development

```bash
cd frontend

# Development server
npm run dev

# Type checking
npm run type-check

# Linting
npm run lint

# Production build
npm run build
```

### Debugging

```bash
# Check video processing
uv run backend/test_whisper_api.py

# Monitor WebSocket connections
# Browser DevTools → Network → WS

# Check SSE streams
# Browser DevTools → Network → EventStream
```

## Configuration

### Whisper Options

**OpenAI Whisper API** (Recommended):

- Fast, cloud-based transcription
- Supports multiple formats automatically
- Requires API key and credits
- Set `USE_OPENAI_WHISPER=True`

**Local Whisper** (Fallback):

- Downloads ~150MB model on first use
- Free but slower processing
- CPU/GPU dependent performance
- Automatic fallback if API fails

### Video Processing

- **Max Duration**: 3 minutes (180 seconds)
- **Supported Formats**: MP4, MOV, AVI, MKV, WMV, FLV
- **Output**: MP4 segments with precise timing

### Performance Tuning

- **Segment Size**: 5-10 seconds with 2s overlap
- **Search Windows**: Max 5 windows per query
- **Embedding Model**: Cached globally for efficiency
- **Database**: Consider PostgreSQL for production

## Troubleshooting

### Common Issues

1. **FFmpeg not found**: Install FFmpeg system-wide
2. **Long video processing**: Ensure video is under 3 minutes duration
3. **API rate limits**: Check OpenAI/Google API quotas
4. **WebSocket connection**: Verify CORS settings for your domain
5. **Slow search**: Ensure embeddings are properly cached

### Debug Commands

```bash
# Check API keys
uv run test_whisper_api.py

# Test video processing
uv run manage.py shell
>>> from processing.tasks import process_video
>>> process_video("video-uuid-here")

# Monitor logs
tail -f backend/logs/django.log
```

## License

MIT License - see LICENSE file for details.

---

**FrameFinder** - Intelligent video search powered by AI
