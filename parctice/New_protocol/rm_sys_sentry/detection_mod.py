from net import model as M 
from net import netpart, net_veri, netpart_s, net_veri_s
import tensorflow as tf 
import numpy as np
import cv2
import time

def get_img_coord(img,c,b,multip):
	# get the coordinations by c and b
	# multip is the gridsize.
	res = []
	c = c[0]
	b = b[0]
	row,col,_ = b.shape
	c = c.reshape([-1])
	ind = c.argsort()[-2:][::-1]
	for aaa in ind:
		i = aaa//col
		j = aaa%col 
		x = int(b[i][j][0])+j*multip+multip//2
		y = int(b[i][j][1])+i*multip+multip//2
		w = int(b[i][j][2])
		h = int(b[i][j][3])
		try:
			M = np.float32([[1,0,-(x-int(w*1.5)//2)],[0,1,-(y-int(h*1.5)//2)]])
			cropped = cv2.warpAffine(img,M,(int(w*1.5),int(h*1.5)))
			cropped = cv2.resize(cropped,(32,32))
			# append [cropped_image,[x,y,w,h]] to result list
			res.append([cropped,[x,y,w,h]])
		except:
			continue
	return res 

def crop(img,bs,cs):
	# triple scales
	multi = [8,32,128]
	res = []
	for i in range(len(bs)):
		# the elements in res are [cropped_imgs, coordinates]
		buff = get_img_coord(img,cs[i],bs[i],multi[i])
		res += buff
	return res

def filter_valid_coord(coords,veri_result,scrs):
	threshold = 0.5
	res = []
	scr_res = []
	for i in range(len(coords)):
		# if the verification result is 1, then append to result. 
		# filter both the coordination and scores for further non_max_suppresion
		if scrs[i]>=threshold:
			res.append(coords[i])
			scr_res.append(scrs[i])
	return res,scr_res

def get_iou(inp1,inp2):
	x1,y1,w1,h1 = inp1[0],inp1[1],inp1[2],inp1[3]
	x2,y2,w2,h2 = inp2[0],inp2[1],inp2[2],inp2[3]
	#print y1,y2,h1,h2
	xo = min(abs(x1+w1/2-x2+w2/2), abs(x1-w1/2-x2-w2/2))
	yo = min(abs(y1+h1/2-y2+h2/2), abs(y1-h1/2-y2-h2/2))
	if abs(x1-x2) > (w1+w2)/2 or abs(y1-y2) > (h1+h2)/2:
		return 0
	if abs(float((x1-x2)*2)) < abs(w1-w2):
		xo = min(w1, w2)
	if abs(float((y1-y2)*2)) < abs(h1-h2):
		yo = min(h1, h2)
	overlap = xo*yo
	total = w1*h1+w2*h2-overlap
	#print 'ovlp',overlap
	#print 'ttl',total
	return float(overlap)/total

def non_max_sup(coords,scr):
	# recursively get the max score in open list and delete the overlapped areas which is more than threshold
	non_max_thresh = 0.05
	open_coords = list(coords)
	open_scr = list(scr)
	result_coords = []
	
	while len(open_scr)>0:
		max_ind = np.argmax(np.array(open_scr))
		max_coord = open_coords[max_ind]
		result_coords.append(max_coord)
		del open_coords[max_ind]
		del open_scr[max_ind]
		#print len(open_scr)
		for i in range(len(open_scr),0,-1):
			iou = get_iou(open_coords[i-1],max_coord)
			#print iou
			if iou>non_max_thresh:
				del open_coords[i-1]
				del open_scr[i-1]
	return result_coords

def draw(img,coords):
	buff_img = img.copy()
	for i in coords:
		x,y,w,h = i
		cv2.rectangle(buff_img,(x-w//2,y-h//2),(x+w//2,y+h//2),(0,255,0),2)
	cv2.imshow('result',buff_img)
	cv2.waitKey(1)

# set output

b0,b1,b2,c0,c1,c2 = netpart.model_out

B0,B1,C0,C1 = netpart_s.model_out

# set and load session
config = tf.ConfigProto(allow_soft_placement=True)
config.gpu_options.allow_growth = True
sess = tf.Session(config=config)
v1 = M.get_all_vars('VERI') + M.get_all_vars('MSRPN_v3')
v2 = M.get_all_vars('VERI_s') + M.get_all_vars('MSRPN_v3_s')
v1 = [item for item in v1 if item not in v2]
M.loadSess('./modelveri_tiny/',sess,var_list=v1)
M.loadSess('./modelveri_tiny_s/',sess,var_list=v2)

import time 

def get_coord_from_detection(img):
	#t1 = time.time()
	buff_out = sess.run([b0,b1,b2,c0,c1,c2],feed_dict={netpart.inpholder:[img]})
	bs,cs = buff_out[:3],buff_out[3:]
	#t2 = time.time()
	res = crop(img,bs,cs)
	#t3 = time.time()
	cropped_imgs = [k[0] for k in res]
	coords = [k[1] for k in res]

	# get score and output
	veri_output = sess.run(net_veri.output,feed_dict={net_veri.inputholder:cropped_imgs})
	veri_classi = np.argmax(veri_output,1)
	#t4 = time.time()
	# ------
	# If nonmax supression is not needed, just remove the softmax computation
	# ------
	#veri_output = np.exp(veri_output-100)
	#veri_output = veri_output/np.sum(veri_output,axis=1,keepdims=True)
	veri_output = veri_output[:,1]

	valid_coord,veri_output = filter_valid_coord(coords,veri_classi,veri_output)
	valid_coord = non_max_sup(valid_coord,veri_output)
	
	return valid_coord

def get_coord_from_detection_small(img):
	#t1 = time.time()
	buff_out = sess.run([B0,B1,C0,C1],feed_dict={netpart_s.inpholder:[img]})
	bs,cs = buff_out[:2],buff_out[2:]
	#t2 = time.time()
	res = crop(img,bs,cs)
	#t3 = time.time()
	cropped_imgs = [k[0] for k in res]
	coords = [k[1] for k in res]

	# get score and output
	veri_output = sess.run(net_veri_s.output,feed_dict={net_veri_s.inputholder:cropped_imgs})
	veri_classi = np.argmax(veri_output,1)
	#t4 = time.time()
	# ------
	# If nonmax supression is not needed, just remove the softmax computation
	# ------
	#veri_output = np.exp(veri_output-100)
	#veri_output = veri_output/np.sum(veri_output,axis=1,keepdims=True)
	veri_output = veri_output[:,1]

	valid_coord,veri_output = filter_valid_coord(coords,veri_classi,veri_output)
	valid_coord = non_max_sup(valid_coord,veri_output)
	
	return valid_coord

if __name__=='__main__':
	img = np.random.random([400,400,3])
	get_coord_from_detection(img)
	get_coord_from_detection_small(img)