import cv2, numpy as np

# open video file
cap = cv2.VideoCapture('video.mp4')

# get the frames per second
fps = cap.get(cv2.CAP_PROP_FPS)

# get the total number of frames
frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

# get the frame with max brightness
max_brightness_frame = None
max_brightness = 0
for i in range(frame_count):
    cap.set(cv2.CAP_PROP_POS_FRAMES, i)
    ret, frame = cap.read()
    brightness = np.sum(frame)
    if brightness > max_brightness:
        max_brightness = brightness
        max_brightness_frame = frame

# display the frame with max brightness
cv2.imshow('frame', max_brightness_frame)

# find the location of the brightest pixel in every frame after the max brightness frame
for i in range(frame_count):
    cap.set(cv2.CAP_PROP_POS_FRAMES, i)
    ret, frame = cap.read()
    if i > 0:
        max_brightness = 0
        for y in range(frame.shape[0]):
            for x in range(frame.shape[1]):
                brightness = np.sum(frame[y,x])
                if brightness > max_brightness:
                    max_brightness = brightness
                    brightest_pixel = (x,y)
        print(i, brightest_pixel)