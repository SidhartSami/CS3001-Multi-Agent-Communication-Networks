import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import time
import random
from datetime import datetime
from communication.broker import ReliableBroker
from communication.message_types import Task
from agents.agent import Agent
from coordinator import Coordinator

class MultiAgentDashboard:
    def __init__(self, root):
        self.root = root
        self.root.title("🤖 Multi-Agent Network Simulation Dashboard")
        self.root.geometry("1600x900")
        
        # Session state
        self.broker = None
        self.coordinator = None
        self.agents = []
        self.running = False
        self.task_counter = 0
        self.num_agents = tk.IntVar(value=3)
        self.auto_refresh = tk.BooleanVar(value=False)
        self.refresh_interval = tk.IntVar(value=2)
        self.last_activity_index = 0
        
        # Setup UI
        self.setup_styles()
        self.setup_ui()
        
        # Auto-refresh loop
        self.auto_refresh_loop()
    
    def setup_styles(self):
        """Configure color scheme and styles"""
        self.colors = {
            'primary': '#667eea',
            'secondary': '#764ba2',
            'success': '#10b981',
            'warning': '#f59e0b',
            'danger': '#ef4444',
            'light': '#f8f9fa',
            'dark': '#1f2937',
            'bg': '#ffffff',
            'text': '#111827'
        }
        
        self.root.configure(bg='#f3f4f6')
    
    def setup_ui(self):
        """Setup main UI layout"""
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left sidebar
        self.setup_sidebar(main_frame)
        
        # Right content area
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))
        
        # Title
        title_label = tk.Label(content_frame, text="🤖 Multi-Agent Network Dashboard", 
                              font=("Helvetica", 20, "bold"), bg='#f3f4f6', fg=self.colors['text'])
        title_label.pack(pady=10)
        
        # Status bar
        self.status_label = tk.Label(content_frame, text="⏳ Not running", 
                                     font=("Helvetica", 12), bg='#fff3cd', fg='#856404')
        self.status_label.pack(fill=tk.X, pady=5)
        
        # Metrics row
        self.setup_metrics(content_frame)
        
        # Agent health
        self.setup_agent_health(content_frame)
        
        # Activity feed
        self.setup_activity_feed(content_frame)
    
    def setup_sidebar(self, parent):
        """Setup control sidebar"""
        sidebar = tk.Frame(parent, bg=self.colors['light'], width=250, relief=tk.RAISED, bd=1)
        sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        sidebar.pack_propagate(False)
        
        # Title
        title = tk.Label(sidebar, text="🎮 Control Panel", font=("Helvetica", 14, "bold"),
                        bg=self.colors['light'], fg=self.colors['text'])
        title.pack(pady=10)
        
        # Agents slider
        tk.Label(sidebar, text="Number of Agents:", bg=self.colors['light']).pack(padx=10, pady=(10, 0))
        self.agents_slider = ttk.Scale(sidebar, from_=1, to=10, orient=tk.HORIZONTAL, 
                                 variable=self.num_agents)
        self.agents_slider.pack(padx=10, pady=5, fill=tk.X)
        self.agents_label = tk.Label(sidebar, text="3", bg=self.colors['light'], font=("Helvetica", 10))
        self.agents_label.pack()
        self.num_agents.trace('w', self.update_agent_count_label)
        
        # Control buttons
        self.start_btn = tk.Button(sidebar, text="▶️ Start", command=self.start_simulation,
                                   bg=self.colors['success'], fg='white', font=("Helvetica", 11, "bold"),
                                   relief=tk.FLAT, padx=10, pady=8, cursor="hand2")
        self.start_btn.pack(padx=10, pady=5, fill=tk.X)
        
        self.stop_btn = tk.Button(sidebar, text="⹹️ Stop", command=self.stop_simulation,
                                  bg=self.colors['danger'], fg='white', font=("Helvetica", 11, "bold"),
                                  relief=tk.FLAT, padx=10, pady=8, state=tk.DISABLED, cursor="hand2")
        self.stop_btn.pack(padx=10, pady=5, fill=tk.X)
        
        tk.Label(sidebar, text="", bg=self.colors['light']).pack(pady=5)
        tk.Frame(sidebar, height=1, bg='#e5e7eb').pack(fill=tk.X, padx=10)
        tk.Label(sidebar, text="", bg=self.colors['light']).pack(pady=5)
        
        # Task buttons
        self.task_btn = tk.Button(sidebar, text="📤 Broadcast Task", command=self.broadcast_task,
                                 bg=self.colors['primary'], fg='white', font=("Helvetica", 11, "bold"),
                                 relief=tk.FLAT, padx=10, pady=8, state=tk.DISABLED, cursor="hand2")
        self.task_btn.pack(padx=10, pady=5, fill=tk.X)
        
        self.task5_btn = tk.Button(sidebar, text="📤 Broadcast 5 Tasks", command=self.broadcast_5_tasks,
                                  bg=self.colors['primary'], fg='white', font=("Helvetica", 11, "bold"),
                                  relief=tk.FLAT, padx=10, pady=8, state=tk.DISABLED, cursor="hand2")
        self.task5_btn.pack(padx=10, pady=5, fill=tk.X)
        
        tk.Label(sidebar, text="", bg=self.colors['light']).pack(pady=5)
        tk.Frame(sidebar, height=1, bg='#e5e7eb').pack(fill=tk.X, padx=10)
        tk.Label(sidebar, text="", bg=self.colors['light']).pack(pady=5)
        
        # Fault injection
        tk.Label(sidebar, text="🔥 Fault Injection", font=("Helvetica", 12, "bold"),
                bg=self.colors['light'], fg=self.colors['danger']).pack(padx=10, pady=5)
        
        tk.Label(sidebar, text="Select Agent:", bg=self.colors['light']).pack(padx=10)
        self.agent_select = ttk.Combobox(sidebar, state="readonly", width=20)
        self.agent_select.pack(padx=10, pady=5)
        
        crash_btn = tk.Button(sidebar, text="💥 Crash Agent", command=self.crash_agent,
                             bg=self.colors['danger'], fg='white', font=("Helvetica", 10, "bold"),
                             relief=tk.FLAT, padx=10, pady=6, cursor="hand2")
        crash_btn.pack(padx=10, pady=3, fill=tk.X)
        
        recover_btn = tk.Button(sidebar, text="✅ Recover Agent", command=self.recover_agent,
                               bg=self.colors['success'], fg='white', font=("Helvetica", 10, "bold"),
                               relief=tk.FLAT, padx=10, pady=6, cursor="hand2")
        recover_btn.pack(padx=10, pady=3, fill=tk.X)
        
        crash_random_btn = tk.Button(sidebar, text="💥 Crash Random", command=self.crash_random,
                                    bg='#f97316', fg='white', font=("Helvetica", 10, "bold"),
                                    relief=tk.FLAT, padx=10, pady=6, cursor="hand2")
        crash_random_btn.pack(padx=10, pady=3, fill=tk.X)
        
        recover_all_btn = tk.Button(sidebar, text="✅ Recover All", command=self.recover_all,
                                   bg='#059669', fg='white', font=("Helvetica", 10, "bold"),
                                   relief=tk.FLAT, padx=10, pady=6, cursor="hand2")
        recover_all_btn.pack(padx=10, pady=3, fill=tk.X)
        
        tk.Label(sidebar, text="", bg=self.colors['light']).pack(pady=5)
        tk.Frame(sidebar, height=1, bg='#e5e7eb').pack(fill=tk.X, padx=10)
        tk.Label(sidebar, text="", bg=self.colors['light']).pack(pady=5)
        
        # Refresh settings
        tk.Label(sidebar, text="🔄 Auto-Refresh", font=("Helvetica", 11, "bold"),
                bg=self.colors['light']).pack(padx=10, pady=5)
        
        refresh_check = ttk.Checkbutton(sidebar, text="Enable", variable=self.auto_refresh)
        refresh_check.pack(padx=10, pady=3)
        
        tk.Label(sidebar, text="Interval (s):", bg=self.colors['light']).pack(padx=10)
        interval_spin = ttk.Spinbox(sidebar, from_=1, to=10, textvariable=self.refresh_interval, width=10)
        interval_spin.pack(padx=10, pady=3)
        
        refresh_now_btn = tk.Button(sidebar, text="🔄 Refresh Now", command=self.refresh_dashboard,
                                   bg=self.colors['warning'], fg='white', font=("Helvetica", 10, "bold"),
                                   relief=tk.FLAT, padx=10, pady=6, cursor="hand2")
        refresh_now_btn.pack(padx=10, pady=5, fill=tk.X)
    
    def setup_metrics(self, parent):
        """Setup metrics display"""
        metrics_frame = tk.Frame(parent, bg='#f3f4f6')
        metrics_frame.pack(fill=tk.X, pady=10)
        
        self.metric_labels = {}
        metrics = [
            ('📋 Total Tasks', 'total_tasks'),
            ('✅ Allocated', 'allocated'),
            ('⏳ Pending', 'pending'),
            ('🏆 Completed', 'completed'),
            ('🤖 Active', 'active_agents'),
            ('⚠️ Failed', 'failed_agents')
        ]
        
        for label_text, key in metrics:
            frame = tk.Frame(metrics_frame, bg='white', relief=tk.FLAT, bd=1)
            frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
            
            tk.Label(frame, text=label_text, font=("Helvetica", 10), bg='white', fg='#6b7280').pack(pady=(5, 0))
            value_label = tk.Label(frame, text="0", font=("Helvetica", 18, "bold"), bg='white', fg=self.colors['primary'])
            value_label.pack(pady=(0, 5))
            
            self.metric_labels[key] = value_label
    
    def setup_agent_health(self, parent):
        """Setup agent health display"""
        health_frame = tk.LabelFrame(parent, text="🏥 Agent Health & Status", font=("Helvetica", 11, "bold"),
                                     bg='#f3f4f6', fg=self.colors['text'], padx=10, pady=10)
        health_frame.pack(fill=tk.X, pady=10)
        
        self.agents_health_frame = tk.Frame(health_frame, bg='#f3f4f6')
        self.agents_health_frame.pack(fill=tk.BOTH, expand=True)
    
    def setup_activity_feed(self, parent):
        """Setup live activity feed"""
        feed_frame = tk.LabelFrame(parent, text="🎬 Live Activity Feed", font=("Helvetica", 11, "bold"),
                                   bg='#f3f4f6', fg=self.colors['text'], padx=10, pady=10)
        feed_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Create scrolled text widget with custom styling
        self.activity_feed = scrolledtext.ScrolledText(feed_frame, height=15, wrap=tk.WORD,
                                                       bg='#ffffff', fg=self.colors['text'],
                                                       font=("Helvetica", 9), relief=tk.FLAT, bd=0)
        self.activity_feed.pack(fill=tk.BOTH, expand=True)
        
        # Configure tags for different event types
        self.activity_feed.tag_config('broadcast', foreground='#667eea', font=("Helvetica", 9, "bold"))
        self.activity_feed.tag_config('bid_good', foreground='#10b981', font=("Helvetica", 9))
        self.activity_feed.tag_config('bid_mid', foreground='#f59e0b', font=("Helvetica", 9))
        self.activity_feed.tag_config('bid_bad', foreground='#ef4444', font=("Helvetica", 9))
        self.activity_feed.tag_config('allocation', foreground='#10b981', font=("Helvetica", 9, "bold"))
        self.activity_feed.tag_config('completed', foreground='#059669', font=("Helvetica", 9))
        self.activity_feed.tag_config('crashed', foreground='#dc2626', font=("Helvetica", 9, "bold"))
        self.activity_feed.tag_config('timestamp', foreground='#9ca3af', font=("Helvetica", 8))
        self.activity_feed.config(state=tk.DISABLED)
    
    def update_agent_count_label(self, *args):
        self.agents_label.config(text=str(self.num_agents.get()))
    
    def start_simulation(self):
        """Start simulation"""
        if self.running:
            return
        
        try:
            self.broker = ReliableBroker()
            broker_thread = threading.Thread(target=self.broker.listen, daemon=True)
            broker_thread.start()
            time.sleep(0.5)
            
            self.coordinator = Coordinator(self.broker)
            num_agents = self.num_agents.get()
            self.agents = [Agent(f"agent_{i+1}", self.broker) for i in range(num_agents)]
            
            time.sleep(1)
            self.running = True
            self.last_activity_index = 0
            
            # Clear activity feed
            self.activity_feed.config(state=tk.NORMAL)
            self.activity_feed.delete("1.0", tk.END)
            self.activity_feed.config(state=tk.DISABLED)
            
            # Update UI
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
            self.task_btn.config(state=tk.NORMAL)
            self.task5_btn.config(state=tk.NORMAL)
            self.agents_slider.config(state=tk.DISABLED)
            self.status_label.config(text="✅ Simulation RUNNING", bg='#d1fae5', fg='#065f46')
            
            self.update_agent_selector()
            self.refresh_dashboard()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start simulation: {str(e)}")
    
    def stop_simulation(self):
        """Stop simulation"""
        if not self.running:
            return
        
        try:
            if self.broker:
                self.broker.stop()
            if self.coordinator:
                self.coordinator.stop()
            for agent in self.agents:
                agent.stop()
            
            self.running = False
            self.agents = []
            
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
            self.task_btn.config(state=tk.DISABLED)
            self.task5_btn.config(state=tk.DISABLED)
            self.agents_slider.config(state=tk.NORMAL)
            self.status_label.config(text="⏹️ Simulation stopped", bg='#fee2e2', fg='#7f1d1d')
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to stop simulation: {str(e)}")
    
    def broadcast_task(self):
        """Broadcast single task"""
        if not self.running or not self.coordinator:
            return
        
        try:
            task_id = f"task_{self.task_counter}"
            self.task_counter += 1
            
            task = Task(
                task_id=task_id,
                priority=random.randint(1, 10),
                estimated_time=random.uniform(1, 3),
                description=f"Process data batch {task_id}"
            )
            
            self.coordinator.broadcast_task(task)
            self.refresh_dashboard()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to broadcast task: {str(e)}")
    
    def broadcast_5_tasks(self):
        """Broadcast 5 tasks"""
        for _ in range(5):
            self.broadcast_task()
            time.sleep(0.2)
        messagebox.showinfo("Success", "5 tasks broadcasted!")
    
    def crash_agent(self):
        """Crash selected agent"""
        agent_id = self.agent_select.get()
        if not agent_id:
            messagebox.showwarning("Warning", "Please select an agent")
            return
        
        for agent in self.agents:
            if agent.agent_id == agent_id:
                # Disable auto-recovery so manual recovery is needed
                agent.crash(auto_recover_after=0)
                self.refresh_dashboard()
                messagebox.showinfo("Agent Crashed", f"{agent_id} has crashed!\n\nYou can:\n1. Click 'Recover Agent' to recover immediately\n2. Wait for auto-recovery (6-7 seconds)")
                return
    
    def recover_agent(self):
        """Recover selected agent"""
        agent_id = self.agent_select.get()
        if not agent_id:
            messagebox.showwarning("Warning", "Please select an agent")
            return
        
        for agent in self.agents:
            if agent.agent_id == agent_id:
                if agent.recover():
                    self.refresh_dashboard()
                    messagebox.showinfo("Success", f"{agent_id} recovered!")
                else:
                    messagebox.showinfo("Info", f"{agent_id} is not crashed")
                return
    
    def crash_random(self):
        """Crash random agent"""
        if not self.agents:
            return
        
        agent = random.choice(self.agents)
        # Enable auto-recovery for random crash
        agent.crash(auto_recover_after=random.uniform(6, 7))
        self.refresh_dashboard()
        messagebox.showinfo("Random Crash", f"{agent.agent_id} crashed!\n\nAuto-recovery in 6-7 seconds...")
    
    def recover_all(self):
        """Recover all agents"""
        recovered = sum(1 for agent in self.agents if agent.recover())
        if recovered > 0:
            self.refresh_dashboard()
            messagebox.showinfo("Success", f"Recovered {recovered} agent(s)!")
        else:
            messagebox.showinfo("Info", "No crashed agents")
    
    def update_agent_selector(self):
        """Update agent selector combobox"""
        agent_ids = [agent.agent_id for agent in self.agents]
        self.agent_select['values'] = agent_ids
        if agent_ids:
            self.agent_select.current(0)
    
    def add_activity(self, message, event_type='bid_mid'):
        """Add message to activity feed"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        self.activity_feed.config(state=tk.NORMAL)
        
        # Add timestamp
        self.activity_feed.insert(tk.END, f"[{timestamp}] ", 'timestamp')
        
        # Add message with appropriate tag
        self.activity_feed.insert(tk.END, message + "\n", event_type)
        
        # Keep only last 1000 lines
        lines = self.activity_feed.get("1.0", tk.END).count('\n')
        if lines > 1000:
            self.activity_feed.delete("1.0", "100.end")
        
        self.activity_feed.see(tk.END)
        self.activity_feed.config(state=tk.DISABLED)
    
    def update_activities_from_coordinator(self):
        """Pull activities from coordinator and update feed"""
        if not self.running or not self.coordinator:
            return
        
        try:
            # Get all recent activities
            all_activities = self.coordinator.get_recent_activity(limit=500)
            
            # Update activity feed with new activities
            for activity in all_activities[self.last_activity_index:]:
                activity_type = activity.get('type', '')
                timestamp = datetime.fromtimestamp(activity['timestamp']).strftime("%H:%M:%S")
                
                # Determine event type and message
                if activity_type == 'task_broadcast':
                    msg = f"📢 Task {activity.get('task_id')} broadcasted (Priority: {activity.get('priority')}/10)"
                    tag = 'broadcast'
                elif activity_type in ('bid', 'bid_sent'):
                    bid_value = activity.get('bid_value', 0)
                    agent_id = activity.get('agent_id')
                    task_id = activity.get('task_id')
                    
                    if bid_value < 2:
                        tag = 'bid_good'
                        emoji = "🟢"
                    elif bid_value < 5:
                        tag = 'bid_mid'
                        emoji = "🟡"
                    else:
                        tag = 'bid_bad'
                        emoji = "🔴"
                    
                    msg = f"{emoji} Bid: {agent_id} bid {float(bid_value):.2f} for {task_id}"
                elif activity_type in ('allocation', 'task_allocated'):
                    msg = f"🏆 Task {activity.get('task_id')} allocated to {activity.get('agent_id')} (bid: {activity.get('bid_value', 0):.2f})"
                    tag = 'allocation'
                elif activity_type == 'task_completed':
                    exec_time = activity.get('execution_time', 0)
                    msg = f"✅ {activity.get('agent_id')} completed {activity.get('task_id')} in {exec_time:.2f}s"
                    tag = 'completed'
                elif activity_type in ('agent_crashed', 'agent_failure'):
                    failed_tasks = activity.get('failed_tasks', 0)
                    msg = f"💥 Agent {activity.get('agent_id')} CRASHED! Reassigning {failed_tasks} task(s)..."
                    tag = 'crashed'
                elif activity_type in ('agent_recovered', 'agent_recovery'):
                    msg = f"✅ Agent {activity.get('agent_id')} RECOVERED!"
                    tag = 'allocation'
                elif activity_type == 'task_reassignment':
                    msg = f"🔄 Task {activity.get('task_id')} reassigned from {activity.get('failed_agent')} to {activity.get('new_agent')}"
                    tag = 'broadcast'
                else:
                    msg = f"{activity_type}: {str(activity)}"
                    tag = 'bid_mid'
                
                # Add to feed
                self.activity_feed.config(state=tk.NORMAL)
                self.activity_feed.insert(tk.END, f"[{timestamp}] ", 'timestamp')
                self.activity_feed.insert(tk.END, msg + "\n", tag)
                
                # Keep only last 1000 lines
                lines = self.activity_feed.get("1.0", tk.END).count('\n')
                if lines > 1000:
                    self.activity_feed.delete("1.0", "100.end")
                
                self.activity_feed.see(tk.END)
                self.activity_feed.config(state=tk.DISABLED)
            
            # Update last index
            self.last_activity_index = len(all_activities)
            
        except Exception as e:
            print(f"Error updating activities: {e}")
    
    def refresh_dashboard(self):
        """Refresh dashboard metrics"""
        if not self.running or not self.coordinator:
            return
        
        try:
            # Update activities from coordinator
            self.update_activities_from_coordinator()
            
            # Update metrics
            stats = self.coordinator.get_stats()
            self.metric_labels['total_tasks'].config(text=str(stats.get('total_tasks', 0)))
            self.metric_labels['allocated'].config(text=str(stats.get('allocated_tasks', 0)))
            self.metric_labels['pending'].config(text=str(stats.get('pending_tasks', 0)))
            self.metric_labels['completed'].config(text=str(stats.get('completed_tasks', 0)))
            self.metric_labels['active_agents'].config(text=f"{stats.get('active_agents', 0)}/{stats.get('total_agents', 0)}")
            self.metric_labels['failed_agents'].config(text=str(stats.get('failed_agents', 0)))
            
            # Update agent health
            self.update_agent_health()
            
        except Exception as e:
            print(f"Error refreshing dashboard: {e}")
    
    def update_agent_health(self):
        """Update agent health display"""
        for widget in self.agents_health_frame.winfo_children():
            widget.destroy()
        
        if not self.coordinator:
            return
        
        agent_statuses = self.coordinator.get_agent_status()
        failed_agents = list(self.coordinator.failed_agents)
        
        if failed_agents:
            failed_label = tk.Label(self.agents_health_frame, 
                                   text=f"⚠️ Failed: {', '.join(failed_agents)}",
                                   bg='#fee2e2', fg='#991b1b', font=("Helvetica", 10, "bold"),
                                   relief=tk.FLAT, padx=10, pady=5)
            failed_label.pack(fill=tk.X, pady=(0, 5))
        
        # Create health indicators
        health_cols = tk.Frame(self.agents_health_frame, bg='#f3f4f6')
        health_cols.pack(fill=tk.X, pady=5)
        
        for agent_id, status in agent_statuses.items():
            is_alive = status['is_alive']
            
            # Check if agent is crashed
            agent_crashed = False
            agent_obj = None
            for agent in self.agents:
                if agent.agent_id == agent_id:
                    agent_crashed = agent.is_crashed
                    agent_obj = agent
                    break
            
            if agent_crashed:
                color = '#dc2626'
                text = f"💥 {agent_id}\nCRASHED"
                # Show if auto-recovery is enabled
                if agent_obj and agent_obj.auto_recover_enabled:
                    time_since_crash = time.time() - agent_obj.crash_time if agent_obj.crash_time else 0
                    time_to_recover = max(0, agent_obj.auto_recover_delay - time_since_crash)
                    text += f"\nAuto-recover in {time_to_recover:.1f}s"
            elif is_alive:
                color = '#10b981'
                text = f"🟢 {agent_id}\nOnline"
            else:
                color = '#ef4444'
                text = f"🔴 {agent_id}\nFailed"
            
            health_box = tk.Frame(health_cols, bg=color, relief=tk.FLAT, padx=10, pady=8)
            health_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=3)
            
            tk.Label(health_box, text=text, bg=color, fg='white', font=("Helvetica", 10, "bold")).pack()
    
    def auto_refresh_loop(self):
        """Auto-refresh loop"""
        if self.auto_refresh.get() and self.running:
            self.refresh_dashboard()
            interval = self.refresh_interval.get() * 1000
            self.root.after(interval, self.auto_refresh_loop)
        else:
            self.root.after(1000, self.auto_refresh_loop)

if __name__ == "__main__":
    root = tk.Tk()
    app = MultiAgentDashboard(root)
    root.mainloop()