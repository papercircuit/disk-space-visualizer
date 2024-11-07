import time
import numpy as np
import matplotlib.pyplot as plt

class EventHandler:
    def __init__(self, monitor):
        self.monitor = monitor
        self.setup_event_handlers()
        
        self.last_mouse_pos = None
        self.last_update_time = 0
        self.throttle_delay = 1/30
        
        # Reference tracking
        self.reference_lines = []
        self.reference_labels = []
        self.reference_texts = []
        self.reference_data = []
        self.max_references = 5
    
    def setup_event_handlers(self):
        canvas = self.monitor.plot_manager.canvas
        canvas.mpl_connect('button_press_event', self.on_click)
        canvas.mpl_connect('draw_event', self.on_draw)
        canvas.mpl_connect('motion_notify_event', self.on_mouse_move)
        canvas.mpl_connect('axes_leave_event', self.on_mouse_leave)
    
    def on_click(self, event):
        if not event.inaxes == self.monitor.plot_manager.ax:
            return
        
        click_x = event.xdata
        click_y = event.ydata
        
        # Check if click is near any reference line
        for i, (ref_time, _, _) in enumerate(self.reference_data):
            if abs(click_x - ref_time) < 0.01:
                self.reference_lines[i].remove()
                self.reference_labels[i].remove()
                self.reference_data.pop(i)
                if i < len(self.reference_texts):
                    self.reference_texts[i].remove()
                    self.reference_texts.pop(i)
                
                self.reference_lines.pop(i)
                self.reference_labels.pop(i)
                
                self._update_reference_numbers()
                self.monitor.plot_manager.canvas.draw_idle()
                return

        if len(self.reference_lines) >= self.max_references:
            return
        
        if not (click_x <= max(self.monitor.times) and click_x >= 0):
            return

        times_array = np.array(self.monitor.times)
        idx = np.abs(times_array - click_x).argmin()
        x_val = times_array[idx]
        sys_val = list(self.monitor.usage)[idx]
        docker_val = list(self.monitor.docker_usage)[idx]

        color = plt.cm.Set3(len(self.reference_lines) / self.max_references)
        ref_line = self.monitor.plot_manager.ax.axvline(x=x_val, color=color, linestyle='--', alpha=0.7, linewidth=0.8)
        
        label = self.monitor.plot_manager.ax.text(x_val, -0.05, f'T{len(self.reference_lines)+1}', 
            rotation=45,
            horizontalalignment='right',
            verticalalignment='top',
            transform=self.monitor.plot_manager.ax.get_xaxis_transform(),
            color=color)
        
        self.reference_lines.append(ref_line)
        self.reference_labels.append(label)
        self.reference_data.append((x_val, sys_val, docker_val))

        for text in self.reference_texts:
            text.remove()
        self.reference_texts.clear()

        num_refs = len(self.reference_data)
        if num_refs > 0:
            total_width = 0.7
            start_pos = 0.15
            gap = total_width / (self.max_references - 1) if num_refs > 1 else total_width

            for i, (t, v, d) in enumerate(self.reference_data):
                color_i = plt.cm.Set3(i / self.max_references)
                x_pos = start_pos + (i * gap)
                
                text = self.monitor.plot_manager.fig.text(x_pos, 0.02,
                    f'T{i+1}:\n{t:.1f}m\nSys:{v:.1f}GB\nDoc:{d:.1f}GB',
                    color=color_i,
                    fontsize=5,
                    horizontalalignment='left',
                    verticalalignment='bottom',
                    transform=self.monitor.plot_manager.fig.transFigure)
                self.reference_texts.append(text)

        self.monitor.plot_manager.canvas.draw_idle()
    
    def _update_reference_numbers(self):
        for i, label in enumerate(self.reference_labels):
            label.set_text(f'T{i+1}')
            color = plt.cm.Set3(i / self.max_references)
            label.set_color(color)
            self.reference_lines[i].set_color(color)

        for text in self.reference_texts:
            text.remove()
        self.reference_texts.clear()

        num_refs = len(self.reference_data)
        if num_refs > 0:
            total_width = 0.7
            start_pos = 0.15
            gap = total_width / (self.max_references - 1) if num_refs > 1 else total_width

            for i, (t, v, d) in enumerate(self.reference_data):
                color_i = plt.cm.Set3(i / self.max_references)
                x_pos = start_pos + (i * gap)
                
                text = self.monitor.plot_manager.fig.text(x_pos, 0.02,
                    f'T{i+1}:\n{t:.1f}m\nSys:{v:.1f}GB\nDoc:{d:.1f}GB',
                    color=color_i,
                    fontsize=5,
                    horizontalalignment='left',
                    verticalalignment='bottom',
                    transform=self.monitor.plot_manager.fig.transFigure,
                    bbox=dict(
                        facecolor='white',
                        alpha=0.8,
                        pad=1,
                        edgecolor='none'
                    ))
                self.reference_texts.append(text)
    
    def on_draw(self, event):
        self.monitor.plot_manager.background = self.monitor.plot_manager.canvas.copy_from_bbox(
            self.monitor.plot_manager.fig.bbox)
    
    def on_mouse_move(self, event):
        if not event.inaxes == self.monitor.plot_manager.ax:
            self.monitor.plot_manager.cursor_line.set_alpha(0)
            self.monitor.plot_manager.tooltip_annotation.set_visible(False)
            self.monitor.plot_manager.canvas.draw_idle()
            return

        if not (event.xdata <= max(self.monitor.times) and event.xdata >= 0):
            self.monitor.plot_manager.cursor_line.set_alpha(0)
            self.monitor.plot_manager.tooltip_annotation.set_visible(False)
            self.monitor.plot_manager.canvas.draw_idle()
            return

        current_time = time.time()
        if current_time - self.last_update_time < self.throttle_delay:
            return
        self.last_update_time = current_time

        self.monitor.plot_manager.cursor_line.set_xdata([event.xdata, event.xdata])
        self.monitor.plot_manager.cursor_line.set_alpha(0.5)

        if len(self.monitor.times) > 0:
            times_array = np.array(self.monitor.times)
            idx = np.abs(times_array - event.xdata).argmin()
            x_val = times_array[idx]
            y_val = list(self.monitor.usage)[idx]

            self.monitor.plot_manager.tooltip_annotation.xy = (x_val, y_val)
            self.monitor.plot_manager.tooltip_annotation.set_text(f'Time: {x_val:.1f}m\nUsage: {y_val:.1f}GB')
            self.monitor.plot_manager.tooltip_annotation.set_visible(True)

        self.monitor.plot_manager.canvas.draw_idle()
    
    def on_mouse_leave(self, event):
        self.monitor.plot_manager.cursor_line.set_alpha(0)
        self.monitor.plot_manager.tooltip_annotation.set_visible(False)
        self.monitor.plot_manager.canvas.draw_idle()