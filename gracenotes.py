import Tkinter as tk
from PIL import Image, ImageTk
import array
import threading
import winsound
import sys
from random import choice
from realtime import *
from scipy import signal 

""""
Much thanks to:
TkDocs 
TKinter Documentation
PyAudio Documentation
Stack Overflow for TKinter Frame navigation method
"""

#DICTIONARIES OF KEYS AND FREQUENCIES#
FreqToKeyNotes = {261.626: "C4", 523.251: "C5", 293.665: "D4", 587.33: "D5", 
329.628: "E4", 659.255: "E5",
349.228: "F4", 415.305: "G4", 440.000: "A4", 493.883: "B4"}

KeyToPos = {"C4": 615, "D4": 585, "E4": 540, "F4": 505, "G4": 463, "A4": 415, 
"B4": 375, "C5": 335, "D5": 290, "E5": 255}

#################### MAIN WINDOW #########################
class GraceNote(tk.Tk): #Main Class
    def switch_frame(self, c): #switch to different screens
        frame = self.frames[c] 
        self.currentFrame = str(c)
        frame.focus_set()
        frame.lift() #bring the frame to the front

    def __init__(self):
        tk.Tk.__init__(self)
        self.geometry("1500x900+500+500") #size of the canvas
        self.container = tk.Frame(self) 
        self.container.pack(expand=True, anchor="center", fill = "both")
        self.frames = {}
        self.currentFrame = None
        for frameName in (SplashScreen, Game, Instructions):
            frame = frameName(self.container,self)
            self.frames[frameName] = frame #add frames to list of frames
            frame.grid(row = 0, column = 0, sticky = "nsew") #add frame to grid

        self.switch_frame(SplashScreen) #start at front page

    def quit(self): #quit game
        sys.exit()

##                    Instructions Page                   ##
class Instructions(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)

        self.parent = parent
        self.pack()

        self.canvas = tk.Canvas(self, width=1500, height=900)
        class Struct(): pass
        self.canvas.data = Struct()

        #add images of instructions
        self.canvas.data.photo = tk.PhotoImage(file="img/bgdblank.gif")
        self.canvas.data.menuphoto = tk.PhotoImage(file="img/bgdmenu.gif") 
        self.canvas.create_image(0,0, image = self.canvas.data.photo, anchor = "nw")
        self.canvas.create_image(0,0, image=self.canvas.data.menuphoto, anchor = "nw")

        self.canvas.pack()

        #return key for going back to the menu
        self.bind("<Return>", lambda event: controller.switch_frame(SplashScreen))

##                    The thread that Analyzes Music    ##
class Analyzer(threading.Thread):
    def __init__(self, queue, daemon):
        #initialize a thread that takes a queue
        threading.Thread.__init__(self)
        self._queue = queue #takes queue
        self.daemon = daemon #closes on exit

    def run(self):
        while True:
            if not self._queue.empty():
                item = self._queue.get()

                """
                b, a = signal.butter(15, 0.125) #low pass filter
                item = signal.filtfilt(b, a, item, padlen=50) #butterworth filter (scipy)
                """
                #fft with numpy 
                freqsleft = np.fft.rfft(item)
                #autocorrelation with numpy
                autocorrLeft = np.fft.irfft(freqsleft * np.conj(freqsleft))

                RATE = 44100
                period = 0
                i = 20
                offset = 20
                # find first peak after zero for autocorrelation period
                #first find trough
                while ((i+offset < len(autocorrLeft)) and autocorrLeft[i-offset] > autocorrLeft[i] and autocorrLeft[i+offset] < autocorrLeft[i]):
                    i += offset
                #then find peak

                while ((i+offset < len(autocorrLeft)) and autocorrLeft[i-offset] > autocorrLeft[i] or autocorrLeft[i+offset] > autocorrLeft[i]):
                        i += offset
                period = i
                
                maximum = max(autocorrLeft[i - offset:i + offset])
                period = np.nonzero(autocorrLeft == maximum)[0][0]
                if period <= 60:
                    period = period * 2 

                #if period >= 50: #ignore octave errors
                answer = (1.0/RATE) * period 
                frequency =  1.0/answer #frequency = 1/period

                minimum = 3737373 #definitely not singing this high
                minFreq = None

                for freq in FreqToKeyNotes: #check for the closest note 
                    if abs(frequency-freq) < minimum:
                        minimum = abs(frequency-freq)
                        minFreq = FreqToKeyNotes[freq]
                game.frames[Game].currBall.y = KeyToPos[minFreq] #move player
 
# class for player object, the Box                
class Box():
    count = 0
    listOfBoxes = []
    def __init__(self, x):
        self.note = choice(KeyToPos.keys())
        self.x = x
        self.y = KeyToPos[self.note] #determine starting position
        Box.count += 1
        Box.listOfBoxes.append(self) #in case I ever want more than one Box

    def redrawAll(self, canvas):
        canvas.create_image(self.x, self.y, image = game.frames[Game].canvas.data.box, anchor = "nw")

# Green obstacle stars to catch
class Obstacle():
    count = 0
    listOfObstacles = []
    def __init__(self, x):
        self.note = choice(KeyToPos.keys())
        self.x = x
        self.y = KeyToPos[self.note] #starting position
        self.color = "blue" #these are blue
        Obstacle.count += 1 #keep track of number
        Obstacle.listOfObstacles.append(self)

    def redrawAll(self, canvas):
        if self.color == "orange":
            canvas.create_image(self.x, self.y, image = game.frames[Game].canvas.data.orangestar, anchor = "nw")
        elif self.color == "red":
            canvas.create_image(self.x, self.y, image = game.frames[Game].canvas.data.redstar, anchor = "nw")
        elif self.color == "blue":
            canvas.create_image(self.x, self.y, image = game.frames[Game].canvas.data.greenstar, anchor = "nw")

# New Life stars give player another life
class NewLife(Obstacle): #wish these were real
    def __init__(self, x):
        Obstacle.__init__(self, x)
        self.color = "orange"

# Error Stars take away lives. They are special obstacles
class ErrorStar(Obstacle):
    def __init__(self, x):
        Obstacle.__init__(self, x)
        self.color = "red" #glad these don't actually exist


#The Actual Game is here
class Game(tk.Frame):

    def keyPressed(self, canvas, event):
        if event.char == "q": # q for quit
            sys.exit()

    def record(self): #start recording thread
        t = RecordStuff(self.queue)
        t.run()

    
    def playReference(self, canvas): #plays A (440 Hz)
        winsound.Beep(440, 800) #800 ms

    
    def drawAll(self):
        self.canvas.delete("all")
        self.canvas.create_image(0,0, image = self.canvas.data.gamebgd, anchor = "nw")
        # game information print to screen
        self.canvas.create_text(300, 100, text= "%d" % self.score, font = ("Helvetica", 36), fill = "white" )
        self.canvas.create_text(550, 100, text= "LIVES: %d" % self.lives, font = ("Helvetica", 26), fill = "white" )
        self.canvas.create_text(900, 100, text= "Lv.%d" % self.level, font = ("Helvetica", 26), fill = "red")
        # draw obstacles and stars if game is in play
        if self.gameStarted == True:
            self.canvas.create_image(0,0, image = self.canvas.data.gamerecord, anchor = "nw")
            for obstacle in Obstacle.listOfObstacles:
                obstacle.redrawAll(self.canvas)
            for box in Box.listOfBoxes:
                box.redrawAll(self.canvas)
        else:
            # end game
            if self.lives == 0:
                self.canvas.create_text(300,100, text="%d" % self.score, font = ("Helvetica", 40), fill = "white")

    def endGame(self):
        self.gameStarted = False

    def createNewLife(self):
        #function periodically makes New Life stars
        delay = 10000
        if self.new == True:
            xcoord = 960
            NewLife(xcoord) #see createObstacle
        else:
            self.new = True
        def f():
            self.createNewLife()
        if self.gameStarted == True:
            self.canvas.after(delay, f)

    def createErrorStar(self):
        #function periodically makes Error Stars depending on level
        xcoord = 960
        ErrorStar(xcoord)
        def f():
            self.createErrorStar()
        if self.gameStarted == True:
            self.canvas.after(self.delay, f)

    def createObstacle(self):
        #periodically makes obstacles 
        xcoord = 960
        Obstacle(xcoord) #creates obstacle at x -coordinate 960
        delay = 1500
        def f():
            self.createObstacle()
        if self.gameStarted == True:
            self.canvas.after(delay, f)

    def timerFired(self):
        self.drawAll()

        if self.lives == 0: #if game has ended
            if self.wait == 100:
                self.gameStarted = False #toggle game started 
                #DELETE ALL THE THINGS
                Box.listOfBoxes = []
                Obstacle.listOfObstacles = [] #clear list of obstacles
                with self.queue.mutex: #clear queue
                    self.queue.queue.clear()
                self.currBall = None
            self.wait -= 1

        else: #what happens when you encounter an obstacle?
            for obstacle in Obstacle.listOfObstacles:
                obstacle.x -= 5
                if obstacle.x == self.currBall.x and obstacle.y == self.currBall.y:
                    Obstacle.listOfObstacles.remove(obstacle)
                    if obstacle.color == "blue":
                        self.score += 10 #increase score if collect blue star
                    if obstacle.color == "red":
                        self.lives -= 1 #oops lost a life
                    if obstacle.color == "orange":
                        self.lives += 1 # orange stars regain life

        if self.wait == 0:
            self.newGame() #countdown to new game after game ended

        startingDelay = 1100 #time between sequential red stars

        if self.delay > 500: #changes level depending on current score
            self.level = self.score/50 + 1
            self.delay = startingDelay - (self.level-1) * 100

        delay = 20 # milliseconds
        def f():
            self.timerFired()
        self.canvas.after(delay, f) # pause, then call timerFired again
        
    def newGame(self): #set variables back to beginning
        self.currBall = Box(25)
        self.new = False
        self.lives = 5
        self.score = 0
        self.wait = 100
        self.level = 1
        self.delay = 1100
        self.gameStarted = True
        self.createObstacle()
        self.createNewLife()
        self.createErrorStar()


    def startGame(self, event):
        if self.gameStarted == False:
            self.currBall = Box(25)
            self.lives = 5
            self.score = 0
            self.delay = 1100
            self.level = 1
            self.gameStarted = True
            self.timerFired()
            self.createObstacle()
            self.new = False
            self.createNewLife()
            self.createErrorStar()

            t = threading.Thread(target=self.record) #start recording
            t.daemon = True
            t.start()
            
            Analyzer(self.queue, True).start() #start analyzing


    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent) 
        self.parent = parent
        self.pack()

        self.canvas = tk.Canvas(self, width=1500, height=900)
        class Struct(): pass
        self.canvas.data = Struct()
        #the game image files go here
        self.canvas.data.gamebgd = tk.PhotoImage(file="img/bgdgame.gif")
        self.canvas.data.gamerecord = tk.PhotoImage(file="img/gamerecord.gif")
        self.canvas.data.orangestar = tk.PhotoImage(file="img/orangestar.gif")
        self.canvas.data.redstar = tk.PhotoImage(file="img/redstar.gif")
        self.canvas.data.greenstar = tk.PhotoImage(file="img/greenstar.gif") 
        self.canvas.data.box = tk.PhotoImage(file="img/box.gif")   
        self.canvas.create_image(0,0, image = self.canvas.data.gamebgd, anchor = "nw")
        self.canvas.pack()
        self.queue = Queue.Queue(0) # self = QQ

        #variables and stuff
        self.gameStarted = False
        self.wait = 100
        self.x = 50
        self.y = 50

        #bindings 
        self.bind("<space>", lambda event: self.startGame(event))
        self.bind("<Key>", lambda event: self.keyPressed(self.canvas, event))
        self.bind("<Return>", lambda event: self.playReference(event))
        self.focus_set()



########## MENU PAGE STUFF #################
class SplashScreen(tk.Frame):

    def keyPressed(self, canvas, event):
        if game.currentFrame == "__main__.SplashScreen": #toggle selection
            if event.keysym == "Left":
                canvas.data.selection -= 1
                self.drawOptions(canvas, canvas.data.selection % 2)
            elif event.keysym == "Right":
                canvas.data.selection += 1
                self.drawOptions(canvas, canvas.data.selection %2)
        if event.char == "q": #quit 
            sys.exit()

    def drawOptions(self, canvas, selection = 0):
        canvas.delete("ALL")
        canvas.create_image(1000,760,image=canvas.menu1, anchor = "nw")
        if selection == 1: #change screen to reflect selection
            canvas.create_image(1000,760,image=canvas.menu2, anchor = "nw")


    def __init__(self,parent, controller):
        tk.Frame.__init__(self, parent)
        self.parent = parent
        self.pack()

        width = 1500
        height = 900
        canvas = tk.Canvas(self, background = "black", bd = 0, width = width, height = height)
    
        class Struct(): pass
        canvas.data = Struct()
        canvas.photo = tk.PhotoImage(file="img/bgd.gif")
        canvas.menu2= tk.PhotoImage(file="img/menu2.gif")
        canvas.menu1= tk.PhotoImage(file = "img/menu1.gif")

        canvas.create_image(0,0,image=canvas.photo, anchor = "nw")

        canvas.pack()
        canvas.data.selection = 0

        self.drawOptions(canvas)

        self.games = (Game, Instructions)
        self.bind("<Key>", lambda event: self.keyPressed(canvas,event))
        self.bind("<Return>", 
            lambda event: controller.switch_frame(self.games[canvas.data.selection % 2]))


game = GraceNote()
game.mainloop()