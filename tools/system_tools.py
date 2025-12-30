"""
System monitoring tools - CPU, RAM, disk, GPU, battery, processes.
"""

import os
import platform
from .tool_registry import register_tool

try:
    import psutil
except ImportError:
    psutil = None

try:
    import GPUtil
except ImportError:
    GPUtil = None


def get_system_stats() -> str:
    """Get overall system stats (CPU, RAM, Disk)."""
    if not psutil:
        return "psutil not installed. Run: pip install psutil"
    
    cpu_percent = psutil.cpu_percent(interval=0.5)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    result = f"System Stats:\n"
    result += f"CPU Usage: {cpu_percent}%\n"
    result += f"RAM: {memory.percent}% used ({memory.used // (1024**3)}GB of {memory.total // (1024**3)}GB)\n"
    result += f"Disk: {disk.percent}% used ({disk.used // (1024**3)}GB of {disk.total // (1024**3)}GB free: {disk.free // (1024**3)}GB)"
    
    # Add GPU if available
    if GPUtil:
        try:
            gpus = GPUtil.getGPUs()
            if gpus:
                gpu = gpus[0]
                result += f"\nGPU: {gpu.name} - {gpu.memoryUtil*100:.0f}% VRAM used"
        except:
            pass
    
    return result


def get_cpu_info() -> str:
    """Get CPU information."""
    if not psutil:
        return "psutil not installed. Run: pip install psutil"
    
    cpu_count = psutil.cpu_count(logical=True)
    cpu_count_physical = psutil.cpu_count(logical=False)
    cpu_freq = psutil.cpu_freq()
    cpu_percent = psutil.cpu_percent(interval=0.5, percpu=True)
    
    result = f"CPU Information:\n"
    result += f"Cores: {cpu_count_physical} physical, {cpu_count} logical\n"
    if cpu_freq:
        result += f"Frequency: {cpu_freq.current:.0f}MHz (max: {cpu_freq.max:.0f}MHz)\n"
    result += f"Usage per core: {', '.join(f'{p}%' for p in cpu_percent[:4])}..."
    
    return result


def get_memory_info() -> str:
    """Get RAM usage details."""
    if not psutil:
        return "psutil not installed. Run: pip install psutil"
    
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    
    result = f"Memory Information:\n"
    result += f"RAM Total: {mem.total // (1024**3)}GB\n"
    result += f"RAM Used: {mem.used // (1024**3)}GB ({mem.percent}%)\n"
    result += f"RAM Available: {mem.available // (1024**3)}GB\n"
    result += f"Swap Used: {swap.used // (1024**3)}GB of {swap.total // (1024**3)}GB"
    
    return result


def get_disk_usage(path: str = "/") -> str:
    """Get disk usage for a given path."""
    if not psutil:
        return "psutil not installed. Run: pip install psutil"
    
    try:
        disk = psutil.disk_usage(path)
        result = f"Disk Usage for {path}:\n"
        result += f"Total: {disk.total // (1024**3)}GB\n"
        result += f"Used: {disk.used // (1024**3)}GB ({disk.percent}%)\n"
        result += f"Free: {disk.free // (1024**3)}GB"
        return result
    except Exception as e:
        return f"Could not get disk usage for {path}: {e}"


def get_gpu_info() -> str:
    """Get GPU information (NVIDIA only)."""
    if not GPUtil:
        return "GPUtil not installed. Run: pip install GPUtil"
    
    try:
        gpus = GPUtil.getGPUs()
        if not gpus:
            return "No NVIDIA GPU detected."
        
        result = "GPU Information:\n"
        for i, gpu in enumerate(gpus):
            result += f"GPU {i}: {gpu.name}\n"
            result += f"  VRAM: {gpu.memoryUsed:.0f}MB / {gpu.memoryTotal:.0f}MB ({gpu.memoryUtil*100:.0f}%)\n"
            result += f"  GPU Load: {gpu.load*100:.0f}%\n"
            result += f"  Temperature: {gpu.temperature}°C"
        return result
    except Exception as e:
        return f"Could not get GPU info: {e}"


def get_battery_status() -> str:
    """Get battery status."""
    if not psutil:
        return "psutil not installed. Run: pip install psutil"
    
    battery = psutil.sensors_battery()
    if not battery:
        return "No battery detected (desktop system)."
    
    status = "Charging" if battery.power_plugged else "On Battery"
    time_left = "Calculating..." if battery.secsleft == psutil.POWER_TIME_UNKNOWN else f"{battery.secsleft // 3600}h {(battery.secsleft % 3600) // 60}m"
    
    return f"Battery: {battery.percent}% - {status}. Time remaining: {time_left}"


def list_processes(sort_by: str = "cpu", limit: int = 5) -> str:
    """List top processes by CPU or memory usage."""
    if not psutil:
        return "psutil not installed. Run: pip install psutil"
    
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
        try:
            pinfo = proc.info
            processes.append(pinfo)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    
    # Sort by requested metric
    key = 'cpu_percent' if sort_by == 'cpu' else 'memory_percent'
    processes.sort(key=lambda x: x.get(key, 0) or 0, reverse=True)
    
    result = f"Top {limit} processes by {sort_by.upper()}:\n"
    for i, proc in enumerate(processes[:limit]):
        result += f"{i+1}. {proc['name']} - CPU: {proc['cpu_percent']:.1f}%, RAM: {proc['memory_percent']:.1f}%\n"
    
    return result.strip()


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
    description="Get NVIDIA GPU information including VRAM usage, load, and temperature.",
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
            "limit": {"type": "integer", "description": "Number of processes to show (default: 5)"}
        },
        "required": []
    },
    func=list_processes
)
