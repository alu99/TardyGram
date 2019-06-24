import time
import tweepy 
import pygame
import urllib 
import textwrap
import pygame.camera
import RPi.GPIO as GPIO
from escpos import *
from PIL import Image
from PIL import ImageEnhance
from pygame.locals import *
from datetime import datetime
from tweepy.streaming import StreamListener

PRINTER_PORT = '/dev/ttyUSB0'
Epson = printer.SerialU210(PRINTER_PORT)
    
pygame.init()
pygame.camera.init()

GPIO.setmode(GPIO.BCM)
GPIO.setup(23, GPIO.OUT)
GPIO.setwarnings(False)
				
#OAuth authentification
consumer_key='xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
consumer_secret='xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
access_token='xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
access_token_secret='xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'

auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_token_secret)

api = tweepy.API(auth)

#limits to 2 Tweet replies per hour (otherwise we'll run out of paper too quickly)
class TweetTimer():
	
	TIMEOUT = 3600
	COUNTS = 3000000
		
	def __init__(self):
		self.prevtime = 0
		self.count = 0
			
	def limiter(self):
		
		# Call this function/method to check if we should process a tweet	
		currtime = time.time()
		if currtime >= (self.prevtime + self.TIMEOUT):
			self.prevtime = currtime
			self.count = 0
			return True
			
		elif self.count < self.COUNTS:
			self.count += 1
			return True
		
		else:
			return False
	
#listening for new Tweets that mention @TardyGram
class MyStreamListener(tweepy.StreamListener):	
	
	def __init__(self, myTimer, wait_on_rate_limit):
		self.disconnect = True
		self.wait_on_rate_limit = True
		self.myTimer = myTimer
		self.final_status_text = ""
		self.statusid = ""
		self.screenname = ""
		self.cam = pygame.camera.Camera("/dev/video0",(1280,960))
		tweepy.StreamListener.__init__(self)
	
	#called when tweet received
	def on_status(self, status):
			
		print status.text
		
		#checks to see if there is an image in the tweet, if not ignores
		if status.user.screen_name != 'tardygram':
	
			if 'http://t.co/' or 'https://pbs.twimg.com/media/' in status.text:
				
				if '@ RT' not in status.text:
					
					if self.myTimer.limiter():
						
						print "In Time"
						
						index = status.text.find("http://t.co/")
						
						if len(status.text[index:]) >= 22:
							tweeturl = status.text[index:index +22]
							self.final_status_text = status.text[:index] + status.text[index +22:]
							print tweeturl
						
						#locates image url & downloads into tweet_data folder
						try:
							tweeturl = status.extended_entities["media"][0]["media_url"]
							#urllib.urlretrieve(tweeturl,'/home/pi/tweet_data/TWEETIMG')
						except:
							print "no image"
						else:
						
							#tweeturl = self.final_status_text[self.final_status_text.find("http://t.co/"):]
							
							urllib.urlretrieve(tweeturl,'/home/pi/tweet_data/TWEETIMG.jpg')
								
							#finds the sender id so we can reply with finished product
							self.statusid = status.id_str
							self.screenname = status.user.screen_name
							
							#removes the image url from the text
							#self.final_status_text = status.text[:status.text.find("http://t.co/")-1]
							
							#finds '<' in the html of tweet and converts to plain text						
							pos = self.final_status_text.find('&lt;')
							if pos != -1:
								
								firsthalf = self.final_status_text[:pos]
								secondhalf = self.final_status_text[(len(firsthalf)+4):]
								self.final_status_text = firsthalf + '<' + secondhalf
							
							#finds '>' in the html of tweet and converts to plain text	
							pos = self.final_status_text.find('&gt;')
							if pos != -1:
								
								firsthalf = self.final_status_text[:pos]
								secondhalf = self.final_status_text[(len(firsthalf)+4):]
								self.final_status_text = firsthalf + '>' + secondhalf
								
							#finds '&' in the html of tweet and converts to plain text
							pos = self.final_status_text.find('&amp;')	
							if pos != -1:
								firsthalf = self.final_status_text[:pos]
								secondhalf = self.final_status_text[(len(firsthalf)+5):]
								self.final_status_text = firsthalf + '&' + secondhalf
								
							print "final text is " + self.final_status_text
							
							#print returning False
							
							self.disconnect = False
						
							self.printing_reply()
				
					else:
						print "Exceeded limit per hour"
						current = datetime.now()
						api.update_status(status = "@" + self.screenname +" Sorry, we can only print 2 tweets per hour. Please try again later. " + "\nDate: " + str(current.month)+'-'+str(current.day)+'-'+str(current.year)+'\nTime: '+str(current.hour)+':'+str(current.minute)+':'+str(current.second),  in_reply_to_status_id = self.screenname)
						return True
						
				else:
					print "is retweet, won't print"
					return True
				
			else:
				print "no photo in tweet"
				return True
		else:
			print "Is a reply from myself"
			return True
				
	def printing_reply (self):
		print "print reply called"
		
		current = datetime.now()
		#api.update_status(status = "Printer busy, please hold your tweets until further notice. " + "\nDate: " + str(current.month)+'-'+str(current.day)+'-'+str(current.year)+'\nTime: '+str(current.hour)+':'+str(current.minute)+':'+str(current.second))
		
		#Prints the image and the text
		WIDTH = 33
		wrapped_text = textwrap.wrap(self.final_status_text, WIDTH)
		
		print "printing text"
		Epson.set(upsidedown=True)
		for line in reversed(wrapped_text):
			Epson.text(line+'\n')
		Epson.text('\n')
		Epson.set(upsidedown=False)
		print "printing image"
		Epson.image('/home/pi/tweet_data/TWEETIMG.jpg')
		Epson.text('\n\n\n\n\n\n\n\n\n\n\n\n') 
		print "printed image and text"
		
		#captures the image of the printed product
		self.cam.start()
		GPIO.output(23, GPIO.HIGH)
		img = self.cam.get_image()
		GPIO.output(23, GPIO.LOW)
		pygame.image.save(img,"/home/pi/tweet_data/RETURNIMG.jpg")
		self.cam.stop()
		print "took/saved photo"
			
		#rotates the photo
		img2 = Image.open("/home/pi/tweet_data/RETURNIMG.jpg")
		img3 = img2.rotate(90)
		img3.save("/home/pi/tweet_data/RETURNIMG.jpg")
		print "rotated photo"
		
		#adds contrast to image
		contrast = 1.3
		toContrast = Image.open("/home/pi/tweet_data/RETURNIMG.jpg")
		enhancer = ImageEnhance.Contrast(toContrast)
		con = enhancer.enhance(contrast)
		con.save("/home/pi/tweet_data/RETURNIMG.jpg")
		
		
		#replies to sender with finished photo	
		api.update_with_media(filename= "/home/pi/tweet_data/RETURNIMG.jpg" , in_reply_to_status_id = self.statusid, status = "@"+ self.screenname + " You've been Tardygrammed!")
		print "replied"
		
		current = datetime.now()
		#api.update_status(status = "Printer Available! " + "\nDate: " + str(current.month)+'-'+str(current.day)+'-'+str(current.year)+'\nTime: '+str(current.hour)+':'+str(current.minute)+':'+str(current.second))
				
myTimer = TweetTimer()
myStreamListener = MyStreamListener(myTimer, wait_on_rate_limit=True)
myStream = tweepy.Stream(auth=api.auth,listener=myStreamListener)
myStream.filter(track=['@tardygram'])
		

while True:
	
	myStream.filter(track=['@tardygram'])
	
	if myStreamListener.disconnect == False:
		print "inside if statement"
		myStreamListener.printing_reply()
	
	else:
		print "no exceptions"
		

		


	

 



