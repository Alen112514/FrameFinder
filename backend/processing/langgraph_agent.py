from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
from typing import List, Dict, Any, TypedDict, Annotated
from operator import add
import os
from api.models import Video, TranscriptSegment
import json

class ChatState(TypedDict):
    messages: Annotated[List[Any], add]
    video_context: Dict[str, Any]
    current_query: str

class VideoChatAgent:
    def __init__(self, video_id: str):
        self.video_id = video_id
        self.video = None
        self.transcript = None
        self.segments = []
        self._load_video_context()
        self.graph = self._build_graph()

    def _load_video_context(self):
        """Load video and transcript data"""
        try:
            self.video = Video.objects.get(id=self.video_id)
            print(f"Loaded video: {self.video.title}")

            try:
                self.transcript = self.video.transcript
                print(f"Loaded transcript: {len(self.transcript.full_text)} characters")

                self.segments = list(self.transcript.segments.all())
                print(f"Loaded {len(self.segments)} transcript segments")

                if len(self.segments) > 0:
                    print(f"First segment: {self.segments[0].text[:100]}...")
                else:
                    print("No transcript segments found!")

            except Exception as transcript_error:
                print(f"Error loading transcript: {transcript_error}")
                self.transcript = None
                self.segments = []

        except Exception as e:
            print(f"Error loading video context: {e}")
            self.video = None
            self.transcript = None
            self.segments = []

    def _build_graph(self):
        """Build the LangGraph workflow"""

        @tool
        def search_transcript(query: str) -> str:
            """Search the video transcript for specific information"""
            relevant_segments = []
            query_lower = query.lower()

            for segment in self.segments:
                if any(word in segment.text.lower() for word in query_lower.split()):
                    relevant_segments.append({
                        'time': f"{segment.start_time:.1f}s",
                        'text': segment.text
                    })

            if relevant_segments:
                return json.dumps(relevant_segments[:5])
            return "No relevant segments found for this query."

        @tool
        def get_video_info() -> str:
            """Get general information about the video"""
            return json.dumps({
                'title': self.video.title,
                'duration': f"{self.video.duration:.1f} seconds",
                'transcript_length': len(self.transcript.full_text),
                'segments': len(self.segments)
            })

        @tool
        def find_timestamp(description: str) -> str:
            """Find the timestamp where something specific happens"""
            from processing.tasks import search_video
            result = search_video(self.video_id, description)

            if result.get('timestamp'):
                return json.dumps({
                    'timestamp': result['timestamp'],
                    'text': result['text'],
                    'window': result['window']
                })
            return "Could not find a matching timestamp for this description."

        # Create the LLM
        llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=os.getenv('GOOGLE_API_KEY'),
            temperature=0.7
        )

        # Create tools
        tools = [search_transcript, get_video_info, find_timestamp]
        llm_with_tools = llm.bind_tools(tools)

        # Build the graph
        graph_builder = StateGraph(ChatState)

        def chat_node(state: ChatState):
            """Process chat messages"""
            messages = state['messages']

            # Add system context
            system_prompt = f"""You are a helpful assistant for analyzing video content.
            You have access to the transcript and metadata for a video titled "{self.video.title}".
            The video is {self.video.duration:.1f} seconds long.

            You can:
            1. Search the transcript for specific information
            2. Find timestamps where specific things are mentioned
            3. Answer questions about the video content

            Be concise and helpful in your responses."""

            full_messages = [SystemMessage(content=system_prompt)] + messages

            response = llm_with_tools.invoke(full_messages)

            return {"messages": [response]}

        def should_continue(state: ChatState):
            """Determine if we should use tools or end"""
            messages = state['messages']
            last_message = messages[-1]

            if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
                return "tools"
            return END

        # Add nodes
        graph_builder.add_node("chat", chat_node)
        graph_builder.add_node("tools", ToolNode(tools))

        # Add edges
        graph_builder.add_edge(START, "chat")
        graph_builder.add_conditional_edges("chat", should_continue)
        graph_builder.add_edge("tools", "chat")

        return graph_builder.compile()

    def process(self, message: str) -> Dict[str, Any]:
        """Process a chat message and return response"""
        try:
            initial_state = {
                "messages": [HumanMessage(content=message)],
                "video_context": {
                    "video_id": self.video_id,
                    "title": self.video.title if self.video else "Unknown"
                },
                "current_query": message
            }

            # Run the graph
            result = self.graph.invoke(initial_state)

            # Extract the response
            ai_messages = [msg for msg in result['messages'] if isinstance(msg, AIMessage)]
            timestamp = None
            window = None

            if ai_messages:
                response_text = ai_messages[-1].content

                # Look for tool calls in all messages to extract timestamp/window data
                for msg in result['messages']:
                    if hasattr(msg, 'tool_calls') and msg.tool_calls:
                        for tool_call in msg.tool_calls:
                            if tool_call['name'] == 'find_timestamp':
                                # Look for the tool result in subsequent messages
                                continue

                    # Check if this is a tool message with find_timestamp results
                    if hasattr(msg, 'content') and isinstance(msg.content, str):
                        try:
                            # Try to parse tool result JSON
                            if msg.content.startswith('{') and ('timestamp' in msg.content or 'window' in msg.content):
                                tool_result = json.loads(msg.content)
                                if 'timestamp' in tool_result:
                                    timestamp = tool_result.get('timestamp')
                                if 'window' in tool_result:
                                    window = tool_result.get('window')
                                    print(f"Found window data from tool: {window}")
                        except (json.JSONDecodeError, AttributeError):
                            pass

                # Fallback: try to extract timestamp from response text
                if timestamp is None and "timestamp" in response_text.lower():
                    import re
                    time_match = re.search(r'(\d+\.?\d*)\s*s', response_text)
                    if time_match:
                        timestamp = float(time_match.group(1))

                return {
                    'text': response_text,
                    'timestamp': timestamp,
                    'window': window
                }

            return {'text': "I couldn't process that request.", 'timestamp': None, 'window': None}

        except Exception as e:
            print(f"Error in chat agent: {e}")
            return {'text': f"Error: {str(e)}", 'timestamp': None, 'window': None}