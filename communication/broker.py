import json
import time
import threading
from typing import Callable, Dict, Optional, List
import logging
from queue import Queue
from collections import defaultdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import redis, but make it optional
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

class InMemoryBroker:
    """In-memory message broker that doesn't require Redis"""
    def __init__(self):
        self.subscribers = defaultdict(list)  # channel -> list of callbacks
        self.message_queues = defaultdict(Queue)  # channel -> Queue of messages
        self.pending_acks = {}  # Messages waiting for acknowledgment
        self.ack_timeout = 5  # seconds
        self.max_retries = 3
        self.running = False
        self.listen_threads = {}  # channel -> thread
        self.timeout_thread = None
        self.lock = threading.Lock()
        
    def publish(self, channel: str, message: dict, reliable: bool = False):
        """Publish message to a channel"""
        if not self.running:
            return
            
        msg_data = json.dumps(message) if isinstance(message, dict) else message
        
        if reliable and isinstance(message, dict) and message.get('requires_ack'):
            msg_id = message.get('msg_id')
            with self.lock:
                self.pending_acks[msg_id] = {
                    'channel': channel,
                    'message': message,
                    'sent_at': time.time(),
                    'retries': 0
                }
            logger.info(f"📤 Sent reliable message {msg_id[:8]} to {channel}")
        
        # Put message in queue for the channel
        self.message_queues[channel].put({
            'type': 'message',
            'channel': channel,
            'data': msg_data
        })
    
    def subscribe(self, channel: str, callback: Callable):
        """Subscribe to a channel with a callback"""
        with self.lock:
            if channel not in self.subscribers:
                self.subscribers[channel] = []
                logger.info(f"📡 Subscribed to channel: {channel}")
                
                # Start listener thread for this channel if not already running
                if channel not in self.listen_threads or not self.listen_threads[channel].is_alive():
                    thread = threading.Thread(target=self._listen_channel, args=(channel,), daemon=True)
                    thread.start()
                    self.listen_threads[channel] = thread
            
            self.subscribers[channel].append(callback)
            logger.info(f"📡 Added subscriber to {channel} (total: {len(self.subscribers[channel])})")
    
    def _listen_channel(self, channel: str):
        """Listen for messages on a specific channel"""
        while self.running:
            try:
                # Get message from queue with timeout
                message = self.message_queues[channel].get(timeout=0.5)
                
                if message['type'] == 'message':
                    try:
                        data = json.loads(message['data']) if isinstance(message['data'], str) else message['data']
                    except (json.JSONDecodeError, TypeError):
                        logger.error(f"❌ Failed to decode message on channel {channel}")
                        continue
                    
                    # Handle ACK messages
                    if channel == 'acks' or data.get('msg_type') == 'acknowledgment':
                        if data.get('msg_type') == 'acknowledgment':
                            self.handle_ack(data.get('ack_for'))
                        continue
                    
                    # Call ALL subscriber callbacks for the channel
                    with self.lock:
                        callbacks = self.subscribers[channel].copy()
                    
                    for callback in callbacks:
                        try:
                            callback(data)
                        except Exception as e:
                            logger.error(f"❌ Error in subscriber callback for {channel}: {e}")
            except:
                # Timeout or queue empty, continue
                continue
    
    def handle_ack(self, msg_id: str):
        """Handle acknowledgment of a message"""
        with self.lock:
            if msg_id in self.pending_acks:
                logger.info(f"✅ Received ACK for message {msg_id[:8]}")
                del self.pending_acks[msg_id]
    
    def check_timeouts(self):
        """Check for messages that need retransmission"""
        if not self.running:
            return
            
        current_time = time.time()
        with self.lock:
            for msg_id, info in list(self.pending_acks.items()):
                if current_time - info['sent_at'] > self.ack_timeout:
                    if info['retries'] < self.max_retries:
                        logger.warning(f"⏱️ Timeout for message {msg_id[:8]}, retransmitting (retry {info['retries'] + 1})")
                        try:
                            self.publish(info['channel'], info['message'], reliable=True)
                            info['retries'] += 1
                            info['sent_at'] = current_time
                        except Exception as e:
                            logger.error(f"❌ Error retransmitting message: {e}")
                    else:
                        logger.error(f"❌ Message {msg_id[:8]} failed after {self.max_retries} retries")
                        del self.pending_acks[msg_id]
    
    def listen(self):
        """Start listening for messages"""
        self.running = True
        
        # Start timeout checker in separate thread
        self.timeout_thread = threading.Thread(target=self._timeout_checker, daemon=True)
        self.timeout_thread.start()
        
        logger.info("👂 In-memory broker listening for messages...")
    
    def _timeout_checker(self):
        """Background thread to check for timeouts"""
        while self.running:
            try:
                self.check_timeouts()
                time.sleep(1)
            except Exception as e:
                if self.running:
                    logger.error(f"❌ Error in timeout checker: {e}")
    
    def stop(self):
        """Stop the broker gracefully"""
        if not self.running:
            return
            
        logger.info("🛑 Stopping broker...")
        self.running = False
        
        # Give threads a moment to finish
        time.sleep(0.5)
        
        logger.info("✅ Broker stopped successfully")


class ReliableBroker:
    """Broker that uses Redis if available, otherwise falls back to in-memory"""
    def __init__(self, host='localhost', port=6379, use_redis=None):
        """
        Initialize broker
        Args:
            host: Redis host (if using Redis)
            port: Redis port (if using Redis)
            use_redis: Force Redis usage (True) or in-memory (False). None = auto-detect
        """
        self.use_redis = use_redis
        
        # Auto-detect: try Redis if available and not explicitly disabled
        if self.use_redis is None:
            if REDIS_AVAILABLE:
                try:
                    test_client = redis.Redis(host=host, port=port, decode_responses=True, socket_connect_timeout=1)
                    test_client.ping()
                    test_client.close()
                    self.use_redis = True
                    logger.info("✅ Redis server detected, using Redis broker")
                except Exception:
                    self.use_redis = False
                    logger.warning("⚠️ Redis server not available, using in-memory broker")
            else:
                self.use_redis = False
                logger.info("ℹ️ Redis library not available, using in-memory broker")
        
        if self.use_redis:
            # Use Redis-based broker
            self.redis_client = redis.Redis(host=host, port=port, decode_responses=True)
            self.pubsub = self.redis_client.pubsub()
            self.subscribers = {}  # channel -> list of callbacks (for fan-out)
            self.pending_acks = {}  # Messages waiting for acknowledgment
            self.ack_timeout = 5  # seconds
            self.max_retries = 3
            self.running = False
            self.listen_thread = None
            self.timeout_thread = None
            
            # Subscribe to acks channel for handling acknowledgments
            self.pubsub.subscribe('acks')
        else:
            # Use in-memory broker
            self.broker = InMemoryBroker()
            logger.info("📦 Using in-memory message broker (no Redis required)")
    
    def publish(self, channel: str, message: dict, reliable: bool = False):
        """Publish message to a channel"""
        if self.use_redis:
            if not self.running:
                return
                
            msg_data = json.dumps(message)
            
            if reliable and message.get('requires_ack'):
                msg_id = message.get('msg_id')
                self.pending_acks[msg_id] = {
                    'channel': channel,
                    'message': message,
                    'sent_at': time.time(),
                    'retries': 0
                }
                logger.info(f"📤 Sent reliable message {msg_id[:8]} to {channel}")
            
            try:
                self.redis_client.publish(channel, msg_data)
            except Exception as e:
                logger.error(f"❌ Error publishing message: {e}")
        else:
            self.broker.publish(channel, message, reliable)
    
    def subscribe(self, channel: str, callback: Callable):
        """Subscribe to a channel with a callback (supports multiple subscribers per channel)"""
        if self.use_redis:
            # Initialize channel list if it doesn't exist
            if channel not in self.subscribers:
                self.subscribers[channel] = []
                self.pubsub.subscribe(channel)
                logger.info(f"📡 Subscribed to channel: {channel}")
            
            # Add callback to the list (multiple callbacks per channel)
            self.subscribers[channel].append(callback)
            logger.info(f"📡 Added subscriber to {channel} (total: {len(self.subscribers[channel])})")
        else:
            self.broker.subscribe(channel, callback)
    
    def handle_ack(self, msg_id: str):
        """Handle acknowledgment of a message"""
        if self.use_redis:
            if msg_id in self.pending_acks:
                logger.info(f"✅ Received ACK for message {msg_id[:8]}")
                del self.pending_acks[msg_id]
        else:
            self.broker.handle_ack(msg_id)
    
    def check_timeouts(self):
        """Check for messages that need retransmission"""
        if self.use_redis:
            if not self.running:
                return
                
            current_time = time.time()
            for msg_id, info in list(self.pending_acks.items()):
                if current_time - info['sent_at'] > self.ack_timeout:
                    if info['retries'] < self.max_retries:
                        logger.warning(f"⏱️ Timeout for message {msg_id[:8]}, retransmitting (retry {info['retries'] + 1})")
                        try:
                            self.redis_client.publish(info['channel'], json.dumps(info['message']))
                            info['retries'] += 1
                            info['sent_at'] = current_time
                        except Exception as e:
                            logger.error(f"❌ Error retransmitting message: {e}")
                    else:
                        logger.error(f"❌ Message {msg_id[:8]} failed after {self.max_retries} retries")
                        del self.pending_acks[msg_id]
        else:
            self.broker.check_timeouts()
    
    def listen(self):
        """Start listening for messages"""
        if self.use_redis:
            self.running = True
            
            # Start timeout checker in separate thread
            self.timeout_thread = threading.Thread(target=self._timeout_checker, daemon=True)
            self.timeout_thread.start()
            
            logger.info("👂 Broker listening for messages...")
            
            try:
                for message in self.pubsub.listen():
                    if not self.running:
                        break
                        
                    if message['type'] == 'message':
                        channel = message['channel']
                        
                        try:
                            data = json.loads(message['data'])
                        except json.JSONDecodeError:
                            logger.error(f"❌ Failed to decode message on channel {channel}")
                            continue
                        
                        # Handle ACK messages specially
                        if channel == 'acks':
                            if data.get('msg_type') == 'acknowledgment':
                                self.handle_ack(data.get('ack_for'))
                            continue
                        
                        # Handle regular acknowledgment messages on any channel
                        if data.get('msg_type') == 'acknowledgment':
                            self.handle_ack(data.get('ack_for'))
                            continue
                        
                        # Call ALL subscriber callbacks for the channel (fan-out pattern)
                        if channel in self.subscribers:
                            for callback in self.subscribers[channel]:
                                try:
                                    callback(data)
                                except Exception as e:
                                    logger.error(f"❌ Error in subscriber callback for {channel}: {e}")
            except Exception as e:
                if self.running:  # Only log if we didn't intentionally stop
                    logger.error(f"❌ Error in listen loop: {e}")
            finally:
                logger.info("🛑 Broker stopped listening")
        else:
            self.broker.listen()
    
    def _timeout_checker(self):
        """Background thread to check for timeouts"""
        if self.use_redis:
            while self.running:
                try:
                    self.check_timeouts()
                    time.sleep(1)
                except Exception as e:
                    if self.running:
                        logger.error(f"❌ Error in timeout checker: {e}")
    
    def stop(self):
        """Stop the broker gracefully"""
        if self.use_redis:
            if not self.running:
                return
                
            logger.info("🛑 Stopping broker...")
            self.running = False
            
            # Give threads a moment to finish their current iteration
            time.sleep(0.5)
            
            try:
                # Unsubscribe from all channels
                if self.pubsub:
                    self.pubsub.unsubscribe()
                    self.pubsub.close()
                    logger.info("✅ PubSub connection closed")
            except Exception as e:
                logger.error(f"⚠️ Error closing pubsub: {e}")
            
            try:
                # Close Redis connection
                if self.redis_client:
                    self.redis_client.close()
                    logger.info("✅ Redis connection closed")
            except Exception as e:
                logger.error(f"⚠️ Error closing redis client: {e}")
            
            logger.info("✅ Broker stopped successfully")
        else:
            self.broker.stop()
