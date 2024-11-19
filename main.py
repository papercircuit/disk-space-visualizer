import sys
from disk_monitor import DiskMonitor

if __name__ == "__main__":
    if "--hot-reload" in sys.argv:
        from hot_reload import start_hot_reload
        start_hot_reload()
    else:
        monitor = DiskMonitor()
        monitor.run()