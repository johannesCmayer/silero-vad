#!/usr/bin/env python

from pathlib import Path
import sys

import typer
from rich import print

import torch
torch.set_num_threads(1)

app = typer.Typer()

SAMPLING_RATE = 16000 # also accepts 8000
DEFAULT_THRESHOLD = 0.5

def print_progress(progress: float):
    print(f"Progress: {progress:.2f}%", end='\r', file=sys.stderr)

@app.command()
def stats(file: Path, threshold: float = DEFAULT_THRESHOLD):
    """
    Calculate statistics about the speech in a media file.

    Calculate the percentage of speech in a media file.
    """
    model, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad',
                                model='silero_vad',
                                force_reload=False)

    (_ , _, read_audio, *_) = utils

    print(f"Reading file: {file}", file=sys.stderr)
    wav = read_audio(file, sampling_rate=SAMPLING_RATE)

    print(f"Calculating Speech Probabilities.", file=sys.stderr)
    speech_probs = []
    window_size_samples = 512 # use 256 for 8000 Hz model
    for i in tqdm(range(0, len(wav), window_size_samples), file=sys.stderr):
        chunk = wav[i: i+window_size_samples]
        if len(chunk) < window_size_samples:
            break
        speech_prob = model(chunk, SAMPLING_RATE).item()
        speech_probs.append((i / SAMPLING_RATE, speech_prob))
    model.reset_states() # reset model states after each audio

    cur = 0
    for seconds, prob in speech_probs:
        if seconds > cur:
            print(f"{seconds:.2f}\t{prob:.2f}", file=sys.stderr)
            cur += 1

    wav.duration = len(wav) / SAMPLING_RATE
    non_speech_duration = sum([window_size_samples / SAMPLING_RATE for seconds, prob in speech_probs if prob < threshold])
    non_speech_duration_percent = non_speech_duration / wav.duration * 100
    print(f"Non Speech Duration: {non_speech_duration:.2f}s, {non_speech_duration_percent}%", file=sys.stderr)

def timestamps(
        file: Path, threshold: float = DEFAULT_THRESHOLD, min_speech_duration_ms: int = 250, 
        max_speech_duration_s: float = float('inf'), min_silence_duration_ms: int = 100, 
        window_size_samples: int = 512, speech_pad_ms: int = 30, calculate_stats: bool = False):
    """
    Get the timestamps of for the speech in a media file. 
    
    Pint to stdout in the format: x1s,y1s x2s,y2s x3s,y3s ...
    where x is the start of the speech and y is the end of the speech.
    Each timestamp is postfix by the literal 's' whith indicates that it is in seconds.
    The output is easily parsed by the auto-editor programs.

    file: Path
        Path to the file to be processed

    threshold: float (default - 0.5)
        Speech threshold. Silero VAD outputs speech probabilities for each audio chunk, probabilities ABOVE this value are considered as SPEECH.
        It is better to tune this parameter for each dataset separately, but "lazy" 0.5 is pretty good for most datasets.

    min_speech_duration_ms: int (default - 250 milliseconds)
        Final speech chunks shorter min_speech_duration_ms are thrown out

    max_speech_duration_s: int (default -  inf)
        Maximum duration of speech chunks in seconds
        Chunks longer than max_speech_duration_s will be split at the timestamp of the last silence that lasts more than 100ms (if any), to prevent agressive cutting.
        Otherwise, they will be split aggressively just before max_speech_duration_s.

    min_silence_duration_ms: int (default - 100 milliseconds)
        In the end of each speech chunk wait for min_silence_duration_ms before separating it

    window_size_samples: int (default - 1536 samples)
        Audio chunks of window_size_samples size are fed to the silero VAD model.
        WARNING! Silero VAD models were trained using 512, 1024, 1536 samples for 16000 sample rate and 256, 512, 768 samples for 8000 sample rate.
        Values other than these may affect model perfomance!!

    speech_pad_ms: int (default - 30 milliseconds)
        Final speech chunks are padded by speech_pad_ms each side
    """

    model, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad',
                                model='silero_vad',
                                force_reload=False)

    (get_speech_timestamps, _, read_audio, *_) = utils

    print(f"Reading file: {file}", file=sys.stderr)
    wav = read_audio(file, sampling_rate=SAMPLING_RATE)

    print(f"Calculating Speech Timestamps.", file=sys.stderr)
    speech_timestamps = get_speech_timestamps(
            audio=wav, 
            model=model, 
            threshold=threshold, 
            sampling_rate=SAMPLING_RATE, 
            min_speech_duration_ms=min_speech_duration_ms, 
            max_speech_duration_s=max_speech_duration_s, 
            min_silence_duration_ms=min_silence_duration_ms, 
            window_size_samples=window_size_samples, 
            speech_pad_ms=speech_pad_ms, 
            progress_tracking_callback=print_progress,
            return_seconds=True,
            visualize_probs=False)

    return speech_timestamps

@app.command()
def voice_timestamps(
        file: Path, threshold: float = DEFAULT_THRESHOLD, min_speech_duration_ms: int = 250, 
        max_speech_duration_s: float = float('inf'), min_silence_duration_ms: int = 100, 
        window_size_samples: int = 512, speech_pad_ms: int = 30, calculate_stats: bool = False):
    
    speech_timestamps = timestamps(file, threshold, min_speech_duration_ms, max_speech_duration_s, min_silence_duration_ms,
               window_size_samples, speech_pad_ms, calculate_stats)

    for segment in speech_timestamps:
        start = segment['start']
        end = segment['end']
        print(f"{start}s,{end}s", end=' ')

@app.command()
def auto_editor_smart_set_speed_for_range(
        file: Path, threshold: float = DEFAULT_THRESHOLD, min_speech_duration_ms: int = 250, 
        max_speech_duration_s: float = float('inf'), min_silence_duration_ms: int = 100, 
        window_size_samples: int = 512, speech_pad_ms: int = 30, calculate_stats: bool = False):
    """
    The output of this command can be fed to auto editor with --set-speed-for-range.

    It calculates speeds such that there can't be more than 1s of no-speech. For shorter
    non-speech regions we first have an exponential function, and then a constant function,
    until we hit the limit where we need to shorten the audio to not have more than 1s of no-speech.
    """
    
    speech_timestamps = timestamps(file, threshold, min_speech_duration_ms, max_speech_duration_s, min_silence_duration_ms,
               window_size_samples, speech_pad_ms, calculate_stats)

    for i, segment in enumerate(speech_timestamps):
        start = segment['start']
        end = segment['end']
        speed = 1
        if i > 0:
            silent_region_end = start
            silent_region_start = speech_timestamps[i-1]['end']
            region_length = silent_region_end - silent_region_start
            speed = min(1 + region_length + region_length**2, max(6, region_length))
            print(f"{speed},{silent_region_start}s,{silent_region_end}s", end=' ')

def main():
    app()

if __name__ == '__main__':
    main()
