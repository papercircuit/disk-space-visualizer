import psutil
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk
from collections import deque
import time
import numpy as np
import subprocess

class DiskMonitor:
    def __init__(self):
        # Just these basic tracking variables
        self.background = None
        self.last_mouse_pos = None
        self.last_update_time = 0
        self.throttle_delay = 1/30  # 30fps throttle
        self.reference_texts = []  # Store text objects for reference labels
        self.max_references = 5
        
        # Set font sizes before creating any plots
        plt.rcParams.update({
            'font.size': 5,          # Base font size
            'axes.labelsize': 5,    # Axis labels
            'axes.titlesize': 5,    # Title size
            'xtick.labelsize': 4,    # X-axis tick labels
            'ytick.labelsize': 4,    # Y-axis tick labels
        })
        
        # Initialize data structures
        self.times = deque()
        self.usage = deque()
        
        # Start time should be set right before first measurement
        self.start_time = None
        
        # Create main window
        self.root = tk.Tk()
        self.root.title("Disk Space Monitor")
        self.root.geometry("700x800")
        
        # Create matplotlib figure (remove the second axis)
        self.fig, self.ax = plt.subplots(figsize=(6, 4))
        
        # Create frame for controls
        self.control_frame = tk.Frame(self.root)
        self.control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Add reset button
        self.reset_button = tk.Button(self.control_frame, text="Reset", command=self.reset_plot)
        self.reset_button.pack(side=tk.LEFT)
        
        # Adjust margins to better accommodate both info box and reference texts
        self.fig.subplots_adjust(
            bottom=0.25,     # Reduced to move plot up
            left=0.15,      
            right=0.92,     
            top=0.95
        )
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Initialize the plot with thinner lines
        self.line, = self.ax.plot([], [], 'b-', linewidth=1)
        self.ax.set_xlabel('Time (minutes)', labelpad=5)  # Changed from seconds to minutes
        self.ax.set_ylabel('Disk Usage (GB)', labelpad=2)
        self.ax.set_title('Disk Usage Monitor', pad=5)
        
        # Set y-axis limits and grid
        root_disk = psutil.disk_usage('/')
        BYTES_TO_GB = 1000 * 1000 * 1000
        self.total_gb = root_disk.total / BYTES_TO_GB
        self.ax.set_ylim(0, self.total_gb)
        self.ax.grid(True, linestyle=':', linewidth=0.5)
        
        # Create centered info text with higher position
        self.info_text = self.fig.text(0.5, 0.15,  # Moved up from 0.08
                                     'Initializing...',
                                     fontsize=5,
                                     horizontalalignment='center',
                                     transform=self.fig.transFigure,
                                     bbox=dict(
                                         facecolor='white',
                                         alpha=0.8,
                                         pad=2,
                                         linewidth=0.5,
                                         boxstyle='round,pad=0.5'
                                     ))
        
        # Update interval (ms)
        self.update_interval = 100
        
        # Add after creating the plot
        self.cursor_line = self.ax.axvline(x=0, color='gray', linestyle=':', alpha=0, linewidth=0.8)
        self.cursor_line.set_ydata([0, self.total_gb])
        self.tooltip_annotation = self.ax.annotate('', 
            xy=(0, 0), 
            xytext=(10, 10), 
            textcoords='offset points',
            bbox=dict(
                boxstyle='round,pad=0.5',
                fc='white',
                alpha=0.8,
                linewidth=0.5
            ),
            fontsize=5,
            visible=False
        )
        
        # Add this line for the reference line
        self.reference_line = self.ax.axvline(x=0, color='red', linestyle='--', alpha=0, linewidth=0.8)
        
        # Add click event handler
        self.canvas.mpl_connect('button_press_event', self.on_click)
        
        # Connect mouse events
        self.canvas.mpl_connect('draw_event', self.on_draw)
        self.canvas.mpl_connect('motion_notify_event', self.on_mouse_move)
        self.canvas.mpl_connect('axes_leave_event', self.on_mouse_leave)
        
        # Add this after creating the canvas
        self.canvas.draw()
        self.background = self.canvas.copy_from_bbox(self.fig.bbox)
        
        # Add after other instance variables
        self.reference_lines = []  # Store reference line objects
        self.reference_data = []   # Store reference line data
        self.reference_labels = []  # Store the text objects
        self.max_references = 5
        
        # Initialize storage for reference elements
        self.reference_lines = []
        self.reference_data = []
        self.reference_labels = []  # Store the tick labels
        self.reference_texts = []   # Store the text objects
        self.max_references = 5
        
        # Add Docker container configuration
        self.docker_config = {
            'image_name': 'localmssql_prokit_database',
            'container_name': 'localmssql'
        }
        
        # Add Docker usage lines
        self.docker_usage = deque()
        self.docker_line, = self.ax.plot([], [], 'r-', linewidth=1, label='Docker Usage')
        self.line.set_label('System')  # Add label to existing line
        
        # Add Docker capacity line (horizontal)
        self.docker_capacity_line = self.ax.axhline(y=0, color='r', linestyle='--', alpha=0.3, linewidth=1, label='Docker Capacity')
        
        # Add legend with all three lines
        self.ax.legend(fontsize=5, loc='upper right')
    
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
    
    def get_docker_container_name(self):
        try:
            # Get list of running containers
            cmd = "docker ps --format '{{.Names}}' | grep -i prokit_database"
            container_name = subprocess.check_output(cmd, shell=True, text=True).strip()
            return container_name
        except Exception as e:
            print(f"Error finding Docker container: {e}")
            return None
    
    def get_docker_usage(self):
        try:
            # Get current container name
            container_name = self.get_docker_container_name()
            if not container_name:
                return None, None

            # Get root filesystem usage (where SQL Server data is stored)
            cmd = f"docker exec {container_name} df -k / | tail -1"
            result = subprocess.check_output(cmd, shell=True, text=True).strip()
            
            # Split the df output and get total and used
            parts = result.split()
            if len(parts) >= 4:  # Make sure we have enough columns
                total_kb = float(parts[1])  # Convert to float first
                used_kb = float(parts[2])
                
                # Convert KB to GB (using 1024 for proper binary conversion)
                total_gb = total_kb / (1024 * 1024)  # KB to GB
                used_gb = used_kb / (1024 * 1024)    # KB to GB
                
                return total_gb, used_gb
                
            return None, None
                
        except Exception as e:
            print(f"Error reading Docker disk usage: {e}")
            return None, None
    
    def update_plot(self):
        # Initialize start_time on first update
        if self.start_time is None:
            self.start_time = time.time()
            current_time = 0
        else:
            current_time = (time.time() - self.start_time) / 60

        # Get system usage
        total_gb, used_gb, available_gb, percent = self.get_disk_usage()
        
        # Get Docker usage
        docker_total_gb, docker_used_gb = self.get_docker_usage()
        
        # Update Docker capacity line if we have valid data
        if docker_total_gb is not None:
            self.docker_capacity_line.set_ydata([docker_total_gb, docker_total_gb])
            self.docker_capacity_line.set_alpha(0.3)  # Make visible
        else:
            self.docker_capacity_line.set_alpha(0)  # Hide if no data
        
        # Append time and system usage
        self.times.append(current_time)
        self.usage.append(used_gb)
        
        # Append Docker usage (with proper handling of None)
        if docker_used_gb is not None:
            self.docker_usage.append(docker_used_gb)
        else:
            self.docker_usage.append(0)

        # Update both lines
        times_list = list(self.times)
        self.line.set_data(times_list, list(self.usage))
        self.docker_line.set_data(times_list, list(self.docker_usage))
        
        # Update axis limits
        self.ax.relim()
        self.ax.autoscale_view(scalex=True, scaley=False)
        self.ax.set_xlim(left=0, right=current_time + 0.5)
        
        # Update info text
        if docker_total_gb is not None and docker_used_gb is not None:
            docker_percent = (docker_used_gb/docker_total_gb*100)
            info_str = (
                f'System: {used_gb:.1f}/{total_gb:.1f}GB ({percent:.1f}%)  •  '
                f'Docker: {docker_used_gb:.1f}/{docker_total_gb:.1f}GB ({docker_percent:.1f}%)'
            )
        else:
            info_str = (
                f'System: {used_gb:.1f}/{total_gb:.1f}GB ({percent:.1f}%)  •  '
                f'Docker: Not Available'
            )
        
        self.info_text.set_text(info_str)
        
        # Force redraw
        self.canvas.draw()
        self.background = self.canvas.copy_from_bbox(self.fig.bbox)
        
        # Schedule next update
        self.root.after(self.update_interval, self.update_plot)
    
    def on_draw(self, event):
        # Cache the background when the figure is drawn
        self.background = self.canvas.copy_from_bbox(self.fig.bbox)
    
    def on_mouse_move(self, event):
        if not event.inaxes == self.ax:
            self.cursor_line.set_alpha(0)
            self.tooltip_annotation.set_visible(False)
            self.canvas.draw_idle()
            return

        if not (event.xdata <= max(self.times) and event.xdata >= 0):
            self.cursor_line.set_alpha(0)
            self.tooltip_annotation.set_visible(False)
            self.canvas.draw_idle()
            return

        # Simple throttle
        current_time = time.time()
        if current_time - self.last_update_time < self.throttle_delay:
            return
        self.last_update_time = current_time

        # Update hover elements
        self.cursor_line.set_xdata([event.xdata, event.xdata])
        self.cursor_line.set_alpha(0.5)

        if len(self.times) > 0:
            times_array = np.array(self.times)
            idx = np.abs(times_array - event.xdata).argmin()
            x_val = times_array[idx]
            y_val = list(self.usage)[idx]

            self.tooltip_annotation.xy = (x_val, y_val)
            self.tooltip_annotation.set_text(f'Time: {x_val:.1f}m\nUsage: {y_val:.1f}GB')
            self.tooltip_annotation.set_visible(True)

        self.canvas.draw_idle()

    def on_mouse_leave(self, event):
        self.cursor_line.set_alpha(0)
        self.tooltip_annotation.set_visible(False)
        self.canvas.draw_idle()
    
    def on_click(self, event):
        if not event.inaxes == self.ax:
            return
        
        # Get click coordinates in data space
        click_x = event.xdata
        click_y = event.ydata
        
        # Check if click is near any reference line
        for i, (ref_time, _, _) in enumerate(self.reference_data):  # Updated to handle 3 values
            # Check if click is within small distance of reference line
            if abs(click_x - ref_time) < 0.01:  # Adjust threshold as needed
                # Remove corresponding line, label, data and text
                self.reference_lines[i].remove()
                self.reference_labels[i].remove()
                self.reference_data.pop(i)
                if i < len(self.reference_texts):
                    self.reference_texts[i].remove()
                    self.reference_texts.pop(i)
                
                # Remove from tracking lists
                self.reference_lines.pop(i)
                self.reference_labels.pop(i)
                
                # Redraw remaining references with updated numbers
                self._update_reference_numbers()
                self.canvas.draw_idle()
                return

        # Don't add new reference if at max
        if len(self.reference_lines) >= self.max_references:
            return
        
        # Check if click is within valid data range
        if not (click_x <= max(self.times) and click_x >= 0):
            return

        # Find closest data point for both system and Docker
        times_array = np.array(self.times)
        idx = np.abs(times_array - click_x).argmin()
        x_val = times_array[idx]
        sys_val = list(self.usage)[idx]
        docker_val = list(self.docker_usage)[idx]

        # Create new reference line with unique color
        color = plt.cm.Set3(len(self.reference_lines) / self.max_references)
        ref_line = self.ax.axvline(x=x_val, color=color, linestyle='--', alpha=0.7, linewidth=0.8)
        
        # Add rotated label under the line
        label = self.ax.text(x_val, -0.05, f'T{len(self.reference_lines)+1}', 
            rotation=45,
            horizontalalignment='right',
            verticalalignment='top',
            transform=self.ax.get_xaxis_transform(),
            color=color)
        
        # Store reference line, label and data (now including Docker value)
        self.reference_lines.append(ref_line)
        self.reference_labels.append(label)
        self.reference_data.append((x_val, sys_val, docker_val))

        # Clear existing reference texts
        for text in self.reference_texts:
            text.remove()
        self.reference_texts.clear()

        # Create new text objects for each reference with better spacing
        num_refs = len(self.reference_data)
        if num_refs > 0:
            # Calculate spacing to spread texts evenly horizontally
            total_width = 0.7
            start_pos = 0.15
            gap = total_width / (self.max_references - 1) if num_refs > 1 else total_width

            for i, (t, v, d) in enumerate(self.reference_data):
                color_i = plt.cm.Set3(i / self.max_references)
                x_pos = start_pos + (i * gap)
                
                # Create vertical text with each piece of info on its own line
                text = self.fig.text(x_pos, 0.02,
                    f'T{i+1}:\n{t:.1f}m\nSys:{v:.1f}GB\nDoc:{d:.1f}GB',
                    color=color_i,
                    fontsize=5,
                    horizontalalignment='left',
                    verticalalignment='bottom',
                    transform=self.fig.transFigure)
                self.reference_texts.append(text)

        # Redraw
        self.canvas.draw_idle()
    
    def _update_reference_numbers(self):
        """Update the T1, T2, etc. numbers for all references after removal"""
        # Update diagonal labels
        for i, label in enumerate(self.reference_labels):
            label.set_text(f'T{i+1}')
            color = plt.cm.Set3(i / self.max_references)
            label.set_color(color)
            self.reference_lines[i].set_color(color)

        # Clear and update reference texts at bottom
        for text in self.reference_texts:
            text.remove()
        self.reference_texts.clear()

        # Recreate reference texts with new numbers
        num_refs = len(self.reference_data)
        if num_refs > 0:
            total_width = 0.7
            start_pos = 0.15
            gap = total_width / (self.max_references - 1) if num_refs > 1 else total_width

            for i, (t, v, d) in enumerate(self.reference_data):
                color_i = plt.cm.Set3(i / self.max_references)
                x_pos = start_pos + (i * gap)
                
                # Create vertical text with adjusted position and spacing
                text = self.fig.text(x_pos, 0.02,  # Keep at bottom
                    f'T{i+1}:\n{t:.1f}m\nSys:{v:.1f}GB\nDoc:{d:.1f}GB',
                    color=color_i,
                    fontsize=5,
                    horizontalalignment='left',
                    verticalalignment='bottom',
                    transform=self.fig.transFigure,
                    bbox=dict(  # Add a white background to prevent overlap
                        facecolor='white',
                        alpha=0.8,
                        pad=1,
                        edgecolor='none'
                    ))
                self.reference_texts.append(text)
    
    def reset_plot(self):
        # Clear data collections
        self.times.clear()
        self.usage.clear()
        
        # Reset start time
        self.start_time = None
        
        # Clear reference lines and labels
        for line in self.reference_lines:
            line.remove()
        for label in self.reference_labels:
            label.remove()
        for text in self.reference_texts:
            text.remove()
            
        self.reference_lines.clear()
        self.reference_labels.clear()
        self.reference_texts.clear()
        self.reference_data.clear()
        
        # Reset plot data
        self.line.set_data([], [])
        
        # Reset x-axis limits
        self.ax.set_xlim(left=0, right=0.5)  # 0.5 minutes initial view
        
        # Clear Docker usage
        self.docker_usage.clear()
        self.docker_line.set_data([], [])
        
        # Reset Docker capacity line
        self.docker_capacity_line.set_ydata([0, 0])
        self.docker_capacity_line.set_alpha(0)
        
        # Force redraw
        self.canvas.draw()
        self.background = self.canvas.copy_from_bbox(self.fig.bbox)
    
    def run(self):
        # Schedule first update
        self.root.after(0, self.update_plot)
        
        # Start the application
        self.root.mainloop()

if __name__ == "__main__":
    monitor = DiskMonitor()
    monitor.run()