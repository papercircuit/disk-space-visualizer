import pyqtgraph as pg
from PyQt6.QtCore import Qt
import numpy as np
import time
from PyQt6.QtWidgets import QPushButton, QVBoxLayout, QWidget, QComboBox, QHBoxLayout, QSlider, QLabel
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
        
        # Set default X range to 5 minutes and ensure it starts at 0
        self.default_window = 5  # 5 minutes
        self.plot.getViewBox().setXRange(0, self.default_window, padding=0)
        self.plot.getViewBox().setLimits(xMin=0)  # Ensure x-axis starts at 0
        
        # Add menu items for zoom control
        self.plot.getViewBox().menu.addSeparator()
        self.plot.getViewBox().menu.addAction('Reset View').triggered.connect(self.reset_view)
        
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
        
        # Create zoom slider
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setMinimum(5)  # 5 minutes minimum
        self.zoom_slider.setMaximum(20)  # 20 minutes maximum
        self.zoom_slider.setValue(10)  # Default 10 minute view
        self.zoom_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.zoom_slider.setTickInterval(5)
        self.zoom_slider.valueChanged.connect(self.on_zoom_changed)
        
        # Add zoom controls to bottom layout
        zoom_layout = QHBoxLayout()
        zoom_layout.addWidget(QLabel("Zoom (minutes):"))
        zoom_layout.addWidget(self.zoom_slider)
        bottom_layout.addLayout(zoom_layout)
        
        # Create time navigation slider
        time_layout = QHBoxLayout()
        time_layout.addWidget(QLabel("Time Navigation:"))
        self.time_slider = QSlider(Qt.Orientation.Horizontal)
        self.time_slider.setMinimum(0)
        self.time_slider.setMaximum(100)  # We'll update this dynamically
        self.time_slider.setValue(100)  # Start at latest time
        self.time_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.time_slider.setTickInterval(10)
        self.time_slider.valueChanged.connect(self.on_time_changed)
        time_layout.addWidget(self.time_slider)
        
        # Add time navigation to bottom layout
        bottom_layout.addLayout(time_layout)
        
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
        
        # Update plot data
        times_array = np.array(list(self.monitor.times))
        self.system_curve.setData(times_array, np.array(list(self.monitor.usage)))
        self.docker_curve.setData(times_array, np.array(list(self.monitor.docker_usage)))

        # Get current view range
        view_range = self.plot.getViewBox().viewRange()
        current_max_x = view_range[0][1]

        # Auto-scroll if viewing the latest data
        if current_max_x >= max(times_array) - 0.1 or current_max_x == self.default_window:
            self.plot.getViewBox().setXRange(
                max(0, current_time - self.default_window),
                max(self.default_window, current_time),
                padding=0
            )

        # Ensure minimum x is always 0
        self.plot.getViewBox().setLimits(xMin=0)

        # Update y-axis
        padding = total_gb * 0.05
        self.plot.getViewBox().setYRange(0, total_gb + padding, padding=0)
        
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
            tick_values.append((current, f"{int(current)}GB"))
            current += major_y
        
        # Add the total as final tick if it's not already included
        if current - major_y != total_gb:
            tick_values.append((total_gb, f"{int(total_gb)}GB"))
        
        # Set custom ticks
        self.plot.getAxis('left').setTicks([tick_values, []])
        
        # Set x-axis ticks based on zoom level
        x_range = view_range[0][1] - view_range[0][0]  # Current visible range

        # Calculate appropriate tick spacing based on zoom level
        if x_range <= 5:  # 5 minutes or less
            major_x = 0.5  # 30 second intervals
        elif x_range <= 15:
            major_x = 1.0  # 1 minute intervals
        elif x_range <= 30:
            major_x = 2.0  # 2 minute intervals
        else:
            major_x = 5.0  # 5 minute intervals

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

        # Update time slider range if viewing latest data
        if len(self.monitor.times) > 0:
            current_value = self.time_slider.value()
            if current_value == self.time_slider.maximum():  # If slider was at the end
                self.time_slider.setValue(100)  # Keep it at the end
            self.time_slider.setEnabled(True)
        else:
            self.time_slider.setEnabled(False)

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
        
        # Reset zoom slider
        self.zoom_slider.setValue(5)
        
        # Reset to default 5-minute view starting at 0
        self.plot.getViewBox().setXRange(0, self.default_window, padding=0)
        self.plot.getViewBox().setLimits(xMin=0)
        
        # Reset time slider
        self.time_slider.setValue(100)
        
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

    def reset_view(self):
        """Reset view to show last 5 minutes"""
        if len(self.monitor.times) > 0:
            latest_time = max(self.monitor.times)
            self.plot.getViewBox().setXRange(
                max(0, latest_time - self.default_window),
                latest_time,
                padding=0
            )

    def on_zoom_changed(self, value):
        """Handle zoom slider change"""
        self.default_window = value
        if len(self.monitor.times) > 0:
            latest_time = max(self.monitor.times)
            self.plot.getViewBox().setXRange(
                max(0, latest_time - self.default_window),
                latest_time,
                padding=0
            )
            
            # Update x-axis ticks immediately
            if value <= 5:  # 5 minutes or less
                major_x = 0.5  # 30 second intervals
            elif value <= 15:
                major_x = 1.0  # 1 minute intervals
            elif value <= 30:
                major_x = 2.0  # 2 minute intervals
            else:
                major_x = 5.0  # 5 minute intervals
            
            self.plot.getAxis('bottom').setTickSpacing(major_x, major_x/2)

    def on_time_changed(self, value):
        """Handle time slider change"""
        if len(self.monitor.times) == 0:
            return
        
        # Convert percentage to time
        latest_time = max(self.monitor.times)
        earliest_time = max(0, latest_time - self.default_window)
        total_time = max(self.monitor.times)
        
        # Calculate target time based on slider percentage
        target_time = (value / 100.0) * total_time
        
        # Ensure we stay within bounds
        target_time = max(self.default_window, min(total_time, target_time))
        
        # Update view range while maintaining zoom level
        self.plot.getViewBox().setXRange(
            max(0, target_time - self.default_window),
            target_time,
            padding=0
        )