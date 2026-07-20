from typing import List
from pydantic import BaseModel, HttpUrl

# This file just defines the shape of our data so FastAPI knows exactly what to expect.

class Message(BaseModel):
    # A single chat bubble, like "user: I need a test" or "assistant: Here you go!"
    role: str
    content: str

class ChatRequest(BaseModel):
    # What the frontend sends us when the user clicks 'Ask SHL Agent'
    messages: List[Message]

class Recommendation(BaseModel):
    # The blueprint for a single assessment card we show on the right side of the screen
    name: str
    url: HttpUrl
    test_type: str

class ChatResponse(BaseModel):
    # Everything we package up and send back to the frontend after we process a message
    reply: str
    recommendations: List[Recommendation]
    end_of_conversation: bool
