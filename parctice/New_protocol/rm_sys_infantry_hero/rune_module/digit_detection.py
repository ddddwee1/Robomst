import conv_deploy
import cv2
import time
import numpy as np

WHITE = (255,255,255)
BLACK = (0,0,0)

image_width = 640
image_height = 480

kernel2 = np.ones((2,2),np.uint8)
kernel3 = np.ones((3,3),np.uint8)

def hist_equal(img):
	equ = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
	equ[:,:,2] = cv2.equalizeHist(equ[:,:,2])
	equ = cv2.cvtColor(equ, cv2.COLOR_HSV2BGR)
	return equ

def get_digits(image,bigbuff=False):

	leftRect = []
	rightRect = []
	left_rect = []
	right_rect = []
	row_left_rect = []
	row_right_rect = []
	leftRect2  = []
	rightRect2 = []

	gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
	#blur = cv2.GaussianBlur(gray,(3,3),0)
	#blur = cv2.GaussianBlur(gray,(3,3),0)
	blurred = cv2.bilateralFilter(gray, 3, 119, 109)
	#_,th3 = cv2.threshold(blurred,200,255,cv2.THRESH_BINARY)# +cv2.THRESH_OTSU)
	edged = cv2.Canny(blurred, 230, 240)
	
	cv2.imshow('',image)

	#cv2.waitKey(1)
	_, contours, hierarchy = cv2.findContours(edged.copy(),cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)

	for contour in contours:
		peri = cv2.arcLength(contour,True)
		contour = cv2.approxPolyDP(contour, 0.0001 * peri, True)
		if cv2.contourArea(contour)<200 or cv2.contourArea(contour)>1000:
			continue

		x,y,w,h = cv2.boundingRect(contour)

		if (w / h) < 1.0 or (w / h) > 2.5:
			continue
		#print cv2.contourArea(contour)
		cv2.drawContours(edged, [contour], -1, (255, 255, 255), 3)

		if x < (image_width//2):
			leftRect2.append([x,y,w,h])
		else:
			rightRect2.append([x,y,w,h])

	cv2.imshow('abc',edged)
	cv2.waitKey(1)

	""" 
	Left rectangle
	"""
	for i in range (len(leftRect2)):
		if i %2 == 0:
			leftRect.append(leftRect2[i])

	for i in range(len(leftRect)):
		find_left = False
		xi,_,_,_ = leftRect[i]
		for j in range(len(leftRect)):
			if i != j:
				xj1,_,_,_ = leftRect[j]
				if abs(xi - xj1) < 8 :
					find_left = True
					break
			else:
				pass

		if find_left == True:
			left_rect.append(leftRect[i])

	for i in range(len(left_rect)):
		x1,y1,w1,h1 = left_rect[i]
		row_left_rect.append(y1)

	""" 
	Right rectangle
	"""

	for i in range (len(rightRect2)):
		if i %2 == 0:
			rightRect.append(rightRect2[i])

	for i in range(len(rightRect)):
		find_right = False
		xi,_,_,_ = rightRect[i]
		for j in range(len(rightRect)):
			if i != j:
				xj1,_,_,_ = rightRect[j]
				if abs(xi - xj1) < 8:
					find_right = True
					break
			else:
				pass

		if find_right == True:
			right_rect.append(rightRect[i])

	for i in range(len(right_rect)):
		x2,y2,w2,h2 = right_rect[i]
		row_right_rect.append(y2)

	if len(row_left_rect) == 0 or len(row_right_rect) == 0:
		return [-1],[-1],[-1],[-1]

	tl_index = np.argmin(row_left_rect)
	bl_index = np.argmax(row_left_rect)
	tr_index = np.argmin(row_right_rect)
	br_index = np.argmax(row_right_rect)

	x1,y1,w1,h1=left_rect[tl_index]
	x2,y2,w2,h2=left_rect[bl_index]
	x3,y3,w3,h3=right_rect[tr_index]
	x4,y4,w4,h4=right_rect[br_index]

	sr_tl = [x1,y1]
	sr_bl = [x2,y2+h2]
	sr_tr = [x3+w3,y3]
	sr_br = [x4+w4,y4+h4]

	coord = [[x1,y1,w1,h1],[x2,y2,w2,h2],[x3,y3,w3,h3],[x4,y4,w4,h4]]

	pts1 = np.float32([sr_tl,sr_tr,sr_bl,sr_br])
	pts2 = np.float32([[0, 52],[300, 52],[0, 200],[300, 200]])
	M = cv2.getPerspectiveTransform(pts1,pts2)

	dst = cv2.warpPerspective(image,M,(300,200))
	#cv2.imshow('aaa',dst)
	#cv2.waitKey(1)

	""" 
	7segment
	"""

	digits_7seg_rect = [(100, 0), (121, 0), (142, 0), (163, 0), (184, 0)]

	digit_7seg_imgs = []

	for x,y in digits_7seg_rect:
		#cv2.rectangle(dst,(x,y),(x+20,y+32),(255,0,0),1)
		img_sevseg = dst[y:y+34,x:x+21]

		# another test
		img_sevseg = img_sevseg[:,:,2]
		img_sevseg = cv2.inRange(img_sevseg,210,255)
		img_sevseg = cv2.morphologyEx(img_sevseg,cv2.MORPH_OPEN,kernel2)
		img_sevseg = cv2.morphologyEx(img_sevseg,cv2.MORPH_CLOSE,kernel2)
		#cv2.imshow('bb',img_sevseg)
		#cv2.waitKey(0)

		buf = cv2.bitwise_not(img_sevseg)
		buf = cv2.dilate(buf,kernel2,iterations = 1)
		#buf = cv2.erode(buf,kernel2,iterations = 2)
		buf = cv2.resize(buf,(24,24))
		buf = cv2.copyMakeBorder(buf, 2, 2, 2, 2, cv2.BORDER_CONSTANT, value=WHITE)
		#cv2.imshow('aaa',buf)
		#cv2.waitKey(0)

		buf = buf.reshape([-1])
		buf = 255 - buf
		buf = np.float32(buf) / 255.
		buf = buf.reshape([-1])
		digit_7seg_imgs.append(buf)

	#cv2.imshow('jkjg',dst)
	#cv2.waitKey(0)

	scr_7seg_raw = conv_deploy.get_pred_7seg(digit_7seg_imgs)
	#print (scr_7seg_raw)

	if bigbuff == False:
		""" 
		Handwritten
		"""
		digits_rect = [(49,54),(124,54),(199,54),(49,108),(124,108),(199,108),(49,162),(124,162),(199,162)]
		digit_imgs = []
		abc = 0
		for x,y in digits_rect:
			#cv2.rectangle(dst,(x,y),(x+50,y+36),(0,0,255),1)
			buf =  dst[y:y+36,x:x+50]
			buf = cv2.cvtColor(buf,cv2.COLOR_BGR2GRAY)
			_,buf = cv2.threshold(buf,20,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)
			buf = cv2.erode(buf,kernel2,iterations = 1)
			buf = cv2.resize(buf,(24,24))
			buf = cv2.copyMakeBorder(buf, 2, 2, 2, 2, cv2.BORDER_CONSTANT, value=WHITE)

			#cv2.imshow('cv',buf)
			#cv2.waitKey(0)

			buf = 255 - buf
			buf = np.float32(buf) / 255.
			buf = buf.reshape([-1])
			digit_imgs.append(buf)

		#cv2.imshow('aaa',dst)
		#cv2.waitKey(1)

		handwritten_num_raw = conv_deploy.get_pred(digit_imgs)
		#print(handwritten_num_raw)

		handwritten_dict = {}

		# filter handwritten_num
		for i in range(len(handwritten_num_raw)):
			handwritten_dict[handwritten_num_raw[i]] = np.count_nonzero(handwritten_num_raw[i])

		if len(handwritten_dict) >= 9 :
			handwritten_num= handwritten_num_raw
			#print handwritten_num
		else:
			handwritten_num = [-1]
			pass

		Flaming_digit = [-1]
		#print handwritten_num

	else:
		""" 
		Flaming Digits
		"""

		flamingdigits_rect = [(59,53),(132,53),(206,53),(59,106),(132,106),(206,106),(59,160),(132,160),(206,160)]
		digit_imgs = []
		abc = 0
		for x,y in flamingdigits_rect:
			#cv2.rectangle(dst,(x,y),(x+34,y+37),(255,555,255),1)
			buf =  dst[y:y+37,x:x+33]
			img_FD = cv2.cvtColor(buf,cv2.COLOR_BGR2GRAY)
			_,buf = cv2.threshold(img_FD,150,255,cv2.THRESH_TOZERO+cv2.THRESH_OTSU)
			#edged = cv2.Canny(buf, 200, 255)
			_, contours, hierarchy = cv2.findContours(buf.copy(),cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
			cv2.drawContours(buf, contours, -1, 255 , -1)
			buf = cv2.bitwise_not(buf)
			buf = cv2.resize(buf,(24,24))
			buf = cv2.copyMakeBorder(buf, 2, 2, 2, 2, cv2.BORDER_CONSTANT, value=WHITE)

			cv2.imshow('cv',buf)
			#cv2.waitKey(0)

			buf = 255 - buf
			buf = np.float32(buf) / 255.
			buf = buf.reshape([-1])
			digit_imgs.append(buf)

		#cv2.imshow('aaa',dst)
		#cv2.waitKey(1)

		scr_FD_raw = conv_deploy.get_pred_flaming(digit_imgs)
		print ('fd',scr_FD_raw)
 	
		#filter flaming digit
		num_FD_dict = {}
		for i in range(len(scr_FD_raw)):
			num_FD_dict[scr_FD_raw[i]] = np.count_nonzero(scr_FD_raw[i])

		if len(num_FD_dict) >= 9 :
			Flaming_digit= scr_FD_raw
			#print Flaming_digit
		else:
			Flaming_digit = [-1]
			pass

		handwritten_num = [-1]

	cv2.imshow('aaa',dst)
	#cv2.waitKey(0)
	return coord, scr_7seg_raw, handwritten_num, Flaming_digit
