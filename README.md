# Multi-Agent Task Completion System

<div align="center">
  <h3 align="center">Multi-Agent Network Simulation</h3>

  <p align="center">
    A distributed task allocation system with fault-tolerant agents and real-time monitoring
    <br />
    <strong>Auction-Based Task Distribution • Fault Tolerance • Real-Time Dashboard</strong>
    <br />
    <br />
    <a href="#demo">View Demo</a>
    ·
    <a href="#usage">Documentation</a>
    ·
    <a href="https://github.com/yourusername/multiagent-task-completion/issues">Report Bug</a>
  </p>
</div>

<!-- TABLE OF CONTENTS -->
<details>
  <summary>Table of Contents</summary>
  <ol>
    <li><a href="#about-the-project">About The Project</a></li>
    <li><a href="#key-features">Key Features</a></li>
    <li><a href="#architecture">Architecture</a></li>
    <li><a href="#built-with">Built With</a></li>
    <li><a href="#getting-started">Getting Started</a></li>
    <li><a href="#usage">Usage</a></li>
    <li><a href="#project-structure">Project Structure</a></li>
    <li><a href="#how-it-works">How It Works</a></li>
    <li><a href="#roadmap">Roadmap</a></li>
    <li><a href="#contributing">Contributing</a></li>
    <li><a href="#license">License</a></li>
    <li><a href="#contact">Contact</a></li>
  </ol>
</details>

## About The Project

The Multi-Agent Task Completion System is a sophisticated distributed computing simulation that demonstrates autonomous task allocation through an auction-based mechanism. The system features multiple intelligent agents that bid on tasks, a coordinator that manages allocation, and comprehensive fault tolerance with automatic recovery mechanisms.

### What Makes This Special

**Intelligent Task Distribution**: Agents autonomously bid on tasks based on their current workload, with the coordinator allocating tasks to the lowest bidder.

**Fault Tolerance**: The system handles agent failures gracefully, automatically reassigning tasks to the next best bidder or rebroadcasting when necessary.

**Real-Time Monitoring**: A beautiful Tkinter-based dashboard provides live visualization of task allocation, agent health, and system metrics.

**Flexible Architecture**: Works with either Redis for production-grade message brokering or in-memory queue for development without external dependencies.

## Key Features

✨ **Auction-Based Task Allocation** - Agents compete for tasks based on their workload and availability

🔄 **Automatic Fault Recovery** - Detects failed agents and reassigns incomplete tasks intelligently

📊 **Real-Time Dashboard** - Interactive GUI with live activity feed, metrics, and agent health monitoring

💪 **Fault Injection** - Simulate agent crashes to test system resilience

❤️ **Heartbeat Monitoring** - Continuous agent health checks with configurable timeouts

📡 **Data Streaming** - Real-time metrics from agents including CPU, memory, and task status

🔌 **Flexible Messaging** - Redis-based or in-memory broker for message passing

🎯 **Smart Task Reassignment** - Falls back to next best bidder or rebroadcasts if no alternatives

## Architecture

```
┌─────────────────┐
│   Coordinator   │ ◄───── Task Broadcast
│   (Task Master) │ ◄───── Bid Collection
└────────┬────────┘ ◄───── Heartbeat Monitor
         │
         │ Message Broker (Redis/In-Memory)
         │
    ┌────┴────┬────────┬────────┐
    │         │        │        │
┌───▼───┐ ┌──▼───┐ ┌──▼───┐ ┌──▼───┐
│Agent 1│ │Agent 2│ │Agent 3│ │Agent N│
│       │ │       │ │       │ │       │
│Bidding│ │Bidding│ │Bidding│ │Bidding│
│Execute│ │Execute│ │Execute│ │Execute│
└───────┘ └───────┘ └───────┘ └───────┘
     │         │         │         │
     └─────────┴─────────┴─────────┘
              Heartbeats
```

### Message Flow

1. **Task Broadcast**: Coordinator publishes task to all agents
2. **Bidding Phase**: Agents evaluate workload and submit bids
3. **Allocation**: Coordinator selects lowest bidder
4. **Execution**: Winning agent executes task
5. **Completion**: Agent reports completion
6. **Monitoring**: Continuous heartbeat and data streaming

## Built With

* ![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
* ![Tkinter](https://img.shields.io/badge/GUI-Tkinter-green.svg)
* ![Redis](https://img.shields.io/badge/Redis-Optional-red.svg)
* ![Threading](https://img.shields.io/badge/Concurrency-Threading-orange.svg)

**Core Technologies:**
- **Python 3.8+** - Main programming language
- **Tkinter** - GUI framework for dashboard
- **Redis** (Optional) - Message broker for distributed systems
- **Threading** - Concurrent execution and monitoring

## Getting Started

Follow these steps to get the simulation running on your local machine.

### Prerequisites

* Python 3.8 or higher
  ```sh
  python --version
  ```

* (Optional) Redis Server - Only needed for production-grade message broker
  ```sh
  # On Ubuntu/Debian
  sudo apt-get install redis-server
  
  # On macOS with Homebrew
  brew install redis
  
  # On Windows with Chocolatey
  choco install redis-64
  ```

### Installation

1. Clone the repository
   ```sh
   git clone https://github.com/yourusername/multiagent-task-completion.git
   cd multiagent-task-completion
   ```

2. Install Python dependencies
   ```sh
   pip install -r requirements.txt
   ```

3. (Optional) Start Redis if you want to use Redis broker
   ```sh
   redis-server
   ```
   
   **Note:** The system automatically falls back to in-memory broker if Redis is not available.

## Usage

### Option 1: Interactive Dashboard (Recommended)

Launch the graphical dashboard for full control and visualization:

```sh
python dashboard.py
```

**Dashboard Features:**
- Start/stop simulation with configurable number of agents (1-10)
- Broadcast single tasks or batch of 5 tasks
- View real-time metrics: total tasks, allocated, pending, completed
- Monitor agent health with color-coded status indicators
- Live activity feed with timestamped events
- Fault injection: crash/recover specific or random agents
- Auto-refresh with configurable intervals

**Dashboard Controls:**
1. Set number of agents using slider (1-10)
2. Click "▶️ Start" to initialize the system
3. Use "📤 Broadcast Task" to send individual tasks
4. Click "📤 Broadcast 5 Tasks" for batch testing
5. Test fault tolerance with "💥 Crash Agent" buttons
6. Watch real-time activity feed for system events

### Option 2: Command-Line Simulation

Run a pre-configured simulation with 3 agents and 5 tasks:

```sh
python run_simulation.py
```

**What happens:**
1. Initializes message broker (Redis or in-memory)
2. Creates coordinator and 3 agents
3. Broadcasts 5 sample tasks
4. Agents bid on tasks autonomously
5. Coordinator allocates to lowest bidders
6. Displays final statistics after 15 seconds

### Example Output

```
🚀 Starting Multi-Agent Network Simulation

✅ Created 3 agents

📢 Broadcasting tasks...

🎯 Coordinator initialized with fault tolerance
🤖 Agent agent_1 initialized with heartbeat
🤖 Agent agent_2 initialized with heartbeat
🤖 Agent agent_3 initialized with heartbeat

💰 Agent agent_1 bid 2.34 for task_0
💰 Agent agent_2 bid 4.12 for task_0
💰 Agent agent_3 bid 1.87 for task_0

🏆 Task task_0 allocated to agent_3 (bid: 1.87)

==================================================
📊 SIMULATION RESULTS
==================================================

📋 Coordinator Stats:
  Total tasks: 5
  Allocated: 5
  Pending: 0
  Active agents: 3/3
  Failed agents: 0

🤖 Agent Stats:
  agent_1 - 🟢 ALIVE:
    Current load: 0/5
    Completed tasks: 2
    CPU: 40.2% | Memory: 245 MB
  agent_2 - 🟢 ALIVE:
    Current load: 0/5
    Completed tasks: 2
    CPU: 38.1% | Memory: 223 MB
  agent_3 - 🟢 ALIVE:
    Current load: 0/5
    Completed tasks: 1
    CPU: 20.5% | Memory: 189 MB

✅ Simulation complete!
```

## Project Structure

```
MultiAgent_Task_Completion/
│
├── coordinator.py          # Central task allocator and monitor
├── dashboard.py           # Tkinter GUI for visualization
├── run_simulation.py      # CLI simulation runner
├── requirements.txt       # Python dependencies
│
├── agents/
│   ├── __init__.py
│   └── agent.py          # Agent implementation with bidding logic
│
└── communication/
    ├── __init__.py
    ├── broker.py         # Message broker (Redis/in-memory)
    └── message_types.py  # Data structures and enums
```

### Component Details

**coordinator.py** - The brain of the system
- Broadcasts tasks to all agents
- Collects and evaluates bids
- Allocates tasks to lowest bidders
- Monitors agent health via heartbeats
- Handles agent failures and task reassignment
- Maintains activity log for dashboard

**agent.py** - Autonomous worker agents
- Listens for task broadcasts
- Calculates bids based on workload
- Executes allocated tasks
- Sends heartbeats and metrics
- Supports crash simulation and recovery

**broker.py** - Message passing infrastructure
- Publish/subscribe pattern implementation
- Reliable message delivery with ACKs
- Automatic retransmission on timeout
- Falls back to in-memory if Redis unavailable

**dashboard.py** - Real-time monitoring interface
- Interactive control panel
- Live metrics and statistics
- Agent health visualization
- Activity feed with color-coded events
- Fault injection controls

## How It Works

### 1. Task Broadcasting

When a task is broadcast:
- Coordinator publishes task to 'tasks' channel
- All active agents receive the broadcast
- Task includes: ID, priority, estimated time, description

### 2. Bidding Phase

Each agent evaluates the task:
```python
base_bid = current_load * 10
random_factor = random.uniform(0, 5)
bid_value = base_bid + random_factor
```
- Lower current load = lower bid (more competitive)
- Random factor adds slight variation
- Agents only bid if below max capacity

### 3. Task Allocation

Coordinator selects winner:
- Waits 2 seconds for bids
- Filters bids from failed agents
- Sorts by bid value (ascending)
- Allocates to lowest bidder
- Stores all bids for potential reassignment

### 4. Fault Detection

Heartbeat monitoring:
- Agents send heartbeat every 2 seconds
- Coordinator tracks last heartbeat time
- Timeout threshold: 6 seconds
- Failed agents marked and tasks reassigned

### 5. Task Reassignment

When agent fails:
1. Check if tasks were completed (via event stream)
2. For incomplete tasks:
   - Try next lowest bidder first
   - If no alternative bidders, rebroadcast after delay
3. Clean up allocations and state

### 6. Crash Recovery

Agents can recover:
- Manual recovery via dashboard
- Automatic recovery after configurable delay
- Resume heartbeats and accept new tasks
- Previous incomplete tasks already reassigned

## Demo

### Dashboard Screenshot

```
┌─────────────────────────────────────────────────────────────────┐
│  🤖 Multi-Agent Network Dashboard                               │
├─────────────────────────────────────────────────────────────────┤
│  ✅ Simulation RUNNING                                          │
├──────┬──────┬──────┬──────┬──────┬──────────────────────────────┤
│📋 12 │✅ 10 │⏳ 2  │🏆 8  │🤖 3/3 │⚠️ 0                      │
├──────┴──────┴──────┴──────┴──────┴──────────────────────────────┤
│  🥼 Agent Health & Status                                       │
│  ┌──────────┬──────────┬──────────┐                             │
│  │🟢 agent_1│🟢 agent_2│🟢 agent_3│                            │
│  │  Online  │  Online  │  Online  │                             │
│  └──────────┴──────────┴──────────┘                             │
├─────────────────────────────────────────────────────────────────┤
│  🎬 Live Activity Feed                                          │
│  [14:32:01] 📢 Task task_0 broadcasted (Priority: 8/10)         │
│  [14:32:01] 🟡 Bid: agent_1 bid 2.34 for task_0                 │
│  [14:32:01] 🟢 Bid: agent_3 bid 1.87 for task_0                 │
│  [14:32:03] 🏆 Task task_0 allocated to agent_3 (bid: 1.87)     │
│  [14:32:05] ✅ agent_3 completed task_0 in 2.12s                │
└──────────────────────────────────────────────────────────────────┘
```

## Roadmap

### Completed Features
- [x] Auction-based task allocation
- [x] Fault detection and recovery
- [x] Interactive dashboard with Tkinter
- [x] Real-time activity logging
- [x] Agent health monitoring
- [x] Flexible message broker (Redis/in-memory)
- [x] Task reassignment to next best bidder
- [x] Configurable agent count
- [x] Batch task broadcasting

### Planned Features
- [ ] Task priority-based scheduling
- [ ] Agent specialization (task types)
- [ ] Load balancing algorithms
- [ ] Performance analytics dashboard
- [ ] Export simulation results
- [ ] Web-based dashboard (Flask/React)
- [ ] Multi-coordinator support
- [ ] Task dependencies and workflows
- [ ] REST API for external control

See [open issues](https://github.com/yourusername/multiagent-task-completion/issues) for feature requests and known issues.

## Configuration

### Broker Settings

Edit `broker.py` to configure:

```python
# Force Redis usage
broker = ReliableBroker(use_redis=True)

# Force in-memory broker
broker = ReliableBroker(use_redis=False)

# Auto-detect (default)
broker = ReliableBroker()
```

### Agent Parameters

In `agent.py`:

```python
self.max_load = 5               # Maximum concurrent tasks
self.heartbeat_interval = 2.0   # Seconds between heartbeats
self.stream_interval = 1.0      # Seconds between data streams
```

### Coordinator Settings

In `coordinator.py`:

```python
self.heartbeat_timeout = 6.0    # Agent failure threshold
self.max_activity_log = 100     # Activity feed size
```

### Contributing

Contributions make the open-source community an amazing place to learn and create. Any contributions you make are **greatly appreciated**!

To contribute:

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 style guide
- Add docstrings to new functions
- Test with both Redis and in-memory brokers
- Update README for new features
- Add logging for debugging

## License

Distributed under the MIT License. See `LICENSE` for more information.

## Contact

Sidhart Sami - sidhart.sami@gmail.com

Project Link: [https://github.com/SidhartSami/CS3001-Multi-Agent-Communication-Networks](https://github.com/SidhartSami/CS3001-Multi-Agent-Communication-Networks)
Report Bug: [https://github.com/SidhartSami/CS3001-Multi-Agent-Communication-Networks/issues](https://github.com/SidhartSami/CS3001-Multi-Agent-Communication-Networks/issues)

### Contributors

This project was developed as a group semester project by:

- **Sidhart Sami**
- **Aliyan Munawwar**
- **Abdul Rafey**
- **Hadi Armaghan**
  
## Acknowledgments

Inspiration and resources:

* [Distributed Systems Concepts](https://www.distributed-systems.net/)
* [Multi-Agent Systems](https://en.wikipedia.org/wiki/Multi-agent_system)
* [Redis Pub/Sub](https://redis.io/topics/pubsub)
* [Tkinter Documentation](https://docs.python.org/3/library/tkinter.html)
* [Threading in Python](https://docs.python.org/3/library/threading.html)
* [Auction Algorithms](https://en.wikipedia.org/wiki/Auction_algorithm)

---

<div align="center">
  <strong>Built with ❤️ for distributed systems enthusiasts</strong>
</div>
