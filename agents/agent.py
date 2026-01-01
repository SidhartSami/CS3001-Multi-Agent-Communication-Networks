import time
import random
import uuid
import threading
from communication.broker import ReliableBroker
from communication.message_types import Message, MessageType, Task, Bid, Heartbeat, AgentDataStream
import logging

logger = logging.getLogger(__name__)

class Agent:
    def __init__(self, agent_id: str, broker: ReliableBroker):
        self.agent_id = agent_id
        self.broker = broker
        self.current_load = 0
        self.max_load = 5
        self.assigned_tasks = []
        self.completed_tasks = []
        self.running_tasks = {}  # task_id -> {'start_time': float, 'stop_flag': threading.Event}
        self.allocated_task_ids = set()
        self.processed_message_ids = set()
        self.bid_task_ids = set()
        self.message_lock = threading.Lock()
        self.is_alive = True
        self.is_crashed = False
        self.auto_recover_enabled = True
        self.auto_recover_delay = 10.0
        self.crash_time = None
        self.last_heartbeat = time.time()
        self.heartbeat_interval = 2.0
        self.stream_interval = 1.0
        self.total_cpu_time = 0.0
        self.total_memory_used = 0.0
        
        # Subscribe to channels
        self.broker.subscribe('tasks', self.handle_task_broadcast)
        self.broker.subscribe('allocations', self.handle_task_allocation)
        self.broker.subscribe('heartbeat_request', self.handle_heartbeat_request)
        
        # Start heartbeat and data streaming threads
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self.stream_thread = threading.Thread(target=self._data_stream_loop, daemon=True)
        self.heartbeat_thread.start()
        self.stream_thread.start()
        
        logger.info(f"🤖 Agent {self.agent_id} initialized with heartbeat and data streaming")
        self.emit_event("agent_started", {})
    
    def emit_event(self, event_type: str, payload: dict):
        """Emit a lightweight agent event to the 'agent_events' channel for coordinator/dashboard"""
        try:
            message = Message(
                msg_id=str(uuid.uuid4()),
                msg_type=MessageType.AGENT_EVENT,
                sender_id=self.agent_id,
                payload={
                    "event_type": event_type,
                    "data": payload
                },
                requires_ack=False
            )
            self.broker.publish('agent_events', message.to_dict())
        except Exception as e:
            logger.error(f"❌ Failed to emit event {event_type} from {self.agent_id}: {e}")

    def handle_task_broadcast(self, message_data: dict):
        """Handle incoming task broadcast"""
        if message_data['msg_type'] != MessageType.TASK_BROADCAST.value:
            return
        
        # Thread-safe message processing
        with self.message_lock:
            msg_id = message_data.get('msg_id')
            
            if msg_id and msg_id in self.processed_message_ids:
                return
            
            if msg_id:
                self.processed_message_ids.add(msg_id)
        
        if self.is_crashed:
            logger.warning(f"⚠️ Agent {self.agent_id} is crashed, ignoring task broadcast")
            if message_data.get('requires_ack'):
                self.send_ack(message_data['msg_id'])
            return
        
        task_data = message_data['payload']['task']
        task = Task(**task_data)
        task_id = task.task_id
        
        with self.message_lock:
            if task_id in self.bid_task_ids or task_id in self.allocated_task_ids:
                logger.debug(f"🤖 Agent {self.agent_id} already interacted with task {task_id}, skipping")
                if message_data.get('requires_ack'):
                    self.send_ack(message_data['msg_id'])
                return
            
            self.bid_task_ids.add(task_id)
        
        logger.info(f"🤖 Agent {self.agent_id} received task {task.task_id}")
        
        if message_data.get('requires_ack'):
            self.send_ack(message_data['msg_id'])
        
        if self.current_load < self.max_load:
            self.send_bid(task)
        else:
            logger.info(f"🤖 Agent {self.agent_id} too busy, not bidding")
    
    def send_bid(self, task: Task):
        """Send bid for a task"""
        base_bid = self.current_load * 10
        random_factor = random.uniform(0, 5)
        bid_value = base_bid + random_factor
        
        bid = Bid(
            agent_id=self.agent_id,
            task_id=task.task_id,
            bid_value=bid_value,
            current_load=self.current_load,
            estimated_completion_time=task.estimated_time
        )
        
        message = Message(
            msg_id=str(uuid.uuid4()),
            msg_type=MessageType.BID,
            sender_id=self.agent_id,
            payload={'bid': bid.to_dict()},
            requires_ack=False
        )
        
        self.broker.publish('bids', message.to_dict())
        logger.info(f"💰 Agent {self.agent_id} bid {bid_value:.2f} for task {task.task_id}")
    
    def handle_task_allocation(self, message_data: dict):
        """Handle task allocation"""
        if message_data['msg_type'] != MessageType.TASK_ALLOCATION.value:
            return
        
        allocated_agent = message_data['payload']['agent_id']
        
        if allocated_agent != self.agent_id:
            return
        
        with self.message_lock:
            msg_id = message_data.get('msg_id')
            
            if msg_id and msg_id in self.processed_message_ids:
                return
            
            task_data = message_data['payload']['task']
            task = Task(**task_data)
            task_id = task.task_id
            
            if task_id in self.allocated_task_ids:
                logger.warning(f"⚠️ Agent {self.agent_id} already allocated task {task_id}, ignoring duplicate")
                if message_data.get('requires_ack'):
                    self.send_ack(msg_id)
                return
            
            if msg_id:
                self.processed_message_ids.add(msg_id)
            self.allocated_task_ids.add(task_id)
            self.assigned_tasks.append(task)
            self.current_load += 1
        
        if self.is_crashed:
            logger.warning(f"⚠️ Agent {self.agent_id} is crashed, rejecting task allocation")
            with self.message_lock:
                self.allocated_task_ids.discard(task_id)
                self.current_load -= 1
            if message_data.get('requires_ack'):
                self.send_ack(msg_id)
            return
        
        logger.info(f"✅ Agent {self.agent_id} received task {task_id}")
        
        if message_data.get('requires_ack'):
            self.send_ack(msg_id)
        
        threading.Thread(target=self.execute_task, args=(task,), daemon=True).start()
    
    def execute_task(self, task: Task):
        """Simulate task execution with proper crash handling"""
        logger.info(f"⚙️ Agent {self.agent_id} executing task {task.task_id}")
        start_time = time.time()
        
        # Create a stop flag for this task
        stop_flag = threading.Event()
        
        with self.message_lock:
            self.running_tasks[task.task_id] = {
                'start_time': start_time,
                'stop_flag': stop_flag
            }
        
        try:
            # Execute task in small increments, checking for crash
            elapsed = 0
            check_interval = 0.1
            
            while elapsed < task.estimated_time:
                # Check if we should stop (due to crash)
                if stop_flag.is_set() or self.is_crashed:
                    logger.warning(f"🛑 Agent {self.agent_id} task {task.task_id} cancelled due to crash")
                    with self.message_lock:
                        self.current_load -= 1
                        if task.task_id in self.running_tasks:
                            del self.running_tasks[task.task_id]
                        self.allocated_task_ids.discard(task.task_id)
                        self.bid_task_ids.discard(task.task_id)
                    self.emit_event("task_cancelled", {"task_id": task.task_id, "elapsed": elapsed})
                    return
                
                sleep_time = min(check_interval, task.estimated_time - elapsed)
                time.sleep(sleep_time)
                elapsed += sleep_time
            
            # Double-check we're not crashed before completing
            if self.is_crashed:
                logger.warning(f"🛑 Agent {self.agent_id} crashed just before completing task {task.task_id}")
                with self.message_lock:
                    self.current_load -= 1
                    if task.task_id in self.running_tasks:
                        del self.running_tasks[task.task_id]
                    self.allocated_task_ids.discard(task.task_id)
                    self.bid_task_ids.discard(task.task_id)
                self.emit_event("task_cancelled", {"task_id": task.task_id})
                return
            
            # Task completed successfully
            with self.message_lock:
                self.current_load -= 1
                self.completed_tasks.append(task)
            
            execution_time = time.time() - start_time
            self.total_cpu_time += execution_time
            logger.info(f"✔️ Agent {self.agent_id} completed task {task.task_id}")
            self.emit_event("task_completed", {"task_id": task.task_id, "execution_time": execution_time})
            
        except Exception as e:
            logger.error(f"❌ Agent {self.agent_id} failed to execute task {task.task_id}: {e}")
            with self.message_lock:
                self.current_load -= 1
            self.emit_event("task_failed", {"task_id": task.task_id, "error": str(e)})
        finally:
            with self.message_lock:
                if task.task_id in self.running_tasks:
                    del self.running_tasks[task.task_id]
                # Only remove from allocated if completed, not if crashed
                if not self.is_crashed:
                    self.allocated_task_ids.discard(task.task_id)
    
    def send_ack(self, msg_id: str):
        """Send acknowledgment"""
        ack_message = {
            'msg_type': 'acknowledgment',
            'ack_for': msg_id,
            'sender_id': self.agent_id,
            'timestamp': time.time()
        }
        self.broker.publish('acks', ack_message)
    
    def _heartbeat_loop(self):
        """Continuously send heartbeat messages"""
        while self.is_alive:
            try:
                if self.is_crashed and self.auto_recover_enabled and self.crash_time:
                    time_since_crash = time.time() - self.crash_time
                    if time_since_crash >= self.auto_recover_delay:
                        logger.info(f"🔄 Agent {self.agent_id} automatically recovering after {time_since_crash:.1f}s...")
                        self.recover()
                
                if not self.is_crashed:
                    self.send_heartbeat()
                time.sleep(self.heartbeat_interval)
            except Exception as e:
                logger.error(f"❌ Error in heartbeat loop for {self.agent_id}: {e}")
                time.sleep(self.heartbeat_interval)
    
    def send_heartbeat(self):
        """Send heartbeat to indicate agent is alive"""
        status = "idle" if self.current_load == 0 else "busy" if self.current_load < self.max_load else "overloaded"
        
        heartbeat = Heartbeat(
            agent_id=self.agent_id,
            timestamp=time.time(),
            status=status,
            current_load=self.current_load,
            max_load=self.max_load
        )
        
        message = Message(
            msg_id=str(uuid.uuid4()),
            msg_type=MessageType.HEARTBEAT,
            sender_id=self.agent_id,
            payload={'heartbeat': heartbeat.to_dict()},
            requires_ack=False
        )
        
        self.broker.publish('heartbeats', message.to_dict())
        self.last_heartbeat = time.time()
    
    def handle_heartbeat_request(self, message_data: dict):
        """Handle heartbeat request from coordinator"""
        if message_data.get('msg_type') == 'heartbeat_request':
            self.send_heartbeat()
    
    def _data_stream_loop(self):
        """Continuously stream agent data (metrics, status)"""
        while self.is_alive:
            try:
                self.send_data_stream()
                time.sleep(self.stream_interval)
            except Exception as e:
                logger.error(f"❌ Error in data stream loop for {self.agent_id}: {e}")
                time.sleep(self.stream_interval)
    
    def send_data_stream(self):
        """Send agent-generated data stream"""
        with self.message_lock:
            utilization = (self.current_load / self.max_load) * 100 if self.max_load > 0 else 0
            avg_task_time = self.total_cpu_time / len(self.completed_tasks) if self.completed_tasks else 0
            running_tasks_copy = list(self.running_tasks.keys())
            current_load = self.current_load
            completed_count = len(self.completed_tasks)
            assigned_count = len(self.assigned_tasks)
        
        memory_usage = random.uniform(100, 500) + (current_load * 50)
        
        stream_data = AgentDataStream(
            agent_id=self.agent_id,
            stream_type="metrics",
            data={
                'cpu_utilization': utilization,
                'memory_usage_mb': memory_usage,
                'active_tasks': current_load,
                'completed_tasks_count': completed_count,
                'avg_task_time': avg_task_time,
                'running_tasks': running_tasks_copy,
                'queue_length': assigned_count - current_load
            },
            timestamp=time.time()
        )
        
        message = Message(
            msg_id=str(uuid.uuid4()),
            msg_type=MessageType.HEARTBEAT,
            sender_id=self.agent_id,
            payload={'stream': stream_data.to_dict()},
            requires_ack=False
        )
        
        self.broker.publish('agent_streams', message.to_dict())
    
    def crash(self, auto_recover_after: float = None):
        """Simulate agent crash - stops all running tasks immediately"""
        with self.message_lock:
            self.is_crashed = True
            self.crash_time = time.time()
            
            # Get list of running tasks and stop them
            running_tasks_copy = list(self.running_tasks.keys())
            
            # Set stop flags for all running tasks
            for task_id, task_info in self.running_tasks.items():
                if 'stop_flag' in task_info:
                    task_info['stop_flag'].set()
        
        if auto_recover_after is not None:
            if auto_recover_after == 0:
                self.auto_recover_enabled = False
            else:
                self.auto_recover_delay = auto_recover_after
        
        logger.warning(f"💥 Agent {self.agent_id} CRASHED (simulated)")
        self.emit_event("agent_crashed", {
            "crash_time": self.crash_time,
            "active_running_tasks": running_tasks_copy
        })
        
        if running_tasks_copy:
            logger.warning(f"🛑 Agent {self.agent_id} stopping {len(running_tasks_copy)} running task(s): {running_tasks_copy}")
        
        if self.auto_recover_enabled:
            logger.info(f"⏰ Agent {self.agent_id} will auto-recover in {self.auto_recover_delay:.1f}s")
    
    def recover(self):
        """Recover agent from crash"""
        with self.message_lock:
            if self.is_crashed:
                self.is_crashed = False
                self.crash_time = None
                self.last_heartbeat = time.time()
                # Clear bid history to allow bidding on new tasks after recovery
                self.bid_task_ids.clear()
                logger.info(f"✅ Agent {self.agent_id} RECOVERED")
                self.emit_event("agent_recovered", {"recovered_at": time.time()})
                self.send_heartbeat()
                return True
        return False
    
    def stop(self):
        """Stop agent gracefully"""
        self.is_alive = False
        self.is_crashed = False
        logger.info(f"🛑 Agent {self.agent_id} stopping")
    
    def get_status(self):
        """Get agent status"""
        with self.message_lock:
            return {
                'agent_id': self.agent_id,
                'current_load': self.current_load,
                'max_load': self.max_load,
                'assigned_tasks': len(self.assigned_tasks),
                'completed_tasks': len(self.completed_tasks),
                'is_alive': self.is_alive,
                'is_crashed': self.is_crashed,
                'last_heartbeat': self.last_heartbeat,
                'running_tasks': list(self.running_tasks.keys())
            }