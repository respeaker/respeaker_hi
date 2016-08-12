import Queue
import collections
import os
import sys
from threading import Event
import pyaudio
import webrtcvad
from pocketsphinx.pocketsphinx import *

SAMPLE_RATE = 16000
CHUNK_MS = 30  # VAD chunk length: 10, 20 or 30 (ms)
CHUNK_FRAMES = int(SAMPLE_RATE * CHUNK_MS / 1000)  # 30 * 16 = 480
CHUNK_SIZE = CHUNK_FRAMES * 2  # 2 bytes width
DEFAULT_PADDING_CHUNKS = 32
DEFAULT_PADDING_MS = DEFAULT_PADDING_CHUNKS * CHUNK_MS
BUFFER_FRAMES = CHUNK_FRAMES * 4


class Microphone:
    def __init__(self, pa, level=3):
        self.queue = Queue.Queue()
        self.pa = pa
        self.stream = self.pa.open(format=pyaudio.paInt16,
                                   channels=1,
                                   rate=SAMPLE_RATE,
                                   input=True,
                                   start=False,
                                   input_device_index=1,
                                   frames_per_buffer=BUFFER_FRAMES,
                                   stream_callback=self._callback)
        self.vad = webrtcvad.Vad(level)
        self.quit_event = Event()

        script_dir = os.path.dirname(os.path.realpath(__file__))

        config = Decoder.default_config()
        config.set_string('-hmm', os.path.join(script_dir, 'model/hmm/en'))
        config.set_string('-dict', os.path.join(script_dir, 'model/respeaker.dic'))
        config.set_string('-kws', os.path.join(script_dir, 'model/keywords.txt'))
        # config.set_string('-keyphrase', 'respeaker')
        # config.set_float('-kws_threshold', 1e-43)
        config.set_int('-samprate', SAMPLE_RATE)
        config.set_int('-nfft', 2048)
        config.set_string('-logfn', os.devnull)
        try:
            self.decoder = Decoder(config)
        except Exception as e:
            print(
            "Maybe replace config.set_int('-samprate', SAMPLE_RATE) with config.set_float('-samprate', SAMPLE_RATE)")
            raise e
        self.decoder.start_utt()
        self.decoder_need_restart = False

    def _callback(self, in_data, frame_count, time_info, status):
        while len(in_data) >= CHUNK_SIZE:
            data = in_data[:CHUNK_SIZE]
            in_data = in_data[CHUNK_SIZE:]

            self.duration_ms += CHUNK_MS
            self.ring_buffer.append(data)

            active = self.vad.is_speech(data, SAMPLE_RATE)
            sys.stdout.write('1' if active else '0')
            self.ring_buffer_flags[self.ring_buffer_index] = 1 if active else 0
            self.ring_buffer_index += 1
            self.ring_buffer_index %= self.padding
            if not self.active:
                num_voiced = sum(self.ring_buffer_flags)
                if num_voiced >= 4:
                    sys.stdout.write('+')
                    self.active = True
                    self.queue.put((b''.join(self.ring_buffer), False))
                    self.phrase_ms = len(self.ring_buffer) * CHUNK_MS
                    self.set_idle_padding()
                elif self.max_wait_ms and self.duration_ms > self.max_wait_ms:
                    self.queue.put(('', True))
            else:
                ending = False  # end of a phrase
                num_voiced = sum(self.ring_buffer_flags)
                self.phrase_ms += CHUNK_MS
                if num_voiced < 1 or (self.max_phrase_ms and self.phrase_ms >= self.max_phrase_ms):
                    self.active = False
                    ending = True
                    sys.stdout.write('-')

                self.queue.put((data, ending))

            sys.stdout.flush()

        return None, pyaudio.paContinue

    def listen(self, max_phrase_ms=9000, max_wait_ms=15000):
        self.start(max_phrase_ms, max_wait_ms)
        frames = []
        self.quit_event.clear()
        while not self.quit_event.is_set():
            data, ending = self.queue.get()
            if not data or ending:
                break
            frames.append(data)

        self.stop()
        return b''.join(frames)

    def detect(self, keyphrase='respeaker'):
        self.start()

        chunks = 0
        detected = False
        self.quit_event.clear()
        while not self.quit_event.is_set():
            if self.decoder_need_restart:
                print('\nrestart decoder')
                self.decoder.end_utt()  # it takes about 1 second on respeaker
                self.decoder.start_utt()
                self.decoder_need_restart = False
                chunks = 0

            data, ending = self.queue.get()
            if not data:
                break

            chunks += len(data) / CHUNK_SIZE
            self.decoder.process_raw(data, False, False)
            hypothesis = self.decoder.hyp()
            if hypothesis:

                if hypothesis.hypstr.find(keyphrase) >= 0:
                    print('\ndetected %s, analyzed %d chunks' % (keyphrase, chunks))
                    detected = True
                    self.decoder_need_restart = True
                    break

            if ending:
                self.set_active_padding()
                print('\nanalyzed %d chunks' % chunks)
                self.decoder_need_restart = True

        self.stop()
        return detected

    def recognize(self, max_phrase_ms=6000, max_wait_ms=15000):
        self.start(max_phrase_ms, max_wait_ms)

        utterance = None
        self.quit_event.clear()
        while not self.quit_event.is_set():
            if self.decoder_need_restart:
                print('\nrestart decoder')
                self.decoder.end_utt()  # it takes about 1 second on respeaker
                self.decoder.start_utt()
                self.decoder_need_restart = False

            data, ending = self.queue.get()
            if not data or ending:
                self.decoder_need_restart = True
                break

            self.decoder.process_raw(data, False, False)
            hypothesis = self.decoder.hyp()
            if hypothesis:
                utterance = hypothesis.hypstr
                self.decoder_need_restart = True
                break

        self.stop()
        return utterance

    def quit(self):
        self.quit_event.set()

    def close(self):
        self.stream.close()

    def set_active_padding(self, active_padding=8):
        self.padding = active_padding
        self.ring_buffer = collections.deque(maxlen=active_padding)
        self.ring_buffer_flags = [0] * active_padding
        self.ring_buffer_index = 0

    def set_idle_padding(self, idle_padding=40):
        self.padding = idle_padding
        self.ring_buffer = collections.deque(maxlen=idle_padding)
        self.ring_buffer_flags = [1] * idle_padding
        self.ring_buffer_index = 0

    def start(self, max_phrase_ms=0, max_wait_ms=0):
        self.set_active_padding()
        self.duration_ms = 0
        self.phrase_ms = 0
        self.max_phrase_ms = max_phrase_ms
        self.max_wait_ms = max_wait_ms
        self.active = False
        with self.queue.mutex:
            self.queue.queue.clear()
        self.stream.start_stream()

    def stop(self):
        self.stream.stop_stream()
