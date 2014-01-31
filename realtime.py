
import pyaudio
import wave
import time
import struct
import sys
import numpy as np
from numpy.fft import fft, fftfreq
import array
import Queue
import threading
from scipy import signal

#recording based on pyAudio 
class RecordStuff(threading.Thread):
    def __init__(self, queue):
        threading.Thread.__init__(self)
        self._queue = queue
        self.leftList = []
        self.rightList = []
        self.thresholdUpper = 0
        self.thresholdLower = 0
        self.CHUNK = 1024
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 2
        self.RATE = 44100
        self.p = pyaudio.PyAudio()
        self.recording = False

    def run(self):
        stream = self.p.open(format=self.FORMAT,
                    channels=self.CHANNELS,
                    rate=self.RATE,
                    input=True,
                    frames_per_buffer=self.CHUNK,
                    stream_callback=self.callback)

        print("* recording")
        stream.start_stream()
        while True:
            time.sleep(0.1)
        print("* done recording")

        stream.stop_stream()
        stream.close()
        self.p.terminate()


    def callback(self, in_data, frame_count, time_info, status):
        #altered pyaudio for recording, non-blocking
        thresholdCount = 1000 #number of times threshold must be reached
        thresholdCountLower = 1000 # "" for silence
        thresholdUp = 1300 #strength of signal needed
        for i in xrange(00, frame_count/4 +1, 1):
            # for each block of four chars
            temp=in_data[4*i:4*(i+1)] #read it into a temp file
            #unpack into numbers and store in array
            amp = struct.unpack('<H', temp[0:2])[0]
            if amp > 0x7fff: # offset issues. 0x7fff is highest possible for WAV
                amp -= 0x10000

            #this block of code checks the threshold levels and starts or stops
            #recording appropiately

            if abs(amp) > thresholdUp:  # greater than 900 
                self.thresholdUpper += 1
            else:
                self.thresholdLower +=1


            if self.thresholdUpper > thresholdCount:
                self.thresholdLower = 0
                self.thresholdUpper = 0
                if self.recording == False:
                    self.recording = True

            if self.recording == True:
                self.leftList.append(amp) #while recording append to list

            if self.thresholdLower > thresholdCountLower:
                self.thresholdUpper = 0
                self.thresholdLower = 0
                if self.recording == True:
                    self._queue.put((np.array(self.leftList)))
                    #send list to queue when done recording
                    self.recording = False
                    self.leftList = []

        return (None, pyaudio.paContinue) # return it

"""Used for Testing 

def analyze():
    a = Analyzer(q)
    a.run()

def record():
    r = RecordStuff(q)
    r.run()

class Game():
    def __init__(self):
        pass

    def timerFired(self):
        1+2

    def run(self):

        self.timerFired()

        t = threading.Thread(target=record)
        t.daemon = True
        t.start()

        a = threading.Thread(target = analyze)
        a.daemon = True
        a.start()

        while True:
            self.timerFired()

q = Queue.Queue(0)
game = Game()
game.run()
"""