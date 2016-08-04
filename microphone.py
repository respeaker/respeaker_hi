import pyaudio
import webrtcvad
import collections
import sys
import os
from pocketsphinx.pocketsphinx import *
import time
import Queue

FORMAT = pyaudio.paInt16
CHANNELS = 1
SAMPLE_RATE = 16000
CHUNK_MS = 30    # 10, 20 or 30 (ms)
CHUNK_SIZE = int(SAMPLE_RATE * CHUNK_MS / 1000) # 30 * 16 = 480
DEFAULT_PADDING_CHUNKS = 32
DEFAULT_PADDING_MS = DEFAULT_PADDING_CHUNKS * CHUNK_MS

script_dir = os.path.dirname(os.path.realpath(__file__))


class Microphone():
    def __init__(self, pa, level=3):
        self.queue = Queue.Queue()
        self.pa = pa
        self.stream = self.pa.open(format=FORMAT,
                                    channels=CHANNELS,
                                    rate=SAMPLE_RATE,
                                    input=True,
                                    start=False,
                                    # input_device_index=1,
                                    frames_per_buffer=CHUNK_SIZE,
                                    stream_callback=self.capture_callback)
        self.vad = webrtcvad.Vad(level)
        self.quit = False

        # Create a decoder with certain model
        config = Decoder.default_config()
        # config.set_string('-hmm', os.path.join(script_dir, 'en-US/acoustic-model'))
        config.set_string('-hmm', os.path.join(script_dir, 'model/hmm/en'))
        # config.set_string('-lm', os.path.join(script_dir, 'model/coco.lm'))
        config.set_string('-dict', os.path.join(script_dir, 'model/respeaker.dic'))
        config.set_string('-kws', os.path.join(script_dir, 'model/keywords.txt'))
        # config.set_string('-keyphrase', 'respeaker')
        # config.set_float('-kws_threshold', 1e-43)
        config.set_int('-samprate', SAMPLE_RATE) # on ubuntu 14.04, it must be changed to `set_float`
        # config.set_int('-nfft', 2048)
        config.set_string("-logfn", os.devnull)
        self.decoder = Decoder(config)
        self.decoder.start_utt()
        self.decoder_need_restart = False

    def capture_callback(self, data, frame_count, time_info, status):
        active = self.vad.is_speech(data, SAMPLE_RATE)
        sys.stdout.write('1' if active else '0')
        self.ring_buffer_flags[self.ring_buffer_index] = 1 if active else 0
        self.ring_buffer_index += 1
        self.ring_buffer_index %= self.padding_chunks
        if not self.triggered:
            self.ring_buffer.append(data)
            num_voiced = sum(self.ring_buffer_flags)
            if num_voiced >= 4:
                sys.stdout.write('+')
                self.triggered = True
                self.queue.put((b''.join(self.ring_buffer), False))
                self.duration = len(self.ring_buffer) * CHUNK_MS
                self.ring_buffer.clear()
        else:
            ending = False  # end of a phrase
            num_voiced = sum(self.ring_buffer_flags)
            self.duration += CHUNK_MS
            if num_voiced < 2 or self.duration >= self.max_duration:
                self.triggered = False
                ending = True
                sys.stdout.write('-')

            self.ring_buffer.append(data)
            self.queue.put((data, ending))

        sys.stdout.flush()
        return None, pyaudio.paContinue

    def listen(self, max_ms=9000):
        self.set_padding_time(DEFAULT_PADDING_MS)
        self.start(max_ms)
        frames = []
        while not self.quit:
            data, ending = self.queue.get()
            frames.append(data)
            if ending:
                break

        self.stop()
        return b''.join(frames)

    def detect(self, keyphrase='respeaker'):
        self.set_padding_time(900)
        self.start(3000)

        detected = False
        while not self.quit:
            if self.decoder_need_restart:
                self.decoder.end_utt()  # it takes about 1 second on respeaker
                self.decoder.start_utt()
                self.decoder_need_restart = False

            data, ending = self.queue.get()
            if not data:
                break

            self.decoder.process_raw(data, False, False)
            hypothesis = self.decoder.hyp()
            if hypothesis:
                if ending:
                    print('\nhypothesis: %s, score: %d' % (hypothesis.hypstr, hypothesis.best_score))
                    print('restart decoder next time')
                    self.decoder_need_restart = True

                if hypothesis.hypstr.find(keyphrase) >= 0:
                    print('\nhypothesis: %s, score: %d' % (hypothesis.hypstr, hypothesis.best_score))
                    print('\ndetected')
                    detected = True
                    self.decoder_need_restart = True
                    break

        self.stop()
        return detected

    def close(self):
        self.queue.put(('', True))
        self.quit = True

        self.stream.close()
        self.pa.terminate()

    def set_padding_time(self, ms=DEFAULT_PADDING_MS):
        chunks = int((ms + CHUNK_MS - 1) / CHUNK_MS)
        self.padding_chunks = chunks
        self.ring_buffer = collections.deque(maxlen=chunks)
        self.ring_buffer_flags = [0] * chunks
        self.ring_buffer_index = 0

    def start(self, max_ms):
        self.max_duration = max_ms
        self.duration = 0
        self.triggered = False
        with self.queue.mutex:
            self.queue.queue.clear()
        self.stream.start_stream()

    def stop(self):
        self.stream.stop_stream()
