import pyaudio
import webrtcvad
import collections
import sys
import os
from pocketsphinx.pocketsphinx import *
import time
import Queue

# import timeit

# def wrapper(func, *args, **kwargs):
#     def wrapped():
#         return func(*args, **kwargs)
#     return wrapped

FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
FRAME_DURATION_MS = 30  # 30 ms
PADDING_DURATION_MS = 300
FRAME_SIZE = int(RATE * FRAME_DURATION_MS / 1000) # 30 * 16 = 480
PADDING_FRAMES = int(PADDING_DURATION_MS / FRAME_DURATION_MS)
KEY_FRAMES = 10

script_dir = os.path.dirname(os.path.realpath(__file__))


class Microphone():
    def __init__(self, pa, level=3):
        self.queue = Queue.Queue()
        self.pa = pa
        self.stream = self.pa.open(format=FORMAT,
                                    channels=CHANNELS,
                                    rate=RATE,
                                    input=True,
                                    start=False,
                                    # input_device_index=1,
                                    frames_per_buffer=FRAME_SIZE,
                                    stream_callback=self.capture_callback)
        self.vad = webrtcvad.Vad(level)
        self.quit = False

        # Create a decoder with certain model
        config = Decoder.default_config()
        # config.set_string('-hmm', os.path.join(script_dir, 'en-US/acoustic-model'))
        config.set_string('-hmm', os.path.join(script_dir, 'model/hmm/en'))
        # config.set_string('-lm', os.path.join(script_dir, 'model/coco.lm'))
        config.set_string('-dict', os.path.join(script_dir, 'model/respeaker.dic'))
        config.set_string('-keyphrase', 'Respeaker')
        config.set_float('-kws_threshold', 1e-30)
        config.set_int('-samprate', RATE)
        config.set_int('-nfft', 2048)
        config.set_string("-logfn", os.devnull)
        self.decoder = Decoder(config)
        self.decoder.start_utt()
        self.decoder_need_restart = False

        self.ring_buffer = collections.deque(maxlen=PADDING_FRAMES)
        self.triggered = False
        self.ring_buffer_flags = [0] * KEY_FRAMES
        self.ring_buffer_index = 0
        self.duration = 0
        self.max_duration = 9000

    def capture_callback(self, data, frame_count, time_info, status):
        active = self.vad.is_speech(data, RATE)
        sys.stdout.write('1' if active else '0')
        self.ring_buffer_flags[self.ring_buffer_index] = 1 if active else 0
        self.ring_buffer_index += 1
        self.ring_buffer_index %= KEY_FRAMES
        if not self.triggered:
            self.ring_buffer.append(data)
            num_voiced = sum(self.ring_buffer_flags)
            if num_voiced > 0.6 * KEY_FRAMES:
                sys.stdout.write('+')
                self.triggered = True
                self.queue.put((b''.join(self.ring_buffer), False))
                self.duration = PADDING_DURATION_MS
                self.ring_buffer.clear()
        else:
            ending = False  # end of a phrase
            num_voiced = sum(self.ring_buffer_flags)
            self.duration += FRAME_DURATION_MS
            if num_voiced < 0.2 * KEY_FRAMES or self.duration >= self.max_duration:
                self.triggered = False
                ending = True
                sys.stdout.write('-')

            self.ring_buffer.append(data)
            self.queue.put((data, ending))

        sys.stdout.flush()
        return None, pyaudio.paContinue

    def listen(self, max_duration=9000):
        self.ring_buffer.clear()
        self.triggered = False
        self.ring_buffer_flags = [0] * PADDING_FRAMES
        self.ring_buffer_index = 0

        with self.queue.mutex:
            self.queue.queue.clear()

        frames = []
        self.stream.start_stream()
        while not self.quit:
            data, ending = self.queue.get()
            frames.append(data)
            if ending:
                break

        self.stream.stop_stream()
        return b''.join(frames)

    def detect(self, keyphrase='Respeaker'):
        detected = False

        self.triggered = False
        self.ring_buffer.clear()

        with self.queue.mutex:
            self.queue.queue.clear()
        self.stream.start_stream()
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

        self.stream.stop_stream()
        return detected

    def close(self):
        self.quit = True
        self.queue.put((None, True))

        self.stream.close()
        self.pa.terminate()
