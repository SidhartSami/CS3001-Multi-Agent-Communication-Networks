from enum import Enum
from dataclasses import dataclass, asdict
from typing import Optional
import time
import uuid

class MessageType(Enum):
    TASK_BROADCAST = "task_broadcast"
    BID = "bid"
    TASK_ALLOCATION = "task_allocation"
    ACK = "acknowledgment"
    HEARTBEAT = "heartbeat"
    AGENT_EVENT = "agent_event"  # NEW - agent -> coordinator event stream

@dataclass
class Task:
    task_id: str
    priority: int  # 1-10, higher = more important
    estimated_time: float  # seconds
    description: str
    created_at: float = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()
    
    def to_dict(self):
        """Convert to dictionary"""
        return asdict(self)

@dataclass
class Message:
    msg_id: str
    msg_type: MessageType
    sender_id: str
    payload: dict
    timestamp: float = None
    requires_ack: bool = False
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()
        if self.msg_id is None:
            self.msg_id = str(uuid.uuid4())
    
    def to_dict(self):
        """Convert to dictionary with proper serialization"""
        return {
            'msg_id': self.msg_id,
            'msg_type': self.msg_type.value,  # Convert Enum to string
            'sender_id': self.sender_id,
            'payload': self.payload,
            'timestamp': self.timestamp,
            'requires_ack': self.requires_ack
        }

@dataclass
class Bid:
    agent_id: str
    task_id: str
    bid_value: float  # Lower is better
    current_load: int
    estimated_completion_time: float
    
    def to_dict(self):
        """Convert to dictionary"""
        return asdict(self)

@dataclass
class Heartbeat:
    agent_id: str
    timestamp: float
    status: str  # "alive", "busy", "idle"
    current_load: int
    max_load: int
    
    def to_dict(self):
        """Convert to dictionary"""
        return asdict(self)

@dataclass
class AgentDataStream:
    agent_id: str
    stream_type: str  # "metrics", "status", "telemetry"
    data: dict  # Flexible data payload
    timestamp: float
    
    def to_dict(self):
        """Convert to dictionary"""
        return asdict(self)
