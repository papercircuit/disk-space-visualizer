import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import time
import numpy as np

class PlotManager:
    def __init__(self, monitor):
        self.monitor = monitor
        self.setup_plot_style()
        self.create_plot()
        self.setup_lines()
        self.setup_annotations()
        
    def setup_plot_style(self):
        plt.rcParams.update({
            'font.size': 5,
            'axes.labelsize': 5,
            'axes.titlesize': 5,
            'xtick.labelsize': 4,
            'ytick.labelsize': 4,
        })
    
    def create_plot(self):
        self.fig, self.ax = plt.subplots(figsize=(6, 4))
        
        # Adjust margins
        self.fig.subplots_adjust(
            bottom=0.25,
            left=0.15,
            right=0.92,
            top=0.95
        )
        
        # Create canvas
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.monitor.root)
        self.canvas.get_tk_widget().pack(fill='both', expand=True)
        
        # Set labels and title
        self.ax.set_xlabel('Time (minutes)', labelpad=5)
        self.ax.set_ylabel('Disk Usage (GB)', labelpad=2)
        self.ax.set_title('Disk Usage Monitor', pad=5)
        
        # Set y-axis limits and grid
        root_disk = self.monitor.get_disk_usage()[0]  # Get total disk size
        self.ax.set_ylim(0, root_disk)
        self.ax.grid(True, linestyle=':', linewidth=0.5)
        
        # Create info text
        self.info_text = self.fig.text(0.5, 0.15,
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
    
    def setup_lines(self):
        # System usage line
        self.line, = self.ax.plot([], [], 'b-', linewidth=1, label='System')
        
        # Docker usage line
        self.docker_line, = self.ax.plot([], [], 'r-', linewidth=1, label='Docker Usage')
        
        # Docker capacity line
        self.docker_capacity_line = self.ax.axhline(y=0, color='r', linestyle='--', alpha=0.3, linewidth=1, label='Docker Capacity')
        
        # Add legend
        self.ax.legend(fontsize=5, loc='upper right')
        
        # Initialize background for blitting
        self.canvas.draw()
        self.background = self.canvas.copy_from_bbox(self.fig.bbox)
    
    def setup_annotations(self):
        # Cursor line for hover effect
        self.cursor_line = self.ax.axvline(x=0, color='gray', linestyle=':', alpha=0, linewidth=0.8)
        self.cursor_line.set_ydata([0, self.ax.get_ylim()[1]])
        
        # Tooltip annotation
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
    
    def update(self):
        if self.monitor.start_time is None:
            self.monitor.start_time = time.time()
            current_time = 0
        else:
            current_time = (time.time() - self.monitor.start_time) / 60

        # Get system usage
        total_gb, used_gb, available_gb, percent = self.monitor.get_disk_usage()
        
        # Get Docker usage
        docker_total_gb, docker_used_gb = self.monitor.get_docker_usage()
        
        # Update Docker capacity line
        if docker_total_gb is not None:
            self.docker_capacity_line.set_ydata([docker_total_gb, docker_total_gb])
            self.docker_capacity_line.set_alpha(0.3)
        else:
            self.docker_capacity_line.set_alpha(0)
        
        # Append new data
        self.monitor.times.append(current_time)
        self.monitor.usage.append(used_gb)
        self.monitor.docker_usage.append(docker_used_gb if docker_used_gb is not None else 0)

        # Update lines
        times_list = list(self.monitor.times)
        self.line.set_data(times_list, list(self.monitor.usage))
        self.docker_line.set_data(times_list, list(self.monitor.docker_usage))
        
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
    
    def reset(self):
        # Clear all data
        self.monitor.times.clear()
        self.monitor.usage.clear()
        self.monitor.docker_usage.clear()
        
        # Reset start time
        self.monitor.start_time = None
        
        # Reset plot data
        self.line.set_data([], [])
        self.docker_line.set_data([], [])
        
        # Reset x-axis limits
        self.ax.set_xlim(left=0, right=0.5)
        
        # Reset Docker capacity line
        self.docker_capacity_line.set_ydata([0, 0])
        self.docker_capacity_line.set_alpha(0)
        
        # Clear all references through event handler
        for line in self.monitor.event_handler.reference_lines:
            line.remove()
        for label in self.monitor.event_handler.reference_labels:
            label.remove()
        for text in self.monitor.event_handler.reference_texts:
            text.remove()
            
        self.monitor.event_handler.reference_lines.clear()
        self.monitor.event_handler.reference_labels.clear()
        self.monitor.event_handler.reference_texts.clear()
        self.monitor.event_handler.reference_data.clear()
        
        # Force redraw
        self.canvas.draw()
        self.background = self.canvas.copy_from_bbox(self.fig.bbox)