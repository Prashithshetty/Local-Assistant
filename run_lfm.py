import torch
import sounddevice as sd
import numpy as np
from liquid_audio import LFM2AudioModel, LFM2AudioProcessor, ChatState, LFMModality
import os
import json
from pathlib import Path

# Import CLI animations
from cli_animations import (
    listening, thinking, speaking, loading,
    print_banner, print_status, print_response_header, print_separator,
    print_instructions, WaitingForInput, Colors
)

# Parameters
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_ID = os.path.join(SCRIPT_DIR, "models", "LFM2-Audio-1.5B")

# --- Monkeypatch liquid_audio to support local paths ---
import liquid_audio.model.lfm2_audio
import liquid_audio.utils
import liquid_audio.processor

original_get_model_dir = liquid_audio.utils.get_model_dir

def patched_get_model_dir(repo_id, revision=None):
    if os.path.exists(repo_id):
        return Path(repo_id)
    return original_get_model_dir(repo_id, revision)

liquid_audio.model.lfm2_audio.get_model_dir = patched_get_model_dir
liquid_audio.utils.get_model_dir = patched_get_model_dir
liquid_audio.processor.get_model_dir = patched_get_model_dir
# -------------------------------------------------------

SAMPLE_RATE = 16000
CHANNELS = 1
RECORD_DURATION = 5

def load_model_with_offloading(model_path: str, max_gpu_memory_gb: float = 5.0):
    """
    Load model with GPU/CPU offloading using accelerate.
    Loads as much as possible on GPU, rest on CPU.
    """
    from accelerate import load_checkpoint_and_dispatch, infer_auto_device_map
    from accelerate.utils import get_balanced_memory
    from liquid_audio.model.lfm2_audio import (
        LFM2AudioModel, LFM2AudioConfig, Lfm2Config, 
        ConformerEncoderConfig, DepthformerConfig, module_exists
    )
    
    cache_path = Path(model_path)
    
    with (cache_path / "config.json").open() as f:
        config = json.load(f)
    
    conf = LFM2AudioConfig(
        lfm=Lfm2Config(**config.pop("lfm")),
        encoder=ConformerEncoderConfig(**config.pop("encoder")),
        depthformer=DepthformerConfig(**config.pop("depthformer")),
        **config,
    )
    
    # Create model on CPU first with bfloat16 for reduced memory
    model = LFM2AudioModel(conf).to(dtype=torch.bfloat16)
    
    # Set attention implementation
    if module_exists("flash_attn"):
        model.lfm.set_attn_implementation("flash_attention_2")
    else:
        model.lfm.set_attn_implementation("sdpa")
    
    # Load weights from checkpoint
    from accelerate import load_checkpoint_in_model
    load_checkpoint_in_model(model, cache_path)
    
    # Infer device map to spread across GPU and CPU
    max_memory = {
        0: f"{max_gpu_memory_gb}GB",  # GPU 0
        "cpu": "24GB"  # CPU RAM
    }
    
    device_map = infer_auto_device_map(
        model,
        max_memory=max_memory,
        no_split_module_classes=["LlamaDecoderLayer", "ConformerBlock"],  # Don't split these
    )
    
    print(f"Device map: {device_map}")
    
    # Dispatch model across devices
    from accelerate import dispatch_model
    model = dispatch_model(model, device_map=device_map)
    
    return model

def record_audio(duration, sample_rate):
    """Records audio from the microphone with animated feedback."""
    with listening(duration):
        recording = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=CHANNELS, dtype='float32')
        sd.wait()
    print_status("Recording captured!", "success")
    return recording.flatten()

def play_audio(audio_data, sample_rate):
    """Plays audio data with animated feedback."""
    with speaking():
        sd.play(audio_data, sample_rate)
        sd.wait()
    print_status("Playback complete!", "audio")

def main():
    print_banner()
    print_status(f"Model path: {MODEL_ID}", "info")
    
    if not os.path.exists(MODEL_ID):
        print_status(f"Model directory not found at {MODEL_ID}", "error")
        return

    try:
        with loading("Loading LFM-2 Audio Model") as loader:
            loader.set_progress(10, "Initializing...")
            # Load model with offloading - reserve some GPU memory for other operations
            model = load_model_with_offloading(MODEL_ID, max_gpu_memory_gb=4.5)
            loader.set_progress(70, "Loading processor...")
            # Processor on GPU for fast audio processing
            processor = LFM2AudioProcessor.from_pretrained(MODEL_ID, device="cuda")
            loader.set_progress(100, "Complete!")
    except Exception as e:
        print_status(f"Error loading with offloading: {e}", "warning")
        import traceback
        traceback.print_exc()
        
        # Fallback to pure CPU
        print_status("Falling back to CPU-only mode...", "warning")
        with loading("Loading Model (CPU)") as loader:
            loader.set_progress(20, "Loading model...")
            model = LFM2AudioModel.from_pretrained(MODEL_ID, device="cpu")
            loader.set_progress(60, "Loading processor...")
            processor = LFM2AudioProcessor.from_pretrained(MODEL_ID, device="cpu")
            loader.set_progress(100, "Complete!")

    mimi = processor.mimi
    
    print_status("Model loaded successfully!", "success")
    print_instructions(RECORD_DURATION)

    # Persistent chat state
    chat = ChatState(processor, codebooks=model.codebooks)
    
    # System prompt
    chat.new_turn("system")
    chat.add_text("Respond with interleaved text and audio.")
    chat.end_turn()

    try:
        while True:
            # Animated waiting prompt
            wait_anim = WaitingForInput()
            wait_anim.start()
            try:
                input()
            finally:
                wait_anim.stop()
            
            input_audio = record_audio(RECORD_DURATION, SAMPLE_RATE)
            audio_tensor = torch.from_numpy(input_audio).unsqueeze(0).float()
            
            chat.new_turn("user")
            chat.add_audio(audio_tensor, SAMPLE_RATE)
            chat.end_turn()
            
            chat.new_turn("assistant")
            
            print_status("Processing your input...", "info")
            
            out_text = []
            out_audio = []
            out_modality = []
            audio_chunks = []
            
            with torch.no_grad(), mimi.streaming(1):
                print_response_header()
                for t in model.generate_interleaved(
                    **chat,
                    max_new_tokens=1024,
                    audio_temperature=1.0,
                    audio_top_k=4,
                ):
                    if t.numel() == 1:
                        out_text.append(t)
                        out_modality.append(LFMModality.TEXT)
                        print(processor.text.decode(t), end="", flush=True)
                    elif t.numel() == 8:
                        if (t == 2048).any():
                            continue
                        out_audio.append(t)
                        out_modality.append(LFMModality.AUDIO_OUT)
                        wav_chunk = mimi.decode(t[None, :, None])[0]
                        audio_chunks.append(wav_chunk)
            
            # Print response header before text output
            print_response_header()
            
            print()
            
            if out_text and out_audio:
                chat.append(
                    text=torch.stack(out_text, 1),
                    audio_out=torch.stack(out_audio, 1),
                    modality_flag=torch.tensor(out_modality, device=processor.device),
                )
            
            chat.end_turn()
            
            print()  # Newline after response text
            
            if audio_chunks:
                full_audio = torch.cat(audio_chunks, dim=-1)
                output_audio = (full_audio.cpu().numpy() * 32767).astype(np.int16)
                play_audio(output_audio.flatten(), 24000)
            else:
                print_status("No audio generated.", "warning")
            
            print_separator()

    except KeyboardInterrupt:
        print()
        print_status("Goodbye!", "info")
    except Exception as e:
        print_status(f"An error occurred: {e}", "error")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
