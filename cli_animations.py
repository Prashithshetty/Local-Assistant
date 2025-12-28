"""
CLI Animation Module for Speech-to-Speech AI
Pure ASCII/Unicode animations - no emojis.
"""

import sys
import time
import threading
import math
from itertools import cycle
from contextlib import contextmanager


class Colors:
    """ANSI color codes for terminal styling."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    ITALIC = "\033[3m"
    UNDERLINE = "\033[4m"
    BLINK = "\033[5m"
    REVERSE = "\033[7m"
    
    # Foreground colors
    BLACK = "\033[30m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    
    # 256 color support for gradients
    @staticmethod
    def fg(n):
        return f"\033[38;5;{n}m"
    
    @staticmethod
    def bg(n):
        return f"\033[48;5;{n}m"


class AnimatedState:
    """Base class for animated CLI states."""
    
    def __init__(self, message: str = "", color: str = Colors.WHITE):
        self.message = message
        self.color = color
        self._stop_event = threading.Event()
        self._thread = None
    
    def _clear_line(self):
        """Clear the current line."""
        sys.stdout.write('\r\033[K')
        sys.stdout.flush()
    
    def _hide_cursor(self):
        sys.stdout.write('\033[?25l')
        sys.stdout.flush()
    
    def _show_cursor(self):
        sys.stdout.write('\033[?25h')
        sys.stdout.flush()
    
    def _animate(self):
        """Animation loop - override in subclasses."""
        raise NotImplementedError
    
    def start(self):
        """Start the animation in a separate thread."""
        self._stop_event.clear()
        self._hide_cursor()
        self._thread = threading.Thread(target=self._animate, daemon=True)
        self._thread.start()
    
    def stop(self):
        """Stop the animation."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=1)
        self._clear_line()
        self._show_cursor()


class ListeningAnimation(AnimatedState):
    """Animated audio waveform for recording state."""
    
    def __init__(self, duration: int = 5):
        super().__init__("LISTENING", Colors.CYAN)
        self.duration = duration
        self.width = 40
        
    def _animate(self):
        start_time = time.time()
        phase = 0
        
        # Block characters for waveform
        blocks = " ▁▂▃▄▅▆▇█"
        
        while not self._stop_event.is_set():
            elapsed = time.time() - start_time
            remaining = max(0, self.duration - elapsed)
            
            # Generate dynamic waveform
            wave = []
            for i in range(self.width):
                # Multiple sine waves for organic look
                val = (
                    math.sin((i * 0.3) + phase) * 0.4 +
                    math.sin((i * 0.5) + phase * 1.3) * 0.3 +
                    math.sin((i * 0.7) + phase * 0.7) * 0.3
                )
                # Normalize to 0-8 range
                idx = int((val + 1) * 4)
                idx = max(0, min(8, idx))
                wave.append(blocks[idx])
            
            waveform = "".join(wave)
            
            # Progress bar
            progress = min(1.0, elapsed / self.duration)
            prog_width = 10
            filled = int(prog_width * progress)
            prog_bar = f"[{'=' * filled}{' ' * (prog_width - filled)}]"
            
            output = (
                f"\r{Colors.CYAN}{Colors.BOLD}>> {self.message} "
                f"{Colors.RESET}{Colors.CYAN}{waveform} "
                f"{Colors.DIM}{remaining:.1f}s {prog_bar}{Colors.RESET}"
            )
            
            sys.stdout.write(output)
            sys.stdout.flush()
            
            phase += 0.15
            time.sleep(0.05)


class ThinkingAnimation(AnimatedState):
    """Neural network-style thinking animation."""
    
    def __init__(self, message: str = "PROCESSING"):
        super().__init__(message, Colors.MAGENTA)
        self.width = 30
        
    def _animate(self):
        # Neural pattern characters
        patterns = [".", "o", "O", "0", "@", "#"]
        phase = 0
        
        while not self._stop_event.is_set():
            # Create flowing neural pattern
            neural = []
            for i in range(self.width):
                val = math.sin((i * 0.4) + phase) + math.sin((i * 0.2) + phase * 1.5)
                idx = int((val + 2) * len(patterns) / 4)
                idx = max(0, min(len(patterns) - 1, idx))
                neural.append(patterns[idx])
            
            pattern = "".join(neural)
            
            # Spinner
            spinners = ["/-\\|", "    "][0]
            spinner = spinners[int(phase * 2) % len(spinners)]
            
            # Dots animation
            dots = "." * (int(phase) % 4)
            
            output = (
                f"\r{Colors.MAGENTA}{Colors.BOLD}[{spinner}] {self.message}{dots:<3} "
                f"{Colors.RESET}{Colors.MAGENTA}{Colors.DIM}{pattern}{Colors.RESET}"
            )
            
            sys.stdout.write(output)
            sys.stdout.flush()
            
            phase += 0.2
            time.sleep(0.08)


class GeneratingAnimation(AnimatedState):
    """Text generation animation with typing effect indicator."""
    
    def __init__(self, message: str = "GENERATING"):
        super().__init__(message, Colors.GREEN)
        self.width = 25
        
    def _animate(self):
        phase = 0
        
        # Matrix-style characters
        chars = "01"
        
        while not self._stop_event.is_set():
            # Generate matrix rain effect
            matrix = []
            for i in range(self.width):
                intensity = math.sin((i * 0.5) + phase) + 1
                if intensity > 1.5:
                    matrix.append(chars[int(phase * 3 + i) % 2])
                elif intensity > 0.8:
                    matrix.append(Colors.DIM + chars[int(phase * 2 + i) % 2] + Colors.RESET + Colors.GREEN)
                else:
                    matrix.append(" ")
            
            stream = "".join(matrix)
            
            # Cursor blink
            cursor = "_" if int(phase * 3) % 2 == 0 else " "
            
            output = (
                f"\r{Colors.GREEN}{Colors.BOLD}>> {self.message} "
                f"{Colors.RESET}{Colors.GREEN}[{stream}]{cursor}{Colors.RESET}"
            )
            
            sys.stdout.write(output)
            sys.stdout.flush()
            
            phase += 0.15
            time.sleep(0.06)


class SpeakingAnimation(AnimatedState):
    """Audio output waveform animation."""
    
    def __init__(self):
        super().__init__("SPEAKING", Colors.YELLOW)
        self.width = 35
        
    def _animate(self):
        phase = 0
        blocks = " ▁▂▃▄▅▆▇█"
        
        while not self._stop_event.is_set():
            # Generate audio visualization
            wave = []
            for i in range(self.width):
                # More aggressive waveform for speaking
                val = (
                    math.sin((i * 0.4) + phase * 2) * 0.5 +
                    math.cos((i * 0.6) + phase * 1.5) * 0.3 +
                    math.sin((i * 0.2) + phase * 3) * 0.2
                )
                idx = int((val + 1) * 4)
                idx = max(0, min(8, idx))
                wave.append(blocks[idx])
            
            waveform = "".join(wave)
            
            # Volume indicator
            vol_phase = (math.sin(phase * 2) + 1) / 2
            vol_bars = int(vol_phase * 5)
            volume = "|" * vol_bars + " " * (5 - vol_bars)
            
            output = (
                f"\r{Colors.YELLOW}{Colors.BOLD}<< {self.message} "
                f"{Colors.RESET}{Colors.YELLOW}{waveform} "
                f"{Colors.DIM}[{volume}]{Colors.RESET}"
            )
            
            sys.stdout.write(output)
            sys.stdout.flush()
            
            phase += 0.12
            time.sleep(0.04)


class LoadingAnimation(AnimatedState):
    """Smooth progress bar with status updates."""
    
    def __init__(self, message: str = "LOADING"):
        super().__init__(message, Colors.BLUE)
        self._progress = 0
        self._status = ""
        self.width = 40
        
    def set_progress(self, progress: int, status: str = ""):
        """Update progress (0-100) and status message."""
        self._progress = min(100, max(0, progress))
        self._status = status
    
    def _animate(self):
        # Spinner characters
        spinners = [
            "    ",
            ".   ",
            "..  ",
            "... ",
            " ...",
            "  ..",
            "   .",
        ]
        
        phase = 0
        
        while not self._stop_event.is_set():
            spinner = spinners[int(phase) % len(spinners)]
            
            # Smooth progress bar with gradient effect
            filled = int(self.width * self._progress / 100)
            
            # Create gradient bar
            bar_chars = []
            for i in range(self.width):
                if i < filled:
                    bar_chars.append("=")
                elif i == filled and self._progress < 100:
                    bar_chars.append(">")
                else:
                    bar_chars.append("-")
            
            bar = "".join(bar_chars)
            
            status_text = f" {self._status}" if self._status else ""
            
            output = (
                f"\r{Colors.BLUE}{Colors.BOLD}[{spinner}] {self.message} "
                f"{Colors.RESET}{Colors.BLUE}[{bar}] "
                f"{Colors.BOLD}{self._progress:3d}%{Colors.DIM}{status_text}{Colors.RESET}"
            )
            
            sys.stdout.write(output)
            sys.stdout.flush()
            
            phase += 0.3
            time.sleep(0.1)


class WaitingForInput(AnimatedState):
    """Pulsing ready indicator."""
    
    def __init__(self):
        super().__init__("READY", Colors.GREEN)
        
    def _animate(self):
        phase = 0
        
        # Pulsing arrow states
        arrows = [
            "  > ",
            " >> ",
            ">>> ",
            ">>>>",
            ">>> ",
            " >> ",
            "  > ",
            "    ",
        ]
        
        while not self._stop_event.is_set():
            arrow = arrows[int(phase) % len(arrows)]
            
            # Pulsing brightness
            if int(phase) % 8 < 4:
                style = Colors.BOLD
            else:
                style = ""
            
            output = (
                f"\r{Colors.GREEN}{style}{arrow} "
                f"Press ENTER to speak {arrow[::-1]}{Colors.RESET}"
            )
            
            sys.stdout.write(output)
            sys.stdout.flush()
            
            phase += 1
            time.sleep(0.15)


class PulseAnimation(AnimatedState):
    """Simple pulsing dot animation for any state."""
    
    def __init__(self, message: str, color: str = Colors.WHITE):
        super().__init__(message, color)
        
    def _animate(self):
        pulse_frames = [
            "(   )",
            "(.  )",
            "(.. )",
            "(...)",
            "( ..)",
            "(  .)",
            "(   )",
        ]
        frame_idx = 0
        
        while not self._stop_event.is_set():
            frame = pulse_frames[frame_idx % len(pulse_frames)]
            
            output = (
                f"\r{self.color}{Colors.BOLD}{frame} {self.message}{Colors.RESET}"
            )
            
            sys.stdout.write(output)
            sys.stdout.flush()
            
            frame_idx += 1
            time.sleep(0.12)


# Context managers for easy use
@contextmanager
def listening(duration: int = 5):
    """Context manager for listening animation."""
    anim = ListeningAnimation(duration)
    anim.start()
    try:
        yield anim
    finally:
        anim.stop()


@contextmanager  
def thinking(message: str = "PROCESSING"):
    """Context manager for thinking animation."""
    anim = ThinkingAnimation(message)
    anim.start()
    try:
        yield anim
    finally:
        anim.stop()


@contextmanager
def generating(message: str = "GENERATING"):
    """Context manager for generating animation."""
    anim = GeneratingAnimation(message)
    anim.start()
    try:
        yield anim
    finally:
        anim.stop()


@contextmanager
def speaking():
    """Context manager for speaking animation."""
    anim = SpeakingAnimation()
    anim.start()
    try:
        yield anim
    finally:
        anim.stop()


@contextmanager
def loading(message: str = "LOADING"):
    """Context manager for loading animation."""
    anim = LoadingAnimation(message)
    anim.start()
    try:
        yield anim
    finally:
        anim.stop()


def print_banner():
    """Print a stylish ASCII startup banner."""
    banner = f"""
{Colors.CYAN}{Colors.BOLD}
    ╔═══════════════════════════════════════════════════════════════╗
    ║                                                               ║
    ║   ██╗     ███████╗███╗   ███╗     ██████╗     █████╗ ██╗      ║
    ║   ██║     ██╔════╝████╗ ████║    ╚════██╗    ██╔══██╗██║      ║
    ║   ██║     █████╗  ██╔████╔██║     █████╔╝    ███████║██║      ║
    ║   ██║     ██╔══╝  ██║╚██╔╝██║    ██╔═══╝     ██╔══██║██║      ║
    ║   ███████╗██║     ██║ ╚═╝ ██║    ███████╗    ██║  ██║██║      ║
    ║   ╚══════╝╚═╝     ╚═╝     ╚═╝    ╚══════╝    ╚═╝  ╚═╝╚═╝      ║
    ║                                                               ║
    ║           {Colors.WHITE}S P E E C H  -  T O  -  S P E E C H{Colors.CYAN}               ║
    ║                                                               ║
    ╚═══════════════════════════════════════════════════════════════╝
{Colors.RESET}"""
    print(banner)


def print_status(message: str, status: str = "info"):
    """Print a styled status message."""
    icons = {
        "info": f"{Colors.BLUE}[i]{Colors.RESET}",
        "success": f"{Colors.GREEN}[+]{Colors.RESET}",
        "warning": f"{Colors.YELLOW}[!]{Colors.RESET}",
        "error": f"{Colors.RED}[x]{Colors.RESET}",
        "audio": f"{Colors.CYAN}[~]{Colors.RESET}",
    }
    icon = icons.get(status, icons["info"])
    print(f" {icon} {message}")


def print_response_header():
    """Print header for AI response."""
    print(f"\n{Colors.MAGENTA}{Colors.BOLD}>> ASSISTANT:{Colors.RESET} ", end="", flush=True)


def print_separator():
    """Print a visual separator."""
    print(f"\n{Colors.DIM}{'─' * 65}{Colors.RESET}\n")


def print_instructions(record_duration: int = 5):
    """Print usage instructions."""
    print(f"""
{Colors.CYAN}{Colors.BOLD}INSTRUCTIONS{Colors.RESET}
{Colors.DIM}{'─' * 40}{Colors.RESET}
  {Colors.WHITE}>{Colors.RESET} Press {Colors.BOLD}ENTER{Colors.RESET} to record ({record_duration}s)
  {Colors.WHITE}>{Colors.RESET} Speak clearly into microphone
  {Colors.WHITE}>{Colors.RESET} AI responds with voice + text
  {Colors.WHITE}>{Colors.RESET} Press {Colors.BOLD}CTRL+C{Colors.RESET} to exit
{Colors.DIM}{'─' * 40}{Colors.RESET}
""")


# Demo function to test animations
if __name__ == "__main__":
    print_banner()
    
    print_status("Testing animations...", "info")
    time.sleep(1)
    
    # Test loading animation
    print()
    with loading("LOADING MODEL") as loader:
        for i in range(0, 101, 5):
            loader.set_progress(i, f"Step {i//10}/10")
            time.sleep(0.15)
    print_status("Loading complete!", "success")
    
    # Test listening animation
    print()
    with listening(3):
        time.sleep(3)
    print_status("Recording captured!", "success")
    
    # Test thinking animation
    print()
    with thinking("PROCESSING AUDIO"):
        time.sleep(2.5)
    print_status("Processing complete!", "success")
    
    # Test generating animation
    print()
    with generating("GENERATING RESPONSE"):
        time.sleep(2)
    print_response_header()
    print("Hello! This is a test response from the AI.")
    
    # Test speaking animation
    print()
    with speaking():
        time.sleep(2.5)
    print_status("Playback complete!", "audio")
    
    print_separator()
    print_status("All animations tested!", "success")
