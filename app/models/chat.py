from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict
from datetime import datetime
from enum import Enum

class ParticipantRole(str, Enum):
    SENDER = "sender"
    RECEIVER = "receiver"
    ADMIN = "admin"
    SUPPORT = "support"

class Participant(BaseModel):
    user_id: str
    username: str
    email: Optional[str] = None
    role: ParticipantRole = ParticipantRole.SENDER
    last_active: Optional[datetime] = None

class ChatMessage(BaseModel):
    message_id: Optional[str] = None
    sender: Participant
    receiver: Participant
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    read_status: bool = False
    message_type: str = 'text'
    attachments: Optional[List[Dict]] = None
    metadata: Optional[Dict] = None

    @validator('content')
    def validate_content(cls, content):
        if not content or len(content.strip()) == 0:
            raise ValueError("Message content cannot be empty")
        return content

class ConversationModel(BaseModel):
    conversation_id: Optional[str] = None
    participants: List[Participant]
    messages: List[ChatMessage] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_message_timestamp: Optional[datetime] = None
    conversation_type: str = 'private'
    tags: Optional[List[str]] = None
    is_active: bool = True

    def add_message(self, message: ChatMessage):
        """
        Add a new message to the conversation
        """
        self.messages.append(message)
        self.last_message_timestamp = message.timestamp

    def get_participant_ids(self) -> List[str]:
        """
        Get a list of participant user IDs
        """
        return [participant.user_id for participant in self.participants]

    def is_participant(self, user_id: str) -> bool:
        """
        Check if a user is part of the conversation
        """
        return user_id in self.get_participant_ids()