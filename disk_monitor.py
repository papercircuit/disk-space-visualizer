import asyncio
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
import sys
import threading
from collections import deque
import signal

from utils.disk_utils import get_disk_usage
from utils.docker_utils import get_docker_usage, get_docker_usage_async
from ui.plot_manager import PlotManager
from ui.event_handlers import EventHandler

class DiskMonitor:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.aboutToQuit.connect(self.cleanup)  # Connect cleanup to quit signal
        self.selected_drive = '/'  # Default to root
        self.setup_data_structures()
        self.plot_manager = PlotManager(self)
        self.setup_update_interval()
        
        # Create async event loop
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        # Setup timer for updates
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(self.update_interval)
        
        # Flag for clean shutdown
        self.running = True
        self.paused = False
    
    def cleanup(self):
        self.running = False
        self.timer.stop()
        self.loop.call_soon_threadsafe(self.loop.stop)  # Stop event loop safely
    
    def setup_data_structures(self):
        self.times = deque()
        self.usage = deque()
        self.docker_usage = deque()
        self.start_time = None
    
    def setup_update_interval(self):
        self.update_interval = 500
    
    def get_disk_usage(self):
        return get_disk_usage(self.selected_drive)
    
    async def get_docker_usage_async(self):
        return await get_docker_usage_async()
    
    def get_docker_usage(self):
        # Return last known values if async operation is running
        if not hasattr(self, 'last_docker_values'):
            self.last_docker_values = (None, None)
        return self.last_docker_values
    
    async def update_docker_usage(self):
        while self.running:
            values = await self.get_docker_usage_async()
            self.last_docker_values = values
            await asyncio.sleep(1)
    
    def start_async_tasks(self):
        self.loop.create_task(self.update_docker_usage())
    
    def update_plot(self):
        if not self.paused:
            self.plot_manager.update()
    
    def reset_plot(self):
        self.plot_manager.reset()
    
    def run(self):
        self.start_async_tasks()
        
        # Run event loop in separate thread
        thread = threading.Thread(target=self._run_event_loop, daemon=True)
        thread.start()
        
        # Start Qt event loop
        sys.exit(self.app.exec())
    
    def _run_event_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()
    
    def pause(self):
        self.paused = True
        self.timer.stop()
    
    def resume(self):
        self.paused = False
        self.timer.start(self.update_interval)
    
    def set_drive(self, drive):
        if drive != self.selected_drive:
            self.selected_drive = drive
            self.reset_plot()