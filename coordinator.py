import time
import threading
import random
from typing import List, Dict, Optional
from communication.broker import ReliableBroker
from communication.message_types import Message, MessageType, Task
import uuid
import logging

logger = logging.getLogger(__name__)

class Coordinator:
    def __init__(self, broker: ReliableBroker):
        self.broker = broker
        self.tasks = []
        self.pending_tasks = {}  # task_id -> bids
        self.allocated_tasks = []
        self.agent_tasks = {}
        self.agent_heartbeats = {}
        self.agent_streams = {}
        self.failed_agents = set()
        self.heartbeat_timeout = 6.0
        self.monitoring_active = True
        
        # Event tracking for dashboard visualization
        self.activity_log = []
        self.max_activity_log = 100
        self.activity_lock = threading.Lock()
        self.processed_events = set()
        
        # Store all bids for each task for fallback allocation
        self.task_bids = {}  # task_id -> sorted list of bids
        
        # Track completed and cancelled tasks
        self.completed_task_ids = set()
        self.cancelled_task_ids = set()
        
        # Subscribe to channels
        self.broker.subscribe('bids', self.handle_bid)
        self.broker.subscribe('heartbeats', self.handle_heartbeat)
        self.broker.subscribe('agent_streams', self.handle_agent_stream)
        self.broker.subscribe('agent_events', self.handle_agent_event)
        
        # Start monitoring thread
        self.monitor_thread = threading.Thread(target=self._monitor_agents, daemon=True)
        self.monitor_thread.start()
        
        logger.info("🎯 Coordinator initialized with fault tolerance and stream monitoring")
    
    def broadcast_task(self, task: Task, reliable: bool = True):
        """Broadcast a new task to all agents"""
        message = Message(
            msg_id=str(uuid.uuid4()),
            msg_type=MessageType.TASK_BROADCAST,
            sender_id='coordinator',
            payload={'task': task.to_dict()},
            requires_ack=reliable
        )
        
        self.tasks.append(task)
        self.pending_tasks[task.task_id] = {
            'task': task,
            'bids': [],
            'broadcast_at': time.time()
        }
        
        logger.info(f"📢 Broadcasting task {task.task_id}: {task.description}")
        self.broker.publish('tasks', message.to_dict(), reliable=reliable)
        
        # Log activity for dashboard
        self._log_activity({
            'type': 'task_broadcast',
            'task_id': task.task_id,
            'priority': task.priority,
            'description': task.description,
            'timestamp': time.time()
        })
        
        # Wait for bids and allocate
        threading.Thread(target=self._allocate_after_delay, args=(task.task_id,), daemon=True).start()
    
    def handle_bid(self, message_data: dict):
        """Handle incoming bids"""
        if message_data['msg_type'] != MessageType.BID.value:
            return
        
        bid_data = message_data['payload']['bid']
        agent_id = bid_data['agent_id']
        task_id = bid_data['task_id']
        
        # Don't reject bids from failed agents here - they might still be alive
        # We'll handle failed agents during allocation
        
        if task_id in self.pending_tasks:
            # Check if this agent already bid on this task
            existing_bids = [b for b in self.pending_tasks[task_id]['bids'] if b['agent_id'] == agent_id]
            if existing_bids:
                logger.debug(f"⚠️ Agent {agent_id} already bid on task {task_id}, ignoring duplicate")
                return
            
            self.pending_tasks[task_id]['bids'].append(bid_data)
            logger.info(f"💰 Received bid from {agent_id} for task {task_id}: {bid_data['bid_value']:.2f}")
            
            # Log activity for dashboard
            self._log_activity({
                'type': 'bid',
                'agent_id': agent_id,
                'task_id': task_id,
                'bid_value': bid_data['bid_value'],
                'timestamp': time.time()
            })
    
    def _allocate_after_delay(self, task_id: str, wait_time: float = 2.0):
        """Wait for bids and then allocate task"""
        time.sleep(wait_time)
        self.allocate_task(task_id)
    
    def allocate_task(self, task_id: str):
        """Allocate task to the agent with lowest bid"""
        if task_id not in self.pending_tasks:
            logger.warning(f"⚠️ Task {task_id} not found in pending")
            return
        
        # Check if task was already completed or cancelled
        if task_id in self.completed_task_ids:
            logger.info(f"ℹ️ Task {task_id} already completed, skipping allocation")
            del self.pending_tasks[task_id]
            return
        
        if task_id in self.cancelled_task_ids:
            logger.info(f"ℹ️ Task {task_id} was cancelled, skipping allocation")
            del self.pending_tasks[task_id]
            return
        
        task_info = self.pending_tasks[task_id]
        bids = task_info['bids']
        
        # Filter out bids from failed agents ONLY at allocation time
        valid_bids = [bid for bid in bids if bid['agent_id'] not in self.failed_agents]
        
        if not valid_bids:
            logger.warning(f"⚠️ No valid bids received for task {task_id}")
            # Still try to allocate to ANY bidder if all are failed
            if bids:
                logger.info(f"ℹ️ All bidders failed, will reallocate when agents recover")
                return
            return
        
        # Sort bids by value (lowest first) and STORE for future fallback
        sorted_bids = sorted(valid_bids, key=lambda x: x['bid_value'])
        self.task_bids[task_id] = sorted_bids  # Save all bids for potential reassignment
        
        winning_bid = sorted_bids[0]
        winner_id = winning_bid['agent_id']
        
        # Send allocation
        self._send_allocation(task_info['task'], winner_id, winning_bid, len(bids))
        
        # Remove from pending
        del self.pending_tasks[task_id]
    
    def _send_allocation(self, task: Task, agent_id: str, winning_bid: dict, total_bids: int):
        """Send task allocation to an agent"""
        message = Message(
            msg_id=str(uuid.uuid4()),
            msg_type=MessageType.TASK_ALLOCATION,
            sender_id='coordinator',
            payload={
                'task': task.to_dict(),
                'agent_id': agent_id,
                'winning_bid': winning_bid
            },
            requires_ack=True
        )
        
        self.broker.publish('allocations', message.to_dict(), reliable=True)
        self.allocated_tasks.append({
            'task': task,
            'agent': agent_id,
            'bid_value': winning_bid['bid_value'],
            'allocated_at': time.time()
        })
        
        # Track which tasks are assigned to which agent
        if agent_id not in self.agent_tasks:
            self.agent_tasks[agent_id] = []
        self.agent_tasks[agent_id].append(task.task_id)
        
        logger.info(f"🏆 Task {task.task_id} allocated to {agent_id} (bid: {winning_bid['bid_value']:.2f})")
        
        # Log activity for dashboard
        self._log_activity({
            'type': 'allocation',
            'task_id': task.task_id,
            'agent_id': agent_id,
            'bid_value': winning_bid['bid_value'],
            'total_bids': total_bids,
            'timestamp': time.time()
        })
    
    def handle_heartbeat(self, message_data: dict):
        """Handle heartbeat from agent"""
        if message_data.get('msg_type') != MessageType.HEARTBEAT.value:
            return
        
        heartbeat_data = message_data.get('payload', {}).get('heartbeat', {})
        if not heartbeat_data:
            return
        
        agent_id = heartbeat_data.get('agent_id')
        if agent_id:
            self.agent_heartbeats[agent_id] = time.time()
            
            # If agent was marked as failed, remove from failed set
            if agent_id in self.failed_agents:
                logger.info(f"✅ Agent {agent_id} recovered!")
                self.failed_agents.discard(agent_id)
                
                # Log recovery activity
                self._log_activity({
                    'type': 'agent_recovery',
                    'agent_id': agent_id,
                    'timestamp': time.time()
                })
    
    def handle_agent_stream(self, message_data: dict):
        """Handle agent data stream"""
        stream_data = message_data.get('payload', {}).get('stream', {})
        if not stream_data:
            return
        
        agent_id = stream_data.get('agent_id')
        if agent_id:
            self.agent_streams[agent_id] = {
                'data': stream_data.get('data', {}),
                'timestamp': stream_data.get('timestamp', time.time()),
                'stream_type': stream_data.get('stream_type', 'unknown')
            }
    
    def handle_agent_event(self, message_data: dict):
        """Handle events emitted by agents (task_started, task_completed, task_cancelled, etc)"""
        try:
            payload = message_data.get('payload', {}) or {}
            event_type = payload.get('event_type') or payload.get('type')
            data = payload.get('data', {})
            agent_id = message_data.get('sender_id', 'unknown')
            timestamp = time.time()
            
            # Track completed tasks
            if event_type == 'task_completed':
                task_id = data.get('task_id')
                if task_id:
                    self.completed_task_ids.add(task_id)
                    # Clean up stored bids for completed tasks
                    if task_id in self.task_bids:
                        del self.task_bids[task_id]
                    logger.info(f"✅ Task {task_id} marked as completed by {agent_id}")
            
            # Track cancelled tasks (from crashed agents)
            elif event_type == 'task_cancelled':
                task_id = data.get('task_id')
                if task_id:
                    self.cancelled_task_ids.add(task_id)
                    logger.info(f"🚫 Task {task_id} marked as cancelled by {agent_id}")
            
            # Create unique event ID to prevent duplicates
            event_id = f"{agent_id}_{event_type}_{data.get('task_id', '')}_{int(timestamp * 1000)}"
            
            # Skip if we've already processed this event
            with self.activity_lock:
                if event_id in self.processed_events:
                    return
                self.processed_events.add(event_id)
                
                # Clean up old processed events (keep last 1000)
                if len(self.processed_events) > 1000:
                    self.processed_events.clear()
            
            # Normalize event for activity log
            activity = {
                'type': event_type,
                'agent_id': agent_id,
                'timestamp': timestamp
            }
            
            # Merge data keys into activity for rendering convenience
            if isinstance(data, dict):
                activity.update(data)
            
            # Filter out certain noisy events from activity log
            if event_type not in ['task_received', 'bid_skipped']:
                self._log_activity(activity)
            
            logger.debug(f"📣 Received agent event '{event_type}' from {agent_id}: {data}")
        except Exception as e:
            logger.error(f"❌ Error handling agent event: {e}")
    
    def _monitor_agents(self):
        """Monitor agent health and detect failures"""
        while self.monitoring_active:
            try:
                current_time = time.time()
                
                # Check all known agents
                for agent_id, last_heartbeat in list(self.agent_heartbeats.items()):
                    time_since_heartbeat = current_time - last_heartbeat
                    
                    if time_since_heartbeat > self.heartbeat_timeout:
                        # Double-check to prevent race conditions
                        if agent_id not in self.failed_agents:
                            self.failed_agents.add(agent_id)
                            logger.warning(f"⚠️ Agent {agent_id} failed! No heartbeat for {time_since_heartbeat:.1f}s")
                            self._handle_agent_failure(agent_id)
                
                time.sleep(1.0)
            except Exception as e:
                logger.error(f"❌ Error in agent monitoring: {e}")
                time.sleep(1.0)
    
    def _handle_agent_failure(self, agent_id: str):
        """Handle agent failure by reassigning its tasks to next best bidder or rebroadcasting"""
        if agent_id not in self.agent_tasks:
            return
        
        failed_tasks = self.agent_tasks[agent_id].copy()
        
        if not failed_tasks:
            del self.agent_tasks[agent_id]
            return
        
        # Get agent's latest stream data
        agent_stream = self.agent_streams.get(agent_id, {})
        stream_data = agent_stream.get('data', {})
        running_tasks_list = stream_data.get('running_tasks', [])
        
        tasks_to_reassign = []
        completed_tasks = []
        
        logger.warning(f"🔍 Checking {len(failed_tasks)} task(s) from failed agent {agent_id}")
        
        for task_id in failed_tasks:
            # Check if task was already completed
            if task_id in self.completed_task_ids:
                completed_tasks.append(task_id)
                logger.info(f"✅ Task {task_id} already completed, no reassignment needed")
                continue
            
            # Check if task was cancelled (stopped mid-execution)
            if task_id in self.cancelled_task_ids:
                tasks_to_reassign.append(task_id)
                logger.info(f"🔄 Task {task_id} was cancelled, needs reassignment")
                continue
            
            # If task is in running_tasks or recently allocated, it needs reassignment
            tasks_to_reassign.append(task_id)
            logger.info(f"🔄 Task {task_id} needs reassignment from failed agent {agent_id}")
        
        if not tasks_to_reassign:
            logger.info(f"ℹ️ All tasks from failed agent {agent_id} were completed, no reassignment needed")
            # Remove completed allocations
            self.allocated_tasks = [
                alloc for alloc in self.allocated_tasks 
                if not (alloc.get('agent') == agent_id and alloc.get('task').task_id in completed_tasks)
            ]
            del self.agent_tasks[agent_id]
            return
        
        logger.warning(f"🔄 Reassigning {len(tasks_to_reassign)} incomplete task(s) from failed agent {agent_id}")
        
        # Log activity for dashboard
        self._log_activity({
            'type': 'agent_failure',
            'agent_id': agent_id,
            'failed_tasks': len(tasks_to_reassign),
            'completed_tasks': len(completed_tasks),
            'timestamp': time.time()
        })
        
        # Remove failed agent's allocations for tasks that need reassignment
        self.allocated_tasks = [
            alloc for alloc in self.allocated_tasks 
            if not (alloc.get('agent') == agent_id and alloc.get('task').task_id in tasks_to_reassign)
        ]
        
        # Reassign each incomplete task to NEXT BEST BIDDER or rebroadcast
        for task_id in tasks_to_reassign:
            # Remove from cancelled set to allow reassignment
            self.cancelled_task_ids.discard(task_id)
            self._reassign_to_next_bidder(task_id, agent_id)
        
        # Clear agent's task list
        del self.agent_tasks[agent_id]
    
    def _reassign_to_next_bidder(self, task_id: str, failed_agent_id: str):
        """Reassign task to the next lowest bidder, or rebroadcast if no bidders available"""
        # Check if we have stored bids for this task
        if task_id not in self.task_bids:
            logger.warning(f"⚠️ No bids stored for task {task_id}, will rebroadcast")
            self._rebroadcast_task_with_delay(task_id)
            return
        
        # Get all bids for this task (already sorted by bid_value)
        all_bids = self.task_bids[task_id]
        
        # Filter out the failed agent and any other failed agents
        valid_bids = [
            bid for bid in all_bids 
            if bid['agent_id'] not in self.failed_agents
        ]
        
        if not valid_bids:
            logger.warning(f"⚠️ No valid alternative bidders for task {task_id}, will rebroadcast")
            self._rebroadcast_task_with_delay(task_id)
            return
        
        # Get the next best bidder (lowest bid among remaining agents)
        next_bidder = valid_bids[0]
        next_agent_id = next_bidder['agent_id']
        
        # Find the task object
        task = self._find_task(task_id)
        if not task:
            logger.error(f"❌ Task {task_id} not found for reassignment")
            return
        
        logger.info(f"🏆 Reassigning task {task_id} to next best bidder: {next_agent_id} (bid: {next_bidder['bid_value']:.2f})")
        
        # Send allocation to next bidder
        self._send_allocation(task, next_agent_id, next_bidder, len(all_bids))
        
        # Log reassignment
        self._log_activity({
            'type': 'task_reassignment',
            'task_id': task_id,
            'failed_agent': failed_agent_id,
            'new_agent': next_agent_id,
            'new_bid': next_bidder['bid_value'],
            'timestamp': time.time()
        })
    
    def _rebroadcast_task_with_delay(self, task_id: str):
        """Rebroadcast a task after a random delay (5-10 seconds) to allow agent recovery"""
        # Find the task object
        task = self._find_task(task_id)
        if not task:
            logger.error(f"❌ Task {task_id} not found for rebroadcast")
            return
        
        # Random delay between 5 and 10 seconds
        delay = random.uniform(5.0, 10.0)
        
        logger.info(f"📢 Will rebroadcast task {task_id} after {delay:.1f}s delay (to allow agent recovery)")
        
        # Clean up old bids
        if task_id in self.task_bids:
            del self.task_bids[task_id]
        
        # Log rebroadcast intent
        self._log_activity({
            'type': 'task_rebroadcast_scheduled',
            'task_id': task_id,
            'delay': delay,
            'timestamp': time.time()
        })
        
        # Schedule rebroadcast in a separate thread
        def delayed_rebroadcast():
            time.sleep(delay)
            # Double-check task wasn't completed while waiting
            if task_id not in self.completed_task_ids:
                logger.info(f"📢 Rebroadcasting task {task_id} after delay")
                self.broadcast_task(task, reliable=True)
                self._log_activity({
                    'type': 'task_rebroadcast',
                    'task_id': task_id,
                    'timestamp': time.time()
                })
            else:
                logger.info(f"ℹ️ Task {task_id} was completed during delay, skipping rebroadcast")
        
        threading.Thread(target=delayed_rebroadcast, daemon=True).start()
    
    def _find_task(self, task_id: str) -> Optional[Task]:
        """Find a task by ID"""
        for task in self.tasks:
            if task.task_id == task_id:
                return task
        return None
    
    def request_heartbeat(self, agent_id: Optional[str] = None):
        """Request heartbeat from specific agent or all agents"""
        message = {
            'msg_type': 'heartbeat_request',
            'sender_id': 'coordinator',
            'timestamp': time.time(),
            'agent_id': agent_id
        }
        self.broker.publish('heartbeat_request', message)
    
    def get_stats(self):
        """Get coordinator statistics"""
        active_agents = len([a for a, hb in self.agent_heartbeats.items() 
                             if time.time() - hb < self.heartbeat_timeout])
        
        # Count truly pending tasks (not completed or cancelled)
        pending_count = len([
            task_id for task_id in self.pending_tasks.keys()
            if task_id not in self.completed_task_ids and task_id not in self.cancelled_task_ids
        ])
        
        # Count allocated but not completed tasks
        allocated_count = len([
            alloc for alloc in self.allocated_tasks
            if alloc['task'].task_id not in self.completed_task_ids
        ])
        
        return {
            'total_tasks': len(self.tasks),
            'pending_tasks': pending_count,
            'allocated_tasks': allocated_count,
            'completed_tasks': len(self.completed_task_ids),
            'active_agents': active_agents,
            'failed_agents': len(self.failed_agents),
            'total_agents': len(self.agent_heartbeats)
        }
    
    def get_agent_status(self):
        """Get status of all agents"""
        current_time = time.time()
        agent_statuses = {}
        
        for agent_id, last_heartbeat in self.agent_heartbeats.items():
            time_since_heartbeat = current_time - last_heartbeat
            is_alive = time_since_heartbeat < self.heartbeat_timeout
            
            # Count only active (not completed) tasks
            active_tasks = [
                task_id for task_id in self.agent_tasks.get(agent_id, [])
                if task_id not in self.completed_task_ids
            ]
            
            agent_statuses[agent_id] = {
                'is_alive': is_alive,
                'last_heartbeat': last_heartbeat,
                'time_since_heartbeat': time_since_heartbeat,
                'assigned_tasks': len(active_tasks),
                'stream_data': self.agent_streams.get(agent_id)
            }
        
        return agent_statuses
    
    def _log_activity(self, activity: dict):
        """Log activity for dashboard visualization (thread-safe)"""
        with self.activity_lock:
            self.activity_log.append(activity)
            # Keep only last N activities
            if len(self.activity_log) > self.max_activity_log:
                self.activity_log.pop(0)
    
    def get_recent_activity(self, limit: int = 20):
        """Get recent activities for dashboard (thread-safe)"""
        with self.activity_lock:
            return self.activity_log[-limit:] if self.activity_log else []
    
    def stop(self):
        """Stop coordinator monitoring"""
        self.monitoring_active = False
        logger.info("🛑 Coordinator monitoring stopped")