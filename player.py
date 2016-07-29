"""
Play a wav file or a raw audio buffer
The default parameter of this player is 1 channel, 16kHz, 16bit samples.
"""
import pyaudio
import wave
import io
import time
import threading
import Queue

CHUNK_SIZE = 4096

class Player():
    def __init__(self, pa):
        self.pa = pa
        self.stream = self.pa.open(format=pyaudio.paInt16,
                                   channels=1,
                                   rate=16000,
                                   output=True,
                                   start=False,
                                #    output_device_index=1,
                                   frames_per_buffer=CHUNK_SIZE,
                                   stream_callback=self.callback)
        self.buffer = b''
        self.lock = threading.RLock()

    def play(self, wav_file):
        self.wav = wave.open(wav_file, 'rb')
        n = self.wav.getnframes()
        with self.lock:
            self.buffer += self.wav.readframes(n)
        self.wav.close()
        if not self.stream.is_active():
            self.stream.stop_stream()
            self.stream.start_stream()

    def play_buffer(self, buffer):
        with self.lock:
            self.buffer += buffer
        if not self.stream.is_active():
            self.stream.stop_stream()
            self.stream.start_stream()

    def callback(self, in_data, frame_count, time_info, status):
        length = frame_count * 2 * 1
        with self.lock:
            data = self.buffer[:length]
            self.buffer = self.buffer[len(data):]
        return data, pyaudio.paContinue

    def close(self):
        self.stream.stop_stream()
        self.stream.close()
