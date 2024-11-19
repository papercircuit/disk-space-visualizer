import pyqtgraph as pg
from PyQt6.QtCore import Qt
import numpy as np
import time
from PyQt6.QtWidgets import QPushButton, QVBoxLayout, QWidget, QComboBox, QHBoxLayout
import math
from utils.disk_utils import get_available_drives

class PlotManager:
    def __init__(self, monitor):
        self.monitor = monitor
        
        # Create main widget and layout first
        self.main_widget = QWidget()
        layout = QVBoxLayout()
        
        # Create plot widget
        self.win = pg.GraphicsLayoutWidget()
        self.win.setBackground('w')
        self.win.ci.setSpacing(0)  # Remove spacing between items
        
        # Create plot first
        self.plot = self.win.addPlot()
        self.plot.hideButtons()
        self.plot.showGrid(x=True, y=True, alpha=0.3)
        self.plot.setLabel('bottom', 'Time (minutes)')
        self.plot.setLabel('left', 'Disk Usage (GB)')
        self.plot.setTitle('Disk Space Monitor')
        
        # Set axis behavior
        self.plot.getViewBox().setMouseEnabled(x=False, y=False)
        self.plot.getViewBox().enableAutoRange(y=False)
        self.plot.getAxis('left').enableAutoSIPrefix(False)
        self.plot.getAxis('bottom').enableAutoSIPrefix(False)
        
        # Create curves
        self.system_curve = self.plot.plot(pen=pg.mkPen('b', width=2), name='System')
        self.docker_curve = self.plot.plot(pen=pg.mkPen('r', width=2), name='Docker')
        self.docker_capacity_line = pg.InfiniteLine(angle=0, pen=pg.mkPen('r', style=Qt.PenStyle.DashLine))
        self.plot.addItem(self.docker_capacity_line)
        
        # Create cursor line and tooltip
        self.cursor_line = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('k', style=Qt.PenStyle.DotLine))
        self.plot.addItem(self.cursor_line)
        self.tooltip = pg.TextItem(text='', anchor=(0, 1))
        self.plot.addItem(self.tooltip)
        
        # Create info label widget
        self.info_label = pg.LabelItem(justify='center')
        self.win.addItem(self.info_label, row=1, col=0)
        self.info_label.setText('Initializing...')
        
        # Add plot widget to layout first
        layout.addWidget(self.win)
        
        # Create bottom controls container
        bottom_layout = QHBoxLayout()
        
        # Create reset button
        self.reset_button = QPushButton('Reset')
        self.reset_button.clicked.connect(self.reset)
        bottom_layout.addWidget(self.reset_button)
        
        # Create pause button
        self.pause_button = QPushButton('Pause')
        self.pause_button.setCheckable(True)
        self.pause_button.clicked.connect(self.toggle_pause)
        bottom_layout.addWidget(self.pause_button)
        
        # Add spacer to push drive selector to right
        bottom_layout.addStretch()
        
        # Create drive selection combo box
        self.drive_combo = QComboBox()
        self.drive_combo.setMinimumWidth(200)  # Make dropdown wider
        self.update_drive_list()
        self.drive_combo.currentIndexChanged.connect(self.on_drive_changed)
        bottom_layout.addWidget(self.drive_combo)
        
        # Add bottom controls to main layout
        layout.addLayout(bottom_layout)
        
        # Set layout
        self.main_widget.setLayout(layout)
        self.main_widget.show()
        
        # Initialize reference points storage
        self.reference_lines = []
        self.reference_labels = []
        self.reference_data = []
        
        # Connect mouse events
        self.plot.scene().sigMouseMoved.connect(self.mouse_moved)
        self.plot.scene().sigMouseClicked.connect(self.mouse_clicked)
        
        # After creating self.plot
        self.plot.getViewBox().setDefaultPadding(0)  # Remove default padding
        self.plot.setContentsMargins(10, 10, 10, 50)  # Add bottom margin for labels

    def update_drive_list(self):
        """Update the drive selection dropdown"""
        self.drive_combo.clear()
        drives = get_available_drives()
        for mountpoint, device in drives:
            self.drive_combo.addItem(f"{mountpoint} ({device})", mountpoint)

    def on_drive_changed(self, index):
        """Handle drive selection change"""
        if index >= 0:
            new_drive = self.drive_combo.itemData(index)
            self.monitor.set_drive(new_drive)
            self.update_title()

    def update_title(self):
        """Update plot title with selected drive info"""
        drive_name = self.drive_combo.currentText().split(' (')[0]  # Get just the name part
        self.plot.setTitle(f'Disk Space Monitor - {drive_name}')

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
            self.docker_capacity_line.setValue(docker_total_gb)
            self.docker_capacity_line.show()
        else:
            self.docker_capacity_line.hide()
        
        # Append new data
        self.monitor.times.append(current_time)
        self.monitor.usage.append(used_gb)
        self.monitor.docker_usage.append(docker_used_gb if docker_used_gb is not None else 0)
        
        # Update curves
        times_array = np.array(list(self.monitor.times))
        self.system_curve.setData(times_array, np.array(list(self.monitor.usage)))
        self.docker_curve.setData(times_array, np.array(list(self.monitor.docker_usage)))
        
        # Calculate y-axis max based on total disk space
        self.y_max = total_gb
        
        # Calculate nice round number for tick intervals
        if total_gb > 500:
            major_y = 100  # Use 100GB intervals for large disks
        elif total_gb > 100:
            major_y = 50   # Use 50GB intervals for medium disks
        else:
            major_y = 10   # Use 10GB intervals for small disks
        
        # Calculate regular tick values
        tick_values = []
        
        # Add ticks from 0 up to total_gb
        current = 0
        while current <= total_gb:
            tick_values.append((current, f"{int(current)}"))
            current += major_y
        
        # Add the total as final tick if it's not already included
        if current - major_y != total_gb:
            tick_values.append((total_gb, f"{int(total_gb)}"))
        
        # Set custom ticks
        self.plot.getAxis('left').setTicks([tick_values, []])
        
        # Disable auto-scaling and set fixed range with padding
        self.plot.getViewBox().disableAutoRange()
        padding = total_gb * 0.05  # 5% padding
        self.plot.getViewBox().setLimits(yMin=0, yMax=total_gb + padding)
        self.plot.getViewBox().setRange(yRange=(0, total_gb + padding), padding=0)
        self.plot.getViewBox().setXRange(0, current_time + 0.5, padding=0)
        
        # Set x-axis ticks
        x_range = current_time + 0.5
        major_x = max(0.5, round(x_range / 5, 1))  # At least 0.5m intervals
        self.plot.getAxis('bottom').setTickSpacing(major_x, major_x/2)
        
        # Update info text
        if docker_total_gb is not None and docker_used_gb is not None:
            docker_percent = (docker_used_gb/docker_total_gb*100)
            info_str = (
                f'Total Disk: {total_gb:.1f}GB  •  '
                f'System Used: {used_gb:.1f}GB ({percent:.1f}%)  •  '
                f'Docker Used: {docker_used_gb:.1f}GB ({docker_percent:.1f}%)'
            )
        else:
            info_str = (
                f'Total Disk: {total_gb:.1f}GB  •  '
                f'System Used: {used_gb:.1f}GB ({percent:.1f}%)  •  '
                f'Docker Used: Not Available'
            )
        self.info_label.setText(info_str)

    def reset(self):
        self.monitor.times.clear()
        self.monitor.usage.clear()
        self.monitor.docker_usage.clear()
        self.monitor.start_time = None
        
        # Clear reference points and their visual elements
        for line in self.reference_lines:
            self.plot.removeItem(line)
        for label in self.reference_labels:
            self.plot.removeItem(label)
        
        # Clear stored references
        self.reference_lines.clear()
        self.reference_labels.clear()
        self.reference_data.clear()
        
        # Reset tooltip and cursor line
        self.tooltip.hide()
        self.cursor_line.hide()
        
        # Reset pause button state
        self.pause_button.setChecked(False)
        self.pause_button.setText('Pause')
        self.monitor.resume()
        
        # Force a redraw
        self.plot.replot()

    def mouse_moved(self, event):
        pos = event  # event is already a QPointF, no need for indexing
        if not self.plot.sceneBoundingRect().contains(pos):
            self.cursor_line.hide()
            self.tooltip.hide()
            return
        
        mouse_point = self.plot.vb.mapSceneToView(pos)
        x = mouse_point.x()
        
        if len(self.monitor.times) > 0:
            times_array = np.array(list(self.monitor.times))
            idx = np.abs(times_array - x).argmin()
            x_val = times_array[idx]
            sys_val = list(self.monitor.usage)[idx]
            docker_val = list(self.monitor.docker_usage)[idx]
            
            self.cursor_line.setPos(x_val)
            self.cursor_line.show()
            
            tooltip_text = f'Time: {x_val:.1f}m\nSystem Used: {sys_val:.1f}GB'
            if docker_val > 0:
                tooltip_text += f'\nDocker Used: {docker_val:.1f}GB'
            
            self.tooltip.setText(tooltip_text)
            self.tooltip.setPos(x_val, sys_val)
            self.tooltip.show()

    def mouse_clicked(self, event):
        pos = event.scenePos()
        if not self.plot.sceneBoundingRect().contains(pos):
            return
        
        mouse_point = self.plot.vb.mapSceneToView(pos)
        x = mouse_point.x()
        
        # Check if click is near any reference line
        for i, line in enumerate(self.reference_lines):
            if abs(x - line.value()) < 0.1:  # 0.1 minute threshold
                self.plot.removeItem(line)
                if i < len(self.reference_labels):
                    self.plot.removeItem(self.reference_labels[i])
                self.reference_lines.pop(i)
                self.reference_labels.pop(i)
                self.reference_data.pop(i)
                return
        
        # Add new reference line if under limit
        if len(self.reference_lines) >= 5:  # max 5 reference points
            return
        
        if len(self.monitor.times) > 0:
            times_array = np.array(list(self.monitor.times))
            idx = np.abs(times_array - x).argmin()
            x_val = times_array[idx]
            
            # Get data first
            sys_val = list(self.monitor.usage)[idx]
            docker_val = list(self.monitor.docker_usage)[idx]
            
            # Create line with unique color
            readable_colors = ['#2E86C1', '#28B463', '#8E44AD', '#D35400', '#273746']  # Blue, Green, Purple, Orange, Dark Gray
            color = pg.mkColor(readable_colors[len(self.reference_lines)])
            ref_line = pg.InfiniteLine(angle=90, movable=False, 
                                     pen=pg.mkPen(color, style=Qt.PenStyle.DashLine))
            ref_line.setValue(x_val)
            self.plot.addItem(ref_line)
            
            # Create label with same color
            stats_text = f'T{len(self.reference_lines)+1}\n{x_val:.1f}m\nSys:{sys_val:.1f}GB'
            if docker_val > 0:
                stats_text += f'\nDoc:{docker_val:.1f}GB'
            label = pg.TextItem(text=stats_text, anchor=(0, 1), color=color)  # Anchor to top-left
            # Position label below axis in the margin area
            label.setParentItem(self.plot.getAxis('bottom'))  # Attach to x-axis
            label.setPos(x_val, 0)  # Position below axis
            self.plot.addItem(label)
            
            # Store reference data
            self.reference_lines.append(ref_line)
            self.reference_labels.append(label)
            self.reference_data.append((x_val, sys_val, docker_val))

    def toggle_pause(self):
        if self.pause_button.isChecked():
            self.pause_button.setText('Resume')
            self.monitor.pause()
        else:
            self.pause_button.setText('Pause')
            self.monitor.resume()

    def refresh(self):
        """Refresh the plot without recreating the window"""
        try:
            # Reload data structures
            self.setup_data_structures()
            
            # Update plot settings
            self.plot.setTitle('Disk Space Monitor')
            self.plot.showGrid(x=True, y=True, alpha=0.3)
            
            # Force update
            self.update()
            
            print("Plot refreshed successfully")
        except Exception as e:
            print(f"Error refreshing plot: {e}")