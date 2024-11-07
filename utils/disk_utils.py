import psutil

def get_disk_usage():
    try:
        root_usage = psutil.disk_usage('/')
        BYTES_TO_GB = 1000 * 1000 * 1000
        
        total_gb = root_usage.total / BYTES_TO_GB
        available_gb = root_usage.free / BYTES_TO_GB
        used_gb = total_gb - available_gb
        percent = (used_gb / total_gb) * 100
        
        return total_gb, used_gb, available_gb, percent
    except Exception as e:
        print(f"Error reading disk usage: {e}")
        return 0, 0, 0, 0