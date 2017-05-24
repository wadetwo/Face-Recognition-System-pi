from picamera.array import PiRGBArray
from picamera import PiCamera
import time
import cv2

camera = PiCamera()
rawcapture = PiRGBArray(camera)

time.sleep(0.1)

camera.capture(rawcapture,format = "bgr")
image = rawcapture.array

cv2.imshow("image", image)
cv2.waitKey(0)
