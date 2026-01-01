import time
import threading
import random
from communication.broker import ReliableBroker
from communication.message_types import Task
from agents.agent import Agent
from coordinator import Coordinator
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def create_sample_tasks():
    """Create sample tasks for testing"""
    tasks = [
        Task(
            task_id=f"task_{i}",
            priority=random.randint(1, 10),
            estimated_time=random.uniform(1, 3),
            description=f"Process data batch {i}"
        )
        for i in range(5)
    ]
    return tasks

def main():
    print("🚀 Starting Multi-Agent Network Simulation\n")
    
    # Initialize broker FIRST
    broker = ReliableBroker()
    
    # Start broker listening in separate thread BEFORE creating agents
    broker_thread = threading.Thread(target=broker.listen, daemon=True)
    broker_thread.start()
    
    # Give broker time to start listening
    time.sleep(0.5)
    
    # Create coordinator AFTER broker is listening
    coordinator = Coordinator(broker)
    
    # Create agents AFTER broker is listening
    num_agents = 3
    agents = [Agent(f"agent_{i+1}", broker) for i in range(num_agents)]
    
    print(f"✅ Created {num_agents} agents\n")
    
    # IMPORTANT: Wait for all subscriptions to be fully registered
    print("⏳ Waiting for all agents to be ready...")
    time.sleep(2)  # Increased wait time to ensure all subscriptions are ready
    
    # Broadcast tasks
    print("\n📢 Broadcasting tasks...\n")
    tasks = create_sample_tasks()
    
    for task in tasks:
        coordinator.broadcast_task(task)
        time.sleep(0.5)  # Small delay between tasks
    
    # Let simulation run
    print("\n⏳ Simulation running...\n")
    time.sleep(15)  # Run for 15 seconds
    
    # Print final stats
    print("\n" + "="*50)
    print("📊 SIMULATION RESULTS")
    print("="*50)
    
    coord_stats = coordinator.get_stats()
    print(f"\n📋 Coordinator Stats:")
    print(f"  Total tasks: {coord_stats['total_tasks']}")
    print(f"  Allocated: {coord_stats['allocated_tasks']}")
    print(f"  Pending: {coord_stats['pending_tasks']}")
    print(f"  Active agents: {coord_stats.get('active_agents', 0)}/{coord_stats.get('total_agents', 0)}")
    print(f"  Failed agents: {coord_stats.get('failed_agents', 0)}")
    
    print(f"\n🤖 Agent Stats:")
    agent_statuses = coordinator.get_agent_status()
    for agent in agents:
        status = agent.get_status()
        agent_id = status['agent_id']
        agent_health = agent_statuses.get(agent_id, {})
        is_alive = agent_health.get('is_alive', True)
        
        health_status = "🟢 ALIVE" if is_alive else "🔴 FAILED"
        print(f"  {status['agent_id']} - {health_status}:")
        print(f"    Current load: {status['current_load']}/{status['max_load']}")
        print(f"    Completed tasks: {status['completed_tasks']}")
        if agent_health.get('stream_data'):
            stream = agent_health['stream_data']['data']
            print(f"    CPU: {stream.get('cpu_utilization', 0):.1f}% | Memory: {stream.get('memory_usage_mb', 0):.0f} MB")
    
    print("\n✅ Simulation complete!")
    
    # Stop all components gracefully
    for agent in agents:
        agent.stop()
    coordinator.stop()
    broker.stop()

if __name__ == "__main__":
    main()