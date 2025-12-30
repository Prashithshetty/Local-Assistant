"""
System monitoring tools - CPU, RAM, disk, GPU, battery, processes.
"""

import os
import logging
import platform
import subprocess
from functools import lru_cache
from typing import Optional
from .tool_registry import register_tool

logger = logging.getLogger("tools.system")

try:
    import psutil
except ImportError:
    psutil = None
    logger.warning("psutil not installed - system monitoring limited")

try:
    import GPUtil
except ImportError:
    GPUtil = None


def _get_amd_gpu_info() -> Optional[str]:
    """Get AMD GPU info via rocm-smi if available."""
    try:
        result = subprocess.run(
            ['rocm-smi', '--showuse', '--showmeminfo', 'vram', '--showtemp'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return result.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def get_system_stats() -> str:
    """Get overall system stats (CPU, RAM, Disk)."""
    if not psutil:
        return "System monitoring unavailable. Install psutil: pip install psutil"
    
    try:
        cpu_percent = psutil.cpu_percent(interval=0.5)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        result = f"System Stats:\n"
        result += f"CPU Usage: {cpu_percent}%\n"
        result += f"RAM: {memory.percent}% used ({memory.used // (1024**3)}GB of {memory.total // (1024**3)}GB)\n"
        result += f"Disk: {disk.percent}% used ({disk.used // (1024**3)}GB of {disk.total // (1024**3)}GB free: {disk.free // (1024**3)}GB)"
        
        # Add GPU if available (NVIDIA first, then AMD)
        if GPUtil:
            try:
                gpus = GPUtil.getGPUs()
                if gpus:
                    gpu = gpus[0]
                    result += f"\nGPU: {gpu.name} - {gpu.memoryUtil*100:.0f}% VRAM used"
            except Exception as e:
                logger.debug(f"GPUtil failed: {e}")
        
        # Try AMD GPU if no NVIDIA detected
        if "GPU:" not in result:
            amd_info = _get_amd_gpu_info()
            if amd_info and "GPU" in amd_info:
                result += "\nAMD GPU detected (use get_gpu_info for details)"
        
        return result
        
    except Exception as e:
        logger.error(f"get_system_stats failed: {e}")
        return f"Could not get system stats: {e}"


def get_cpu_info() -> str:
    """Get CPU information."""
    if not psutil:
        return "CPU monitoring unavailable. Install psutil: pip install psutil"
    
    try:
        cpu_count = psutil.cpu_count(logical=True)
        cpu_count_physical = psutil.cpu_count(logical=False)
        cpu_freq = psutil.cpu_freq()
        cpu_percent = psutil.cpu_percent(interval=0.5, percpu=True)
        
        result = f"CPU Information:\n"
        result += f"Cores: {cpu_count_physical} physical, {cpu_count} logical\n"
        if cpu_freq:
            result += f"Frequency: {cpu_freq.current:.0f}MHz (max: {cpu_freq.max:.0f}MHz)\n"
        
        # Show all cores but summarize if too many
        if len(cpu_percent) <= 8:
            result += f"Usage per core: {', '.join(f'{p}%' for p in cpu_percent)}"
        else:
            avg = sum(cpu_percent) / len(cpu_percent)
            result += f"Average usage: {avg:.1f}% (across {len(cpu_percent)} cores)"
        
        return result
        
    except Exception as e:
        logger.error(f"get_cpu_info failed: {e}")
        return f"Could not get CPU info: {e}"


def get_memory_info() -> str:
    """Get RAM usage details."""
    if not psutil:
        return "Memory monitoring unavailable. Install psutil: pip install psutil"
    
    try:
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        result = f"Memory Information:\n"
        result += f"RAM Total: {mem.total // (1024**3)}GB\n"
        result += f"RAM Used: {mem.used // (1024**3)}GB ({mem.percent}%)\n"
        result += f"RAM Available: {mem.available // (1024**3)}GB\n"
        result += f"Swap Used: {swap.used // (1024**3)}GB of {swap.total // (1024**3)}GB"
        
        return result
        
    except Exception as e:
        logger.error(f"get_memory_info failed: {e}")
        return f"Could not get memory info: {e}"


def get_disk_usage(path: str = "/") -> str:
    """Get disk usage for a given path."""
    if not psutil:
        return "Disk monitoring unavailable. Install psutil: pip install psutil"
    
    # Expand user path if needed
    target_path = os.path.expanduser(path)
    
    try:
        disk = psutil.disk_usage(target_path)
        result = f"Disk Usage for {path}:\n"
        result += f"Total: {disk.total // (1024**3)}GB\n"
        result += f"Used: {disk.used // (1024**3)}GB ({disk.percent}%)\n"
        result += f"Free: {disk.free // (1024**3)}GB"
        return result
    except FileNotFoundError:
        return f"Path not found: {path}"
    except PermissionError:
        return f"Permission denied: {path}"
    except Exception as e:
        logger.error(f"get_disk_usage failed for {path}: {e}")
        return f"Could not get disk usage for {path}: {e}"


def get_gpu_info() -> str:
    """Get GPU information (NVIDIA and AMD)."""
    result_parts = []
    
    # Try NVIDIA via GPUtil
    if GPUtil:
        try:
            gpus = GPUtil.getGPUs()
            if gpus:
                result_parts.append("NVIDIA GPU Information:")
                for i, gpu in enumerate(gpus):
                    result_parts.append(f"GPU {i}: {gpu.name}")
                    result_parts.append(f"  VRAM: {gpu.memoryUsed:.0f}MB / {gpu.memoryTotal:.0f}MB ({gpu.memoryUtil*100:.0f}%)")
                    result_parts.append(f"  GPU Load: {gpu.load*100:.0f}%")
                    if gpu.temperature:
                        result_parts.append(f"  Temperature: {gpu.temperature}°C")
        except Exception as e:
            logger.debug(f"GPUtil query failed: {e}")
    
    # Try AMD via rocm-smi
    amd_info = _get_amd_gpu_info()
    if amd_info:
        result_parts.append("\nAMD GPU Information:")
        # Parse rocm-smi output (simplified)
        for line in amd_info.split('\n'):
            line = line.strip()
            if line and not line.startswith('='):
                result_parts.append(f"  {line}")
    
    if not result_parts:
        # Fallback: check if any GPU exists via lspci
        try:
            lspci = subprocess.run(['lspci'], capture_output=True, text=True, timeout=5)
            if 'VGA' in lspci.stdout or '3D' in lspci.stdout:
                for line in lspci.stdout.split('\n'):
                    if 'VGA' in line or '3D' in line:
                        return f"GPU detected but no driver tools available:\n{line.strip()}\nInstall GPUtil (NVIDIA) or ROCm (AMD) for detailed info."
        except Exception:
            pass
        return "No GPU detected or GPU tools not installed. Install GPUtil for NVIDIA or ROCm for AMD."
    
    return '\n'.join(result_parts)


def get_battery_status() -> str:
    """Get battery status."""
    if not psutil:
        return "Battery monitoring unavailable. Install psutil: pip install psutil"
    
    try:
        battery = psutil.sensors_battery()
        if not battery:
            return "No battery detected. This appears to be a desktop system."
        
        status = "Charging" if battery.power_plugged else "On Battery"
        
        # Handle time remaining calculation safely
        if battery.secsleft == psutil.POWER_TIME_UNKNOWN:
            time_left = "Calculating..."
        elif battery.secsleft == psutil.POWER_TIME_UNLIMITED:
            time_left = "Unlimited (plugged in)"
        elif battery.secsleft < 0:
            time_left = "Unknown"
        else:
            hours = battery.secsleft // 3600
            minutes = (battery.secsleft % 3600) // 60
            time_left = f"{hours}h {minutes}m"
        
        return f"Battery: {battery.percent}% - {status}. Time remaining: {time_left}"
        
    except Exception as e:
        logger.error(f"get_battery_status failed: {e}")
        return f"Could not get battery status: {e}"


def list_processes(sort_by: str = "cpu", limit: int = 5) -> str:
    """List top processes by CPU or memory usage."""
    if not psutil:
        return "Process monitoring unavailable. Install psutil: pip install psutil"
    
    # Validate and sanitize inputs
    sort_by = sort_by.lower() if sort_by else "cpu"
    if sort_by not in ("cpu", "memory"):
        sort_by = "cpu"
    
    limit = max(1, min(limit or 5, 20))  # Clamp between 1 and 20
    
    try:
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                pinfo = proc.info
                processes.append(pinfo)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        
        # Sort by requested metric
        key = 'cpu_percent' if sort_by == 'cpu' else 'memory_percent'
        processes.sort(key=lambda x: x.get(key, 0) or 0, reverse=True)
        
        result = f"Top {limit} processes by {sort_by.upper()}:\n"
        for i, proc in enumerate(processes[:limit]):
            name = proc.get('name', 'Unknown')[:20]  # Truncate long names
            cpu = proc.get('cpu_percent', 0) or 0
            mem = proc.get('memory_percent', 0) or 0
            result += f"{i+1}. {name} - CPU: {cpu:.1f}%, RAM: {mem:.1f}%\n"
        
        return result.strip()
        
    except Exception as e:
        logger.error(f"list_processes failed: {e}")
        return f"Could not list processes: {e}"


# ============================================================
# Register all system tools
# ============================================================

register_tool(
    name="get_system_stats",
    description="Get overall system status including CPU, RAM, disk, and GPU usage. Good for 'how is my system doing' type questions.",
    parameters={"type": "object", "properties": {}, "required": []},
    func=get_system_stats
)

register_tool(
    name="get_cpu_info",
    description="Get CPU information including cores, frequency, and per-core usage.",
    parameters={"type": "object", "properties": {}, "required": []},
    func=get_cpu_info
)

register_tool(
    name="get_memory_info",
    description="Get RAM and swap memory usage details.",
    parameters={"type": "object", "properties": {}, "required": []},
    func=get_memory_info
)

register_tool(
    name="get_disk_usage",
    description="Get disk space usage for a given path. Defaults to root partition.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to check disk usage for (default: /)"}
        },
        "required": []
    },
    func=get_disk_usage
)

register_tool(
    name="get_gpu_info",
    description="Get GPU information including VRAM usage, load, and temperature. Supports both NVIDIA and AMD GPUs.",
    parameters={"type": "object", "properties": {}, "required": []},
    func=get_gpu_info
)

register_tool(
    name="get_battery_status",
    description="Get battery level and charging status. Works on laptops only.",
    parameters={"type": "object", "properties": {}, "required": []},
    func=get_battery_status
)

register_tool(
    name="list_processes",
    description="List top processes by CPU or memory usage.",
    parameters={
        "type": "object",
        "properties": {
            "sort_by": {"type": "string", "enum": ["cpu", "memory"], "description": "Sort by 'cpu' or 'memory' (default: cpu)"},
            "limit": {"type": "integer", "description": "Number of processes to show (default: 5, max: 20)"}
        },
        "required": []
    },
    func=list_processes
)

