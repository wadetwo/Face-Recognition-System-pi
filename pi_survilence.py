from pyimagesearch.tempimage import TempImage
#from dropbox.client import DropboxOAuth2FlowNoRedirect
#from dropbox.client import DropboxClient
from picamera.array import PiRGBArray
from picamera import PiCamera
import argparse
import warnings
import datetime
import imutils
import json
import time
import cv2

ap = argparse.ArgumentParser()
ap.add_argument("-c", "--conf",required=True,help="path to the JSON configureation file")
args = vars(ap.parse_args())

warnings.filterwarnings("ignore")
conf = json.load(open(args["conf"]))
client = None

if conf["use_dropbox"]:
	flow = DropboxOAuth2FlowNoRedirect(conf["dropbox_key"],conf["dropbox_secret"])
	print "[INFO] Authorize this application: {}".format(flow.start())
	authCode = raw_input("Enter auth code here: ").strip()
	(accessToken, userID) = flow.finish(authCode)
	client = DropboxClient(accessToken)
	print "[SUCESS] dropbox account linked"

camera = PiCamera()
camera.resolution = tuple(conf["resolution"])
camera.framerate = conf["fps"]
rawCapture = PiRGBArray(camera,size=tuple(conf["resolution"]))

print "[INFO] warming up..."
time.sleep(conf["camera_warmup_time"])
avg = None
lastUploaded = datetime.datetime.now()
motionCounter = 0

for f in camera.capture_continuous(rawCapture, format="bgr",use_video_port=True):
	
	frame = f.array
	timestamp = datetime.datetime.now()
	text="Unoccupied"
	frame = imutils.resize(frame, width=500)
	gray = cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)
	gray = cv2.GaussianBlur(gray,(21, 21),0)

	if avg is None:
		print "[INFO] starting background model..."
		avg = gray.copy().astype("float")
		rawCapture.truncate(0)
		continue
	cv2.accumulateWeighted(gray,avg,0.5)
	frameDelta = cv2.absdiff(gray,cv2.convertScaleAbs(avg))
	thresh = cv2.threshold(frameDelta,conf["delta_thresh"],255,cv2.THRESH_BINARY)[1]
	thresh = cv2.dilate(thresh,None,iterations=2)
	(cnts,_)=cv2.findContours(thresh.copy(),cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
	for c in cnts:
		if cv2.contourArea(c) < conf["min_area"]:
			continue
		(x,y,w,h) = cv2.boundingRect(c)
		cv2.rectangle(frame,(x,y),(x+w,y+h),(0,255,0),2)
		text = "occupied"
	ts = timestamp.strftime("%A %d %B %Y %I:%M:%S%p")
	cv2.putText(frame, "Room status:{}".format(text),(10,20),cv2.FONT_HERSHEY_SIMPLEX,0.5,(0,0,255),2)
	cv2.putText(frame, ts, (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1)

	if text == "occupied":
		if(timestamp -lastUploaded ).seconds >= conf["min_upload_seconds"]:
			motionCounter += 1
			if motionCounter >= conf["min_motion_frames"]:
				if conf["use_dropbox"]:
					t = TempImage()	
					cv2.imwrite(t.path,frame)
					print "[Upload] {}".format(ts)
					path = "{base_path}/{timestamp}.jpg".format(base_path=conf["dropbox_base_path"],timestamp=ts)
					client.put_file(path,open(t.path,"rb"))
					t.cleanup()
				else: 
                                        t = TempImage()
                                        cv2.imwrite(t.path,frame)
					print "[Upload] {}".format(ts)
				lastUploaded = timestamp
				motionCounter = 0
	else:
		motionCounter = 0

	if conf["show_video"]:
		cv2.imshow("Security Feed", frame)
		key = cv2.waitKey(1)&0xFF
		if key == ord("q"):
			break
	rawCapture.truncate(0)
