import subprocess
import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
import sys
import os

_executor = ThreadPoolExecutor(max_workers=1)

def _convert_size_to_gb(size_str):
    """Convert Docker size string (like '10.5GB' or '150MB') to GB float."""
    try:
        if not size_str or size_str == '0B':
            return 0.0
            
        # Handle Docker's size format which might include parentheses
        size_str = size_str.split('(')[0].strip()
            
        units = {'B': 1, 'KB': 1024, 'MB': 1024**2, 'GB': 1024**3, 'TB': 1024**4}
        
        # Extract number and unit more reliably
        number = ''
        unit = ''
        for char in size_str:
            if char.isdigit() or char == '.':
                number += char
            elif char.isalpha():
                unit += char
        
        if not number or not unit:
            return 0.0
            
        number = float(number)
        unit = unit.upper()
        
        # Handle both KB and kB format
        if unit.startswith('K'):
            unit = 'KB'
        elif unit.startswith('M'):
            unit = 'MB'
        elif unit.startswith('G'):
            unit = 'GB'
        elif unit.startswith('T'):
            unit = 'TB'
        
        if unit not in units:
            print(f"Unknown unit in size string: {size_str}")
            return 0.0
            
        return number * units[unit] / units['GB']
    except Exception as e:
        print(f"Error converting size {size_str}: {e}")
        return 0.0

async def get_docker_usage_async():
    """Get Docker disk usage asynchronously."""
    try:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_executor, get_docker_usage)
    except Exception as e:
        print(f"Error in async Docker usage check: {e}")
        return 0.0, 0.0

def get_docker_usage():
    """Get total and used Docker disk space in GB."""
    try:
        # Check if Docker is running
        try:
            subprocess.run(["docker", "info"], capture_output=True, check=True)
        except subprocess.CalledProcessError:
            return 0.0, 0.0

        # On macOS, Docker runs in a VM with a fixed disk size
        if sys.platform == "darwin":
            try:
                # Get disk usage from Docker Desktop's VM
                result = subprocess.run(
                    ["docker", "run", "--rm", "alpine", "df", "-B1", "/"],
                    capture_output=True, text=True, check=True
                )
                
                lines = result.stdout.strip().split('\n')
                if len(lines) >= 2:
                    parts = lines[1].split()
                    if len(parts) >= 4:
                        # parts[1] is total, parts[3] is available in bytes
                        total_bytes = float(parts[1])
                        avail_bytes = float(parts[3])
                        total_gb = total_bytes / (1024 * 1024 * 1024)
                        avail_gb = avail_bytes / (1024 * 1024 * 1024)
                        return total_gb, total_gb - avail_gb
            except subprocess.CalledProcessError:
                pass
                
        # Fallback for non-macOS or if VM check fails
        result = subprocess.run(
            ["docker", "system", "df", "--format", "{{json .}}"],
            capture_output=True, text=True
        )
        
        if result.returncode == 0:
            total_size = 0.0
            used_size = 0.0
            
            for line in result.stdout.strip().split('\n'):
                try:
                    data = json.loads(line)
                    if data.get('Type') != 'Build Cache':
                        size = _convert_size_to_gb(data.get('Size', '0B'))
                        reclaimable = _convert_size_to_gb(data.get('Reclaimable', '0B').split()[0])
                        total_size += size
                        used_size += size - reclaimable
                except json.JSONDecodeError:
                    continue
                    
            return total_size, used_size
            
        return 0.0, 0.0
        
    except Exception:
        return 0.0, 0.0