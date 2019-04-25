
# -*- coding: utf-8 -*-
"""
Created on Sat Jul  7 14:39:08 2018

@author: 01
"""

import sys
import time
import random
import numpy  as np
import numba as nb
import matplotlib.pyplot as plt
import cv2 as cv 
try:
    from osgeo import gdal
except ImportError:
    import gdal

def ransac(data,N,r):
    pts1=data[:,:2]
    pts2=data[:,2:4]
    #N迭代次数
    n=0
    Matrix=np.zeros((2,3))
    for i in range(N):
        y=list(range(pts1.shape[0]))
        slice = random.sample(y, 3)
           
        p1 = np.float32(pts1[slice])
        p2 = np.float32(pts2[slice])
        M = cv.getAffineTransform(p2,p1)
        
        one=np.ones((pts1.shape[0],1))
        pts2_one=np.c_[pts2,one]
        pts2_t=[]
        for j in range(pts1.shape[0]):
            pts2_t.append(np.dot(M,pts2_one[j]))
        pts2_t=np.array(pts2_t)
        indx=np.where(np.linalg.norm(pts2_t-pts1,axis=1)<r)[0]
        Rmse=np.sqrt(np.sum(np.square(pts2_t[indx]-pts1[indx]))/pts1[indx].shape[0])
        if np.where(np.linalg.norm(pts2_t-pts1,axis=1)<r)[0].shape[0]>n:
            
            n=np.where(np.linalg.norm(pts2_t-pts1,axis=1)<r)[0].shape[0]
            
            Matrix=M
            #print(M)
            index=np.where(np.linalg.norm(pts2_t-pts1,axis=1)<r)[0]
            rmse=Rmse
            print(i,n,index.shape,Rmse,rmse)
        elif np.where(np.linalg.norm(pts2_t-pts1,axis=1)<r)[0].shape[0]==n:
            
            if Rmse<rmse:
                n=np.where(np.linalg.norm(pts2_t-pts1,axis=1)<r)[0].shape[0]
            
                Matrix=M
                #print(M)
                index=np.where(np.linalg.norm(pts2_t-pts1,axis=1)<r)[0]
                rmse=Rmse
                print(i,n,index.shape,Rmse,rmse)
    print(n)
    print(index.shape)
    return data[index],M  
def main(in_file,out_file,r):
    N = 1000
    data = np.loadtxt(in_file, delimiter=',')
    data = data[:, :4]
    data1, M = ransac(data, N, r)
    np.savetxt(out_file, data1)
    print(M)
if __name__ == "__main__":
    start_time = time.time()
    # in_file=r"D:\work\project\image_registration\test\test7.5\bi_match_t.csv" #参数1
    # out_file=r"D:\work\project\image_registration\test\test7.5\bi_match_t_ransac.csv"#参数2
    # r=1
    # main(in_file,out_file,r)
    if len(sys.argv[1:]) < 3:
        sys.exit('Problem reading input')
    main(sys.argv[1], sys.argv[2], sys.argv[3])
    end_time = time.time()
    print( "time: %.2f min." % ((end_time - start_time) / 60))
    
