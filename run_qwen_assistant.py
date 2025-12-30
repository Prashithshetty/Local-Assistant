
#!/usr/bin/env python3
"""
Modular Speech Assistant: Whisper + Qwen2.5-3B + XTTS-v2
"""

import os
import sys
import json
import time
import torch
import sounddevice as sd
import numpy as np
import tempfile
import datetime
import collections
import whisper
import soundfile as sf
import concurrent.futures
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from cli_animations import (
    listening, thinking, speaking, loading,
    print_banner, print_status, print_response_header, print_separator,
    print_instructions, WaitingForInput, Colors
)
from search_utils import perform_search

QWEN_MODEL = os.path.join(SCRIPT_DIR, "models", "qwen2.5-3b-instruct")
XTTS_MODEL = os.path.join(SCRIPT_DIR, "models", "XTTS-v2")
SAMPLE_RATE = 16000
RECORD_DURATION = 5

# INT4 Quantization config for Qwen - uses ~2GB VRAM instead of ~6GB
QUANTIZATION_CONFIG = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_quant_type="nf4"
)

TOOLS = [{
    "type": "function",
    "function": {
        "name": "web_search",
        "description": "Search the internet for current information like weather, news, sports, or stocks.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "timelimit": {
                    "type": "string",
                    "description": "Time limit for search results (d: day, w: week, m: month, y: year). Use 'd' or 'w' for recent news."
                }
            },
            "required": ["query"]
        }
    }
}]


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


def execute_tool(tool_name, tool_args):
    if tool_name == "web_search":
        query = tool_args.get("query", "")
        timelimit = tool_args.get("timelimit")
        print_status(f"Searching: {query} (Time: {timelimit or 'All'})", "info")
        results = perform_search(query, timelimit=timelimit)
        print_status("Search complete!", "success")
        return results
    return "Unknown tool"


PIPER_MODEL_PATH = os.path.join(SCRIPT_DIR, "models", "piper", "en_US-amy-medium.onnx")

class SpeechAssistant:
    def __init__(self):
        self.whisper_model = None
        self.qwen_model = None
        self.qwen_tokenizer = None
        self.piper_voice = None
        
    def load_models(self):
        """Load all models in parallel for faster startup."""
        
        def load_whisper():
            # Use GPU for Whisper with 'base' model (faster, ~1.5GB VRAM)
            device = "cuda" if torch.cuda.is_available() else "cpu"
            return whisper.load_model("base", device=device)
        
        def load_qwen():
            # INT4 quantized Qwen - fits in ~2GB VRAM
            tokenizer = AutoTokenizer.from_pretrained(QWEN_MODEL)
            model = AutoModelForCausalLM.from_pretrained(
                QWEN_MODEL, 
                torch_dtype=torch.float16,
                quantization_config=QUANTIZATION_CONFIG,
                device_map="cuda:0"
            )
            return tokenizer, model
        
        def load_piper():
            try:
                from piper import PiperVoice
                # Keep Piper on CPU to save VRAM
                return PiperVoice.load(PIPER_MODEL_PATH, config_path=PIPER_MODEL_PATH + ".json", use_cuda=False)
            except Exception as e:
                print_status(f"Piper error: {e}", "warning")
                return None
        
        with loading("Loading models in parallel (Whisper GPU + Qwen INT4 + Piper)") as loader:
            loader.set_progress(10, "Starting parallel load...")
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                whisper_future = executor.submit(load_whisper)
                qwen_future = executor.submit(load_qwen)
                piper_future = executor.submit(load_piper)
                
                loader.set_progress(30, "Loading Whisper...")
                self.whisper_model = whisper_future.result()
                
                loader.set_progress(60, "Loading Qwen (INT4)...")
                self.qwen_tokenizer, self.qwen_model = qwen_future.result()
                
                loader.set_progress(90, "Loading Piper...")
                self.piper_voice = piper_future.result()
            
            loader.set_progress(100, "All models loaded!")

    # ... (models loaded) ...

    def transcribe(self, audio_data):
        """Transcribe audio directly from numpy array (in-memory, no file I/O)."""
        # Whisper expects float32 audio
        audio_fp32 = audio_data.astype(np.float32)
        result = self.whisper_model.transcribe(audio_fp32, language="en")
        return result["text"].strip()
    
    def generate_response(self, user_text):
        current_time_str = datetime.datetime.now().strftime("%A, %B %d, %Y %I:%M %p")
        
        system_prompt = (
            "You are a friendly voice assistant. Your responses will be spoken aloud using text to speech, "
            "so write in a natural conversational tone. Never use asterisks, bullet points, numbered lists, "
            "markdown, or special symbols. Avoid abbreviations and write numbers as words when it sounds more natural. "
            "Keep your answers brief and to the point, like you are having a casual conversation. "
            f"The current date and time is {current_time_str}. User location is likely India based on timezone. "
            "When you need current information like weather, news, or sports scores, use the web search tool."
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text}
        ]
        
        text = self.qwen_tokenizer.apply_chat_template(messages, tools=TOOLS, add_generation_prompt=True, tokenize=False)
        inputs = self.qwen_tokenizer(text, return_tensors="pt").to(self.qwen_model.device)
        
        with torch.no_grad():
            outputs = self.qwen_model.generate(**inputs, max_new_tokens=256, temperature=0.7, do_sample=True, pad_token_id=self.qwen_tokenizer.pad_token_id)
        
        response = self.qwen_tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=False)
        
        if "<tool_call>" in response:
            try:
                tool_start = response.find("<tool_call>") + len("<tool_call>")
                tool_end = response.find("</tool_call>")
                tool_json = response[tool_start:tool_end].strip()
                tool_data = json.loads(tool_json)
                
                tool_name = tool_data.get("name", "")
                tool_args = tool_data.get("arguments", {})
                tool_result = execute_tool(tool_name, tool_args)
                
                messages.append({"role": "assistant", "content": response})
                messages.append({"role": "tool", "content": tool_result, "name": tool_name})
                
                text = self.qwen_tokenizer.apply_chat_template(messages, add_generation_prompt=True, tokenize=False)
                inputs = self.qwen_tokenizer(text, return_tensors="pt").to(self.qwen_model.device)
                
                with torch.no_grad():
                    outputs = self.qwen_model.generate(**inputs, max_new_tokens=256, temperature=0.7, do_sample=True, pad_token_id=self.qwen_tokenizer.pad_token_id)
                
                response = self.qwen_tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
            except Exception as e:
                print_status(f"Tool error: {e}", "warning")
                response = response.split("<tool_call>")[0].strip()
        else:
            response = response.replace("<|im_end|>", "").strip()
        
        return response

    def speak(self, text, output_path):
        # Use Piper TTS
        if self.piper_voice:
            try:
                # Synthesize returns iterator of AudioChunk objects
                audio_bytes = bytes()
                for audio_chunk in self.piper_voice.synthesize(text):
                    audio_bytes += audio_chunk.audio_int16_bytes  # Extract audio bytes from AudioChunk
                
                # Convert to numpy array (16-bit PCM)
                audio_array = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
                
                # Write WAV file
                sf.write(output_path, audio_array, self.piper_voice.config.sample_rate)
                return True
            except Exception as e:
                print_status(f"Piper error: {e}", "warning")
        
        print_status("TTS failed: Piper not available or errored.", "warning")
        return False


def main():
    print_banner()
    
    assistant = SpeechAssistant()
    assistant.load_models()
    
    print_status("All models loaded!", "success")
    print_status("Web search enabled for weather, news, stocks, etc.", "info")
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
            
            # In-memory transcription (no temp file I/O)
            print_status("Transcribing...", "info")
            user_text = assistant.transcribe(audio)
            print(f"{Colors.BOLD}You said:{Colors.RESET} {user_text}")
            
            print_response_header()
            with thinking():
                response = assistant.generate_response(user_text)
            print(f"{Colors.BOLD}Assistant:{Colors.RESET} {response}")
            
            output_path = os.path.join(SCRIPT_DIR, "response.wav")
            if assistant.speak(response, output_path):
                audio_data, sr = sf.read(output_path)
                play_audio(audio_data.astype(np.float32), sr)
                os.remove(output_path)
            
            # Temp file removal no longer needed (in-memory processing)
            print_separator()
    
    except KeyboardInterrupt:
        print()
        print_status("Goodbye!", "info")


if __name__ == "__main__":
    main()
