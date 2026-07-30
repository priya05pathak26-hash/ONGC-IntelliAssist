"""
Backend startup script with automatic port conflict resolution.
Handles WinError 10013 by detecting and terminating stale processes.
"""
import socket
import sys
import os
import signal
import subprocess
from pathlib import Path

# Add backend to path
BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIR))

def is_port_available(port: int, host: str = "127.0.0.1") -> bool:
    """Check if a port is available for binding."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((host, port))
            return True
    except OSError:
        return False

def find_process_on_port(port: int, host: str = "127.0.0.1") -> int | None:
    """Find PID of process using the specified port."""
    try:
        # Use netstat to find the process
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True,
            text=True,
            timeout=5
        )
        for line in result.stdout.splitlines():
            if f"{host}:{port}" in line and "LISTENING" in line:
                parts = line.split()
                if parts:
                    return int(parts[-1])
    except Exception:
        pass
    return None

def kill_process(pid: int) -> bool:
    """Kill a process by PID."""
    try:
        if sys.platform == "win32":
            os.kill(pid, signal.SIGTERM)
        else:
            os.kill(pid, signal.SIGTERM)
        return True
    except Exception:
        try:
            subprocess.run(["taskkill", "/F", "/PID", str(pid)], timeout=5)
            return True
        except Exception:
            return False

def find_available_port(start_port: int = 8000, max_port: int = 8100) -> int:
    """Find the next available port starting from start_port."""
    for port in range(start_port, max_port):
        if is_port_available(port):
            return port
    raise RuntimeError(f"No available port found in range {start_port}-{max_port}")

def main():
    """Main startup logic with port conflict resolution."""
    import argparse
    
    parser = argparse.ArgumentParser(description="ONGC IntelliAssist Backend")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    args = parser.parse_args()
    
    port = args.port
    host = args.host
    
    print(f"ONGC IntelliAssist Backend Startup")
    print(f"==================================")
    print(f"Requested port: {port}")
    
    # Check if port is available
    if not is_port_available(port, host):
        print(f"\n Port {port} is already in use!")
        
        # Find the process using the port
        pid = find_process_on_port(port, host)
        if pid:
            print(f"  Found process PID {pid} using port {port}")
            
            # Check if it's a Python/uvicorn process
            try:
                result = subprocess.run(
                    ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if "python" in result.stdout.lower() or "uvicorn" in result.stdout.lower():
                    print(f"  Process appears to be a stale Python/uvicorn instance")
                    print(f"  Attempting to terminate PID {pid}...")
                    
                    if kill_process(pid):
                        print(f"  [OK] Successfully terminated PID {pid}")
                        # Wait a moment for the port to be released
                        import time
                        time.sleep(2)
                        
                        # Verify port is now available
                        if is_port_available(port, host):
                            print(f"  [OK] Port {port} is now available")
                        else:
                            print(f"  [WARN] Port {port} still not available, finding alternative...")
                            port = find_available_port(port + 1)
                            print(f"  [OK] Using alternative port: {port}")
                    else:
                        print(f"  [FAIL] Failed to terminate PID {pid}")
                        print(f"  Finding alternative port...")
                        port = find_available_port(port + 1)
                        print(f"  [OK] Using alternative port: {port}")
                else:
                    print(f"  Process is not Python/uvicorn: {result.stdout.strip()}")
                    print(f"  Finding alternative port...")
                    port = find_available_port(port + 1)
                    print(f"  [OK] Using alternative port: {port}")
            except Exception as e:
                print(f"  Error checking process: {e}")
                print(f"  Finding alternative port...")
                port = find_available_port(port + 1)
                print(f"  [OK] Using alternative port: {port}")
        else:
            print(f"  Could not identify process using port {port}")
            print(f"  Finding alternative port...")
            port = find_available_port(port + 1)
            print(f"  [OK] Using alternative port: {port}")
    
    print(f"\n[OK] Starting backend on {host}:{port}")
    
    # Build uvicorn command
    cmd = [
        sys.executable, "-m", "uvicorn",
        "app.main:app",
        "--host", host,
        "--port", str(port),
    ]
    
    if args.reload:
        cmd.append("--reload")
    
    print(f"  Command: {' '.join(cmd)}")
    print(f"\n{'='*50}")
    print(f"Backend is starting...")
    print(f"{'='*50}\n")
    
    # Execute uvicorn
    try:
        os.chdir(BACKEND_DIR)
        os.execv(sys.executable, cmd)
    except Exception as e:
        print(f"\n Failed to start backend: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
