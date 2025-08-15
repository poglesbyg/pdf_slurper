#!/usr/bin/env python
"""Start both API and Web UI services for testing."""

import subprocess
import time
import signal
import sys
from pathlib import Path

def start_service(name, command, port):
    """Start a service and return the process."""
    print(f"🚀 Starting {name}...")
    try:
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait a bit for startup
        time.sleep(2)
        
        if process.poll() is None:
            print(f"✅ {name} started on port {port}")
            return process
        else:
            print(f"❌ {name} failed to start")
            return None
            
    except Exception as e:
        print(f"❌ Failed to start {name}: {e}")
        return None

def check_service(port, name):
    """Check if a service is responding."""
    import requests
    try:
        response = requests.get(f"http://localhost:{port}/health", timeout=5)
        if response.status_code == 200:
            print(f"✅ {name} is responding on port {port}")
            return True
        else:
            print(f"⚠️ {name} responded with status {response.status_code}")
            return False
    except requests.exceptions.RequestException:
        print(f"❌ {name} not responding on port {port}")
        return False

def main():
    """Start both services."""
    print("🚀 Starting PDF Slurper v2 Services")
    print("=" * 50)
    
    # Start API server
    api_process = start_service(
        "API Server", 
        "uv run python run_api.py", 
        8080
    )
    
    if not api_process:
        print("❌ Failed to start API server. Exiting.")
        sys.exit(1)
    
    # Wait for API to be ready
    time.sleep(3)
    
    # Start Web UI
    web_process = start_service(
        "Web UI", 
        "uv run python run_web_ui.py", 
        3000
    )
    
    if not web_process:
        print("❌ Failed to start Web UI. Exiting.")
        api_process.terminate()
        sys.exit(1)
    
    # Wait for Web UI to be ready
    time.sleep(3)
    
    print("\n" + "=" * 50)
    print("🔍 Checking service health...")
    
    # Check both services
    api_healthy = check_service(8080, "API Server")
    web_healthy = check_service(3000, "Web UI")
    
    if api_healthy and web_healthy:
        print("\n🎉 All services are running!")
        print("\n📱 Access Points:")
        print(f"   Web UI: http://localhost:3000")
        print(f"   API: http://localhost:8080")
        print(f"   API Docs: http://localhost:8080/api/docs")
        print(f"   Health: http://localhost:8080/health")
        print(f"   Web Health: http://localhost:3000/health")
        
        print("\n⏹️  Press Ctrl+C to stop all services")
        
        try:
            # Keep services running
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\n🛑 Stopping services...")
            api_process.terminate()
            web_process.terminate()
            
            # Wait for graceful shutdown
            api_process.wait(timeout=5)
            web_process.wait(timeout=5)
            
            print("✅ All services stopped")
            
    else:
        print("\n⚠️ Some services are not healthy. Stopping...")
        api_process.terminate()
        web_process.terminate()
        sys.exit(1)

if __name__ == "__main__":
    main()
