import asyncio
import tkinter as tk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from collections import deque
from functools import partial

from utils.disk_utils import get_disk_usage
from utils.docker_utils import get_docker_usage, get_docker_usage_async
from ui.plot_manager import PlotManager
from ui.event_handlers import EventHandler

class DiskMonitor:
    def __init__(self):
        self.setup_window()
        self.setup_data_structures()
        self.plot_manager = PlotManager(self)
        self.event_handler = EventHandler(self)
        self.setup_update_interval()
        
        # Create async event loop
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
    
    def setup_window(self):
        self.root = tk.Tk()
        self.root.title("Disk Space Monitor")
        self.root.geometry("700x800")
        
        self.control_frame = tk.Frame(self.root)
        self.control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.reset_button = tk.Button(self.control_frame, text="Reset", command=self.reset_plot)
        self.reset_button.pack(side=tk.LEFT)
    
    def setup_data_structures(self):
        self.times = deque()
        self.usage = deque()
        self.docker_usage = deque()
        self.start_time = None
    
    def setup_update_interval(self):
        self.update_interval = 500
    
    def get_disk_usage(self):
        return get_disk_usage()
    
    async def get_docker_usage_async(self):
        return await get_docker_usage_async()
    
    def get_docker_usage(self):
        # Return last known values if async operation is running
        if not hasattr(self, 'last_docker_values'):
            self.last_docker_values = (None, None)
        return self.last_docker_values
    
    async def update_docker_usage(self):
        while True:
            self.last_docker_values = await self.get_docker_usage_async()
            await asyncio.sleep(1)  # Update every second
    
    def start_async_tasks(self):
        self.loop.create_task(self.update_docker_usage())
    
    def update_plot(self):
        self.plot_manager.update()
        self.root.after(self.update_interval, self.update_plot)
    
    def reset_plot(self):
        self.plot_manager.reset()
    
    def run(self):
        # Start async tasks in background
        self.start_async_tasks()
        
        # Run event loop in separate thread
        import threading
        thread = threading.Thread(target=self._run_event_loop, daemon=True)
        thread.start()
        
        # Start UI update
        self.root.after(0, self.update_plot)
        self.root.mainloop()
    
    def _run_event_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()