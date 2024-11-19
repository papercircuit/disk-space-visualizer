import psutil
import subprocess

def get_disk_usage(path='/'):
    try:
        root_usage = psutil.disk_usage(path)
        BYTES_TO_GB = 1000 * 1000 * 1000
        
        total_gb = root_usage.total / BYTES_TO_GB
        available_gb = root_usage.free / BYTES_TO_GB
        used_gb = total_gb - available_gb
        percent = (used_gb / total_gb) * 100
        
        return total_gb, used_gb, available_gb, percent
    except Exception as e:
        print(f"Error reading disk usage for {path}: {e}")
        return 0, 0, 0, 0

def get_available_drives():
    """Get list of available disk partitions with friendly names"""
    try:
        partitions = psutil.disk_partitions()
        drives = []
        
        # Get volume info using diskutil
        try:
            result = subprocess.run(['diskutil', 'list', '-plist'], capture_output=True, text=True)
            
            # Use diskutil info for each device to get volume name
            for p in partitions:
                if not p.device.startswith('/dev/disk'):
                    continue
                    
                try:
                    vol_info = subprocess.run(['diskutil', 'info', p.device], capture_output=True, text=True)
                    vol_output = vol_info.stdout
                    
                    # Extract volume name from diskutil output
                    volume_name = None
                    for line in vol_output.split('\n'):
                        if 'Volume Name:' in line:
                            volume_name = line.split('Volume Name:')[-1].strip()
                            break
                    
                    if volume_name and volume_name != "None":
                        # Add with friendly name
                        drives.append((p.mountpoint, f"{volume_name} ({p.device})"))
                    else:
                        # Fallback to mount point name if no volume name
                        name = p.mountpoint.split('/')[-1]
                        if not name:
                            name = "Root"
                        drives.append((p.mountpoint, f"{name} ({p.device})"))
                        
                except Exception as e:
                    print(f"Error getting volume info for {p.device}: {e}")
                    continue
                    
        except Exception as e:
            print(f"Error running diskutil: {e}")
            # Fallback to basic names
            for p in partitions:
                if p.device.startswith('/dev/disk'):
                    name = p.mountpoint.split('/')[-1]
                    if not name:
                        name = "Root"
                    drives.append((p.mountpoint, f"{name} ({p.device})"))
        
        return drives if drives else [('/', 'Macintosh HD (/dev/disk1s1)')]
        
    except Exception as e:
        print(f"Error getting drives: {e}")
        return [('/', 'Macintosh HD (/dev/disk1s1)')]