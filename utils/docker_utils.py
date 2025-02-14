import subprocess
import asyncio
from concurrent.futures import ThreadPoolExecutor

_executor = ThreadPoolExecutor(max_workers=1)

def get_docker_container_name():
    try:
        cmd = "docker ps --format '{{.Names}}' | grep -i prokit_database"
        container_name = subprocess.check_output(cmd, shell=True, text=True).strip()
        return container_name
    except Exception as e:
        print(f"Error finding Docker container: {e}")
        return None

async def get_docker_usage_async():
    try:
        # Run Docker operations in a separate thread
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_executor, get_docker_usage)
    except Exception as e:
        print(f"Error in async Docker usage check: {e}")
        return None, None

def get_docker_usage():
    try:
        container_name = get_docker_container_name()
        if not container_name:
            return None, None

        cmd = f"docker exec {container_name} df -k / | tail -1"
        result = subprocess.check_output(cmd, shell=True, text=True).strip()
        
        parts = result.split()
        if len(parts) >= 4:
            total_kb = float(parts[1])
            used_kb = float(parts[2])
            
            KB_TO_GB = 1000 * 1000
            total_gb = total_kb / KB_TO_GB
            used_gb = used_kb / KB_TO_GB
            
            return total_gb, used_gb
            
        return None, None
    except Exception as e:
        print(f"Error reading Docker disk usage: {e}")
        return None, None