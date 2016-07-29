"""
This is the worker thread which handles the input (string).
"""

import threading
import Queue
import time
import re

class Worker(threading.Thread):
    def __init__(self, queue_len = 10):
        threading.Thread.__init__(self)
        self.q = Queue.Queue(queue_len)
        self.thread_stop = False

    def set_tts(self, tts):
        self.tts = tts

    def set_player(self, ply):
        self.player = ply

    def push_cmd(self, cmd):
        self.q.put(cmd)

    def hook(self):
        """
        do stuff in the thread loop
        """
        pass

    def run(self):
        while not self.thread_stop:
            self.hook()
            cmd = ''
            try:
                cmd = self.q.get(timeout=1)
            except:
                continue
            print("worker thread get cmd: %s" %(cmd, ))
            self._parse_cmd(cmd)
            self.q.task_done()
            len = self.q.qsize()
            if len > 0:
                print("still got %d commands to execute." % (len,))

    def _parse_cmd(self, cmd):
        if re.match(r'how.*(plant|plants).*(going|doing)?', cmd) or re.match(r'check.*(plant|plants).*', cmd):
            print 'they are good'
            self.player.play_buffer(self.tts.speech('they are good.'))
        else:
            print 'unknown command, ignore.'

    def stop(self):
        self.thread_stop = True
        self.q.join()
