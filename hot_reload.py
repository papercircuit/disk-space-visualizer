from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import sys
import os
import subprocess
import time

class CodeChangeHandler(FileSystemEventHandler):
    def __init__(self):
        self.last_reload = time.time()
        self.reload_delay = 5 # Minimum seconds between reloads
        self.process = None
        self.start_app()

    def start_app(self):
        if self.process:
            self.process.terminate()
            self.process.wait()
        
        # Start the application in a new process
        self.process = subprocess.Popen([sys.executable, 'main.py'])

    def on_modified(self, event):
        if event.src_path.endswith('.py'):
            current_time = time.time()
            if current_time - self.last_reload > self.reload_delay:
                print(f"\nReloading due to changes in {os.path.basename(event.src_path)}...")
                self.last_reload = current_time
                self.start_app()

def start_hot_reload():
    event_handler = CodeChangeHandler()
    observer = Observer()
    observer.schedule(event_handler, path='.', recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        if event_handler.process:
            event_handler.process.terminate()
        observer.stop()
    observer.join()