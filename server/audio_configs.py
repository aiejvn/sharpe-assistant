import pyaudio

# CHUNK = 1024 # Number of audio samples per frame
CHUNK = 4096 # Number of audio samples per frame
                # Note: 4096 is the standard. Many functions assume this is 4096. Do not change unless absolutely necessary.
FORMAT= pyaudio.paInt16 # Audio format
CHANNELS = 1 # Mono audio
RATE = 44100 # Sampling rate (samples per second)
DTYPE = 'float32'