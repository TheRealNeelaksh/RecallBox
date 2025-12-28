import subprocess
import sys
import time

def run(cmd):
    # Start a subprocess without blocking
    return subprocess.Popen(cmd, shell=True)

def main():
    processes = []

    # Server 1: Plugin proxy server
    cmd1 = "uvicorn lobechat_plugin.proxy_server:app --host 127.0.0.1 --port 5600"
    print("Starting proxy server on port 5600...")
    processes.append(run(cmd1))

    time.sleep(1)  # small delay to avoid overlap on startup

    # Server 2: Your FastAPI app
    cmd2 = "uvicorn app.main:app --host 127.0.0.1 --port 5600"
    print("Starting app server on port 5500...")
    processes.append(run(cmd2))

    # TODO: You can add LobeChat local start command here later
    # Example:
    # cmd3 = "pnpm dev"
    # processes.append(run(cmd3))

    print("All services started. Press Ctrl+C to stop.")

    try:
        # Keep script running until user stops it
        for p in processes:
            p.wait()
    except KeyboardInterrupt:
        print("\nShutting down...")
        for p in processes:
            p.terminate()
        sys.exit(0)

if __name__ == "__main__":
    main()
