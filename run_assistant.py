#!/usr/bin/env python3
"""
Local Assistant: Whisper + Llama-3.2-3B-Instruct + Kokoro TTS
A lightweight, universal Linux voice assistant.
"""

import os
import sys
import json
import time
import re
import datetime
import numpy as np
import sounddevice as sd
import soundfile as sf
import concurrent.futures

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from cli_animations import (
    listening, thinking, speaking, loading,
    print_banner, print_status, print_response_header, print_separator,
    print_instructions, WaitingForInput, Colors
)
from tools import get_all_tools, execute_tool
from model_downloader import ensure_llama_models_exist, get_llama_model_path

# Audio settings
SAMPLE_RATE = 16000
RECORD_DURATION = 5

# Kokoro TTS settings
KOKORO_VOICE = "af_heart"  # American female voice
KOKORO_LANG = "a"  # American English

# Get tools dynamically from registry
TOOLS = get_all_tools()


def record_audio(duration, sample_rate):
    """Record audio for a fixed duration."""
    with listening(duration):
        recording = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype='float32')
        sd.wait()
    print_status("Recording captured!", "success")
    return recording.flatten()


def play_audio(audio_data, sample_rate=24000):
    with speaking():
        sd.play(audio_data, sample_rate)
        sd.wait()
    print_status("Playback complete!", "audio")


def format_tools_for_prompt(tools: list) -> str:
    """Format tool definitions for the system prompt."""
    tool_strs = []
    for tool in tools:
        func = tool.get("function", {})
        name = func.get("name", "")
        desc = func.get("description", "")
        params = func.get("parameters", {}).get("properties", {})
        param_strs = []
        for pname, pinfo in params.items():
            ptype = pinfo.get("type", "string")
            pdesc = pinfo.get("description", "")
            param_strs.append(f"      - {pname} ({ptype}): {pdesc}")
        params_text = "\n".join(param_strs) if param_strs else "      (no parameters)"
        tool_strs.append(f"  - {name}: {desc}\n    Parameters:\n{params_text}")
    return "\n".join(tool_strs)


class SpeechAssistant:
    def __init__(self):
        self.whisper_model = None
        self.llm = None
        self.kokoro_pipeline = None
        self.conversation_history = []
        self.max_history = 2  # Only keep 1 previous turn to minimize hallucination
        self._last_tool_result = None
    
    def load_models(self):
        """Load all models in parallel for faster startup."""
        import whisper
        from llama_cpp import Llama
        
        def load_whisper():
            return whisper.load_model("base")
        
        def load_llama():
            model_path = get_llama_model_path()
            n_gpu_layers = 0
            try:
                import torch
                if torch.cuda.is_available():
                    n_gpu_layers = -1
                    print_status("CUDA detected, using GPU acceleration", "info")
            except ImportError:
                print_status("Running on CPU (install torch for GPU)", "info")
            
            return Llama(
                model_path=model_path,
                n_ctx=4096,
                n_gpu_layers=n_gpu_layers,
                verbose=False
            )
        
        def load_kokoro():
            try:
                from kokoro import KPipeline
                return KPipeline(lang_code=KOKORO_LANG, repo_id="hexgrad/Kokoro-82M")
            except Exception as e:
                print_status(f"Kokoro error: {e}", "warning")
                return None
        
        with loading("Loading models in parallel (Whisper + Llama + Kokoro)") as loader:
            loader.set_progress(10, "Starting parallel load...")
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                whisper_future = executor.submit(load_whisper)
                llama_future = executor.submit(load_llama)
                kokoro_future = executor.submit(load_kokoro)
                
                loader.set_progress(30, "Loading Whisper...")
                self.whisper_model = whisper_future.result()
                
                loader.set_progress(60, "Loading Llama-3.2-3B...")
                self.llm = llama_future.result()
                
                loader.set_progress(90, "Loading Kokoro TTS...")
                self.kokoro_pipeline = kokoro_future.result()
            
            loader.set_progress(100, "All models loaded!")
    
    def transcribe(self, audio_data):
        """Transcribe audio using Whisper."""
        audio_fp32 = audio_data.astype(np.float32)
        result = self.whisper_model.transcribe(audio_fp32, language="en")
        return result["text"].strip()
    
    def generate_response(self, user_text: str) -> str:
        """Generate a response using Llama-3.2-3B with tool calling."""
        current_time = datetime.datetime.now().strftime("%A, %B %d, %Y %I:%M %p")
        
        # Build system prompt with tools
        tools_text = format_tools_for_prompt(TOOLS)
        
        system_prompt = (
            "You are a locally running voice assistant. Be helpful, concise, and accurate.\n"
            "ABSOLUTE RULES:\n"
            "1. NEVER make up or guess ANY information (system stats, files, etc). If you dont know, call a tool.\n"
            "2. For ANY action or query about files/system/web, output ONLY the JSON tool call:\n"
            f"   Format: {{\"tool\": \"tool_name\", \"args\": {{}}}}\n"
            "3. Wrap spoken responses in <speak>...</speak> tags.\n"
            "4. FILE OPERATIONS:\n"
            "   - LIST files: {\"tool\": \"find_files\", \"args\": {\"pattern\": \"*.pdf\"}}\n"
            "   - OPEN file by number: {\"tool\": \"find_and_open_file\", \"args\": {\"pattern\": \"*.pdf\", \"which\": 4}}\n"
            "5. SYSTEM STATS: {\"tool\": \"get_system_stats\", \"args\": {}}\n\n"
            f"Time: {current_time} | OS: Linux (CachyOS)\n\n"
            f"TOOLS:\n{tools_text}"
        )

        # Build messages - only keep last turn to minimize hallucination
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add only the previous turn (if any)
        for msg in self.conversation_history[-2:]:
            messages.append(msg)
        
        messages.append({"role": "user", "content": user_text})
        
        # Generate response
        response = self.llm.create_chat_completion(
            messages=messages,
            max_tokens=256,
            temperature=0.3,
            stop=["<|eot_id|>", "<|end_of_text|>"]
        )
        
        response_text = response["choices"][0]["message"]["content"].strip()
        
        # DEBUG: Show raw LLM output to diagnose tool calling
        print(f"\n{Colors.YELLOW}[DEBUG] Raw LLM output: {response_text[:200]}...{Colors.RESET}")
        
        # Check if there's a tool call JSON anywhere in the response
        # This regex handles nested braces in the args object
        json_match = re.search(r'\{\s*"tool"\s*:\s*"[^"]+"\s*,\s*"args"\s*:\s*\{[^}]*\}\s*\}', response_text)
        
        if json_match:
            json_str = json_match.group(0)
            print(f"{Colors.GREEN}[DEBUG] Found tool JSON: {json_str}{Colors.RESET}")
            
            try:
                # Parse tool call
                tool_call = json.loads(json_str)
                tool_name = tool_call.get("tool", "")
                tool_args = tool_call.get("args", {})
                
                print_status(f"Calling tool: {tool_name}", "info")
                tool_result = execute_tool(tool_name, tool_args)
                self._last_tool_result = tool_result
                
                # Generate follow-up response with tool result
                messages.append({"role": "assistant", "content": json_str})
                messages.append({"role": "user", "content": f"Tool result: {tool_result}\n\nSummarize this briefly for voice output (1-2 sentences, no technical details). Wrap your spoken response in <speak>...</speak> tags."})
                
                follow_up = self.llm.create_chat_completion(
                    messages=messages,
                    max_tokens=128,
                    temperature=0.3,
                    stop=["<|eot_id|>", "<|end_of_text|>"]
                )
                response_text = follow_up["choices"][0]["message"]["content"].strip()
                
            except json.JSONDecodeError as e:
                print_status(f"JSON parse error: {e}", "warning")
                self._last_tool_result = None
        else:
            print(f"{Colors.YELLOW}[DEBUG] No tool call found in response{Colors.RESET}")
            self._last_tool_result = None
        
        # Update history
        self.conversation_history.append({"role": "user", "content": user_text})
        self.conversation_history.append({"role": "assistant", "content": response_text})
        
        # Trim history to only keep 1 previous turn
        if len(self.conversation_history) > self.max_history:
            self.conversation_history = self.conversation_history[-self.max_history:]
        
        return response_text
    
    
    def speak(self, text: str, output_path: str) -> bool:
        """Synthesize speech using Kokoro TTS."""
        if not self.kokoro_pipeline:
            print_status("TTS not available", "warning")
            return False
        
        try:
            # Generate audio using Kokoro
            audio_chunks = []
            for _, _, audio in self.kokoro_pipeline(text, voice=KOKORO_VOICE, speed=1.0):
                audio_chunks.append(audio)
            
            # Combine chunks and save
            full_audio = np.concatenate(audio_chunks) if len(audio_chunks) > 1 else audio_chunks[0]
            sf.write(output_path, full_audio, 24000)  # Kokoro outputs at 24kHz
            return True
        except Exception as e:
            print_status(f"TTS error: {e}", "warning")
            return False


def main():
    print_banner()
    
    # Ensure models are downloaded
    if not ensure_llama_models_exist():
        print_status("Model download failed. Please check errors and retry.", "error")
        return
    
    assistant = SpeechAssistant()
    assistant.load_models()
    
    print_status("All models loaded!", "success")
    print_status("Lightweight Llama-3.2-3B assistant ready.", "info")
    print_instructions(RECORD_DURATION)
    
    try:
        while True:
            wait_anim = WaitingForInput()
            wait_anim.start()
            try:
                input()
            finally:
                wait_anim.stop()
            
            audio = record_audio(RECORD_DURATION, SAMPLE_RATE)
            
            if len(audio) == 0:
                continue
            
            print_status("Transcribing...", "info")
            user_text = assistant.transcribe(audio)
            print(f"{Colors.BOLD}You said:{Colors.RESET} {user_text}")
            
            if not user_text.strip():
                print_status("No speech detected, try again.", "warning")
                continue
            
            print_response_header()
            with thinking():
                response = assistant.generate_response(user_text)
            
            # Display tool result if any
            if assistant._last_tool_result:
                print(f"{Colors.CYAN}{assistant._last_tool_result}{Colors.RESET}")
                print()
            
            # Display the response (clean up speak tags for display)
            display_response = response.replace('<speak>', '').replace('</speak>', '')
            print(f"{Colors.BOLD}Assistant:{Colors.RESET} {display_response}")
            
            # Extract speech content from <speak> tags, or use full response
            speak_match = re.search(r'<speak>(.*?)</speak>', response, re.DOTALL)
            speech_text = speak_match.group(1).strip() if speak_match else response
            
            # Speak
            output_path = os.path.join(SCRIPT_DIR, "response.wav")
            if assistant.speak(speech_text, output_path):
                audio_data, sr = sf.read(output_path)
                play_audio(audio_data.astype(np.float32), sr)
                os.remove(output_path)
            
            print_separator()
    
    except KeyboardInterrupt:
        print()
        print_status("Goodbye!", "info")


if __name__ == "__main__":
    main()
