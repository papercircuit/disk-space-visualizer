import psutil
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk
from collections import deque
import time

class DiskMonitor:
    def __init__(self):
        # Set font sizes before creating any plots
        plt.rcParams.update({
            'font.size': 5,          # Base font size
            'axes.labelsize': 5,    # Axis labels
            'axes.titlesize': 5,    # Title size
            'xtick.labelsize': 4,    # X-axis tick labels
            'ytick.labelsize': 4,    # Y-axis tick labels
        })
        
        # Initialize data structures with a maximum length
        MAX_POINTS = 3600  # Store 1 hour of data at 1 second intervals
        self.times = deque(maxlen=MAX_POINTS)
        self.usage = deque(maxlen=MAX_POINTS)
        
        # Start time should be set right before first measurement
        self.start_time = None
        
        # Create main window
        self.root = tk.Tk()
        self.root.title("Disk Space Monitor")
        self.root.geometry("700x800")
        
        # Create matplotlib figure with smaller size
        self.fig, self.ax = plt.subplots(figsize=(6, 3))
        # Adjust margins to prevent overlap
        self.fig.subplots_adjust(
            bottom=0.24,     # Increase bottom margin even more
            left=0.15,      # Decrease left margin
            right=0.92,     # Decrease right margin
            top=0.90        # Keep top margin
        )
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Initialize the plot with thinner lines
        self.line, = self.ax.plot([], [], 'b-', linewidth=1)
        self.ax.set_xlabel('Time (seconds)', labelpad=5)  # Slightly increase x-axis label padding
        self.ax.set_ylabel('Disk Usage (GB)', labelpad=2)
        self.ax.set_title('Disk Usage Monitor', pad=5)
        
        # Set y-axis limits and grid
        root_disk = psutil.disk_usage('/')
        BYTES_TO_GB = 1000 * 1000 * 1000
        self.total_gb = root_disk.total / BYTES_TO_GB
        self.ax.set_ylim(0, self.total_gb)
        self.ax.grid(True, linestyle=':', linewidth=0.5)
        
        # Create centered info text
        self.info_text = self.fig.text(0.5, 0.08, 'Initializing...',  # Add initial text to help with positioning
                                     fontsize=5,
                                     horizontalalignment='center',  # Center the text
                                     transform=self.fig.transFigure,  # Use figure coordinates
                                     bbox=dict(
                                         facecolor='white',
                                         alpha=0.8,
                                         pad=2,
                                         linewidth=0.5,
                                         boxstyle='round,pad=0.5'
                                     ))
        
        # Update interval (ms)
        self.update_interval = 1000
    
    def get_disk_usage(self):
        try:
            # Get root volume stats using 1000-based conversion (like macOS)
            root_usage = psutil.disk_usage('/')
            
            # Use 1000 instead of 1024 for conversion to match macOS
            BYTES_TO_GB = 1000 * 1000 * 1000
            total_gb = root_usage.total / BYTES_TO_GB
            available_gb = root_usage.free / BYTES_TO_GB
            
            # Calculate used space as the inverse of available
            used_gb = total_gb - available_gb
            
            # Calculate actual percentage
            percent = (used_gb / total_gb) * 100
            
            return total_gb, used_gb, available_gb, percent
            
        except Exception as e:
            print(f"Error reading disk usage: {e}")
            return 0, 0, 0, 0
    
    def update_plot(self):
        # Initialize start_time on first update
        if self.start_time is None:
            self.start_time = time.time()
            current_time = 0  # Force first point to be at 0
        else:
            current_time = time.time() - self.start_time
        
        total_gb, used_gb, available_gb, percent = self.get_disk_usage()
        
        self.times.append(current_time)
        self.usage.append(used_gb)
        
        # Convert deques to lists for plotting
        times_list = list(self.times)
        usage_list = list(self.usage)
        
        self.line.set_data(times_list, usage_list)
        self.ax.relim()
        self.ax.autoscale_view(scalex=True, scaley=False)  # Only autoscale x-axis
        
        # Add small padding to the right
        self.ax.set_xlim(left=0, right=current_time + 5)
        
        # Format info text with line breaks and shorter labels
        info_str = (
            f'Total: {total_gb:.1f}GB  •  '
            f'Used: {used_gb:.1f}GB  •  '
            f'Free: {available_gb:.1f}GB  •  '
            f'Usage: {percent:.1f}%'
        )
        
        # Update info text position and size
        self.info_text.set_position((0.5, 0.08))  # Center horizontally
        self.info_text.set_transform(self.fig.transFigure)  # Ensure using figure coordinates
        self.info_text.set_text(info_str)
        
        # Update box properties for better fit
        self.info_text.set_bbox(dict(
            facecolor='white',
            alpha=0.8,
            pad=2,
            linewidth=0.5
        ))
        
        self.canvas.draw()
        
        # Schedule next update
        self.root.after(self.update_interval, self.update_plot)
    
    def run(self):
        # Schedule first update
        self.root.after(0, self.update_plot)
        
        # Start the application
        self.root.mainloop()

if __name__ == "__main__":
    monitor = DiskMonitor()
    monitor.run()