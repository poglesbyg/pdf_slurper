#!/usr/bin/env python
"""Simple script to start the new PDF Slurper v2 services."""

import subprocess
import time
import signal
import sys
import os
from pathlib import Path

def main():
    """Start both API and Web UI services."""
    print("🚀 Starting PDF Slurper v2 Services")
    print("=" * 50)
    
    # Change to the correct directory
    project_dir = Path(__file__).parent
    os.chdir(project_dir)
    print(f"Working directory: {project_dir}")
    
    # Start API server
    print("🔧 Starting API Server...")
    api_process = subprocess.Popen([
        "uv", "run", "python", "run_api.py"
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # Wait for API to be fully ready
    print("⏳ Waiting for API server to be ready...")
    api_ready = False
    for i in range(30):  # Wait up to 30 seconds
        try:
            import requests
            response = requests.get("http://localhost:8080/health", timeout=2)
            if response.status_code == 200:
                print("✅ API Server is ready!")
                api_ready = True
                break
        except:
            pass
        time.sleep(1)
        print(f"   Waiting... ({i+1}/30)")
    
    if not api_ready:
        print("❌ API Server failed to start")
        api_process.terminate()
        return
    
    # Start Web UI
    print("🌐 Starting Web UI...")
    web_process = subprocess.Popen([
        "uv", "run", "python", "run_web_ui.py"
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # Wait for Web UI to be ready
    print("⏳ Waiting for Web UI to be ready...")
    web_ready = False
    for i in range(30):  # Wait up to 30 seconds
        try:
            import requests
            response = requests.get("http://localhost:3000/health", timeout=2)
            if response.status_code == 200:
                print("✅ Web UI is ready!")
                web_ready = True
                break
        except:
            pass
        time.sleep(1)
        print(f"   Waiting... ({i+1}/30)")
    
    if not web_ready:
        print("⚠️ Web UI may not be fully ready, but continuing...")
        web_ready = True  # Continue anyway
    
    print("\n🎉 Services started!")
    print("\n📱 Access Points:")
    print(f"   Web UI: http://localhost:3000")
    print(f"   API: http://localhost:8080")
    print(f"   API Docs: http://localhost:8080/api/docs")
    print(f"   Health: http://localhost:8080/health")
    
    print("\n⏹️  Press Ctrl+C to stop all services")
    
    def signal_handler(sig, frame):
        print("\n\n🛑 Stopping services...")
        api_process.terminate()
        web_process.terminate()
        
        # Wait for graceful shutdown
        try:
            api_process.wait(timeout=5)
            web_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            api_process.kill()
            web_process.kill()
        
        print("✅ All services stopped")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        # Keep services running
        while True:
            time.sleep(1)
            
            # Check if processes are still running
            if api_process.poll() is not None:
                print("❌ API server stopped unexpectedly")
                break
            if web_process.poll() is not None:
                print("❌ Web UI stopped unexpectedly")
                break
                
    except KeyboardInterrupt:
        pass
    finally:
        signal_handler(None, None)

if __name__ == "__main__":
    main()
