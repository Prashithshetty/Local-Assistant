
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
from tools import get_all_tools, execute_tool
from model_downloader import ensure_models_exist

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


# Tool execution is now handled by tools/tool_registry.py


PIPER_MODEL_PATH = os.path.join(SCRIPT_DIR, "models", "piper", "en_US-amy-medium.onnx")

class SpeechAssistant:
    def __init__(self):
        self.whisper_model = None
        self.qwen_model = None
        self.qwen_tokenizer = None
        self.piper_voice = None
        # Conversation memory - keeps last N messages for context
        self.conversation_history = []
        self.max_history = 10  # 5 turns (user + assistant pairs)
        self.compressed_summary = None  # Stores compressed history summary
        
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
            "You are a locally running voice assistant. Your goal is to be helpful, concise, humanlike and accurate, dont use symbols like *, # or anyother.\n"
            "CRITICAL PROTOCOLS:\n"
            "1. **TOOL USAGE**: To perform ANY action (SEARCHing, OPENing files, checking stats), you MUST generate a <tool_call> block. Do not just describe what you will do.\n"
            "2. **VOICE OUTPUT**: You are speaking to the user. Wrap ALL spoken text in <speak>...</speak> tags. Keep spoken text BRIEF (1-2 sentences). Do not read out long lists or technical IDs.\n"
            "3. **FILE OPERATIONS**: If the user asks to 'open' a file they just found, use `find_and_open_file` with the appropriate index or pattern.\n"
            "4. **CONTEXT**: \n"
            f"   - Time: {current_time_str}\n"
            "   - Location: India\n"
            "   - User OS: Linux (CachyOS/Arch)\n"
            "AVAILABLE TOOLS: find_and_open_file, find_files, get_system_stats, open_application, web_search."
        )
        
        # Build messages with history for context
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add compressed summary if it exists
        if self.compressed_summary:
            messages.append(self.compressed_summary)
        
        messages.extend(self.conversation_history)  # Add past conversation
        messages.append({"role": "user", "content": user_text})
        
        text = self.qwen_tokenizer.apply_chat_template(messages, tools=TOOLS, add_generation_prompt=True, tokenize=False)
        inputs = self.qwen_tokenizer(text, return_tensors="pt").to(self.qwen_model.device)
        
        with torch.no_grad():
            outputs = self.qwen_model.generate(**inputs, max_new_tokens=256, temperature=0.3, do_sample=True, pad_token_id=self.qwen_tokenizer.pad_token_id)
        
        response = self.qwen_tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=False)
        
        if "<tool_call>" in response:
            try:
                tool_start = response.find("<tool_call>") + len("<tool_call>")
                tool_end = response.find("</tool_call>")
                tool_json = response[tool_start:tool_end].strip()
                tool_data = json.loads(tool_json)
                
                tool_name = tool_data.get("name", "")
                tool_args = tool_data.get("arguments", {})
                print_status(f"Calling tool: {tool_name}", "info")
                tool_result = execute_tool(tool_name, tool_args)
                
                messages.append({"role": "assistant", "content": response})
                messages.append({"role": "tool", "content": tool_result, "name": tool_name})
                
                text = self.qwen_tokenizer.apply_chat_template(messages, add_generation_prompt=True, tokenize=False)
                inputs = self.qwen_tokenizer(text, return_tensors="pt").to(self.qwen_model.device)
                
                with torch.no_grad():
                    outputs = self.qwen_model.generate(**inputs, max_new_tokens=256, temperature=0.3, do_sample=True, pad_token_id=self.qwen_tokenizer.pad_token_id)
                
                response = self.qwen_tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
                
                # Store tool result to display later
                self._last_tool_result = tool_result
            except Exception as e:
                print_status(f"Tool error: {e}", "warning")
                response = response.split("<tool_call>")[0].strip()
                self._last_tool_result = None
        else:
            response = response.replace("<|im_end|>", "").strip()
            self._last_tool_result = None
        
        # Update conversation history
        self.conversation_history.append({"role": "user", "content": user_text})
        self.conversation_history.append({"role": "assistant", "content": response})
        
        # Compress history if too long (keep 4 recent turns + compressed summary)
        if len(self.conversation_history) > self.max_history:
            self._compress_history()
        
        return response
    
    def _compress_history(self):
        """Compress old conversation history into a summary."""
        print(f"\n{Colors.YELLOW}[COMPRESSION] History exceeds limit ({len(self.conversation_history)} messages). Compressing...{Colors.RESET}")
        
        # Compress ALL messages, keep NONE
        # This creates a complete reset: only summary remains
        messages_to_compress = self.conversation_history
        recent_messages = []  # Keep nothing, summary becomes the only context
        
        if not messages_to_compress:
            print(f"{Colors.YELLOW}[COMPRESSION] No messages to compress, skipping.{Colors.RESET}\n")
            return
        
        print(f"{Colors.YELLOW}[COMPRESSION] Compressing ALL {len(messages_to_compress)} messages into summary...{Colors.RESET}")
        
        # Build a summary prompt - use strict extraction to prevent hallucination
        history_text = "\n".join([
            f"{msg['role'].upper()}: {msg['content']}" 
            for msg in messages_to_compress
        ])
        
        # If there's already a compressed summary, include it in the compression
        if self.compressed_summary:
            history_text = f"{self.compressed_summary['content']}\n\n{history_text}"
        
        summary_prompt = (
            "STRICT INSTRUCTION: Extract and list ONLY the factual information from this conversation. "
            "Do NOT add any information that wasn't explicitly stated. "
            "Do NOT make assumptions or creative interpretations. "
            "Format: List each user question and assistant answer briefly.\n\n"
            "CONVERSATION TO SUMMARIZE:\n"
            f"{history_text}\n\n"
            "FACTUAL SUMMARY (bullet points only):"
        )
        
        # Use Qwen to generate summary with VERY low temperature to avoid creativity
        inputs = self.qwen_tokenizer(summary_prompt, return_tensors="pt").to(self.qwen_model.device)
        
        with torch.no_grad():
            outputs = self.qwen_model.generate(
                **inputs, 
                max_new_tokens=128, 
                temperature=0.1,  # Very low temperature = more factual, less creative
                do_sample=True, 
                pad_token_id=self.qwen_tokenizer.pad_token_id
            )
        
        summary = self.qwen_tokenizer.decode(
            outputs[0][inputs["input_ids"].shape[1]:], 
            skip_special_tokens=True
        ).strip()
        
        print(f"{Colors.GREEN}[COMPRESSION] Summary generated:{Colors.RESET}")
        print(f"{Colors.CYAN}{summary}{Colors.RESET}")
        print(f"{Colors.GREEN}[COMPRESSION] History compressed! All messages replaced with summary. Ready for 4 new turns.{Colors.RESET}\n")
        
        # Replace ALL messages with summary
        self.compressed_summary = {"role": "system", "content": f"Previous conversation summary: {summary}"}
        self.conversation_history = recent_messages  # Empty list

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
    
    # Auto-download models if they don't exist
    if not ensure_models_exist():
        print_status("Model download incomplete. Please check errors and try again.", "warning")
        return
    
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
            
            # Display tool result (file list, etc.) if any
            if hasattr(assistant, '_last_tool_result') and assistant._last_tool_result:
                print(f"{Colors.CYAN}{assistant._last_tool_result}{Colors.RESET}")
                print()
            
            # Display the response (clean up speak tags for display)
            display_response = response.replace('<speak>', '').replace('</speak>', '')
            print(f"{Colors.BOLD}Assistant:{Colors.RESET} {display_response}")
            
            # Extract speech content from <speak> tags, or use full response
            import re
            speak_match = re.search(r'<speak>(.*?)</speak>', response, re.DOTALL)
            speech_text = speak_match.group(1).strip() if speak_match else response
            
            output_path = os.path.join(SCRIPT_DIR, "response.wav")
            if assistant.speak(speech_text, output_path):
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
