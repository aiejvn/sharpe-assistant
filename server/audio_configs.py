import pyaudio

CHUNK = 1024 # Number of audio samples per frame
FORMAT= pyaudio.paInt16 # Audio format
CHANNELS = 1 # Mono audio
RATE = 44100 # Sampling rate (samples per second)
DTYPE = 'float32'