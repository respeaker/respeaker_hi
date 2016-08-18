
import os
import time
from threading import Thread, Event
from microphone import Microphone
from bing_voice import *
from player import Player
import pyaudio
import sys
try:
    from creds import BING_KEY
except ImportError:
    print('Get a key from https://www.microsoft.com/cognitive-services/en-us/speech-api and create creds.py with the key')
    sys.exit(-1)


script_dir = os.path.dirname(os.path.realpath(__file__))
hi = os.path.join(script_dir, 'audio/hi.wav')
mic = None
quit_event = Event()

def main():
    global mic, quit_event

    bing = BingVoice(BING_KEY)
    awake = False

    pa = pyaudio.PyAudio()
    mic = Microphone(pa)
    player = Player(pa)

    while not quit_event.is_set():
        if not awake:
            if mic.recognize(keyword='hey respeaker'):
                awake = True
                player.play(hi)
                continue
            else:
                break

        data = b''.join(mic.listen())
        if data:
            # recognize speech using Microsoft Bing Voice Recognition
            try:
                text = bing.recognize(data, language='en-US')
                print('Bing:' + text.encode('utf-8'))
                tts_data = bing.synthesize('you said ' + text)
                player.play_raw(tts_data)

                if text.find('start recording') >= 0:
                    mic.record('record.wav')
                elif text.find('stop recording') >= 0:
                    mic.interrupt(stop_recording=True)
                elif text.find('play recording audio') >= 0:
                    player.play('record.wav')
            except UnknownValueError:
                print("Microsoft Bing Voice Recognition could not understand audio")
            except RequestError as e:
                print("Could not request results from Microsoft Bing Voice Recognition service; {0}".format(e))
        else:
            print('no data')

        awake = False

    mic.close()

if __name__ == '__main__':
    thread = Thread(target=main)
    thread.start()
    while True:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            print('\nquit')
            quit_event.set()
            mic.interrupt(True, True)
            break

    thread.join()

