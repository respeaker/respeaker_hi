
import pyaudio
import wave
import time
import threading

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


    def play(self, wav_file, block=True):
        self.wav = wave.open(wav_file, 'rb')
        # self.stream = self.pa.open(format=self.pa.get_format_from_width(self.wav.getsampwidth()),
        #                                channels=self.wav.getnchannels(),
        #                                rate=self.wav.getframerate(),
        #                                output=True,
        #                             #    output_device_index=1,
        #                                frames_per_buffer=CHUNK_SIZE,
        #                                stream_callback=self.callback)
        self.event = threading.Event()
        self.stream.start_stream()
        if block:
            self.event.wait()
            self.stream.stop_stream()

    def callback(self, in_data, frame_count, time_info, status):
        data = self.wav.readframes(frame_count)
        if self.wav.getnframes() == self.wav.tell():
            data = data.ljust(frame_count * self.wav.getsampwidth() * self.wav.getnchannels(), '\x00')
            self.event.set()

        return data, pyaudio.paContinue
