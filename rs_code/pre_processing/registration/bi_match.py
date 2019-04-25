# -*- coding: utf-8 -*-
"""
Created on Thu May 24 11:29:04 2018

@author: 01
"""
#说明：使用sift进行特征点和描述子的提取，并使用欧式距离比值进行双向匹配，得到初始的匹配点对




import cv2 as cv
import numpy as np

# Initiate SIFT detector
def Bi_match(img1,img2):
    sift = cv.xfeatures2d.SIFT_create()
    #sift = cv.KAZE_create()
    # find the keypoints and descriptors with SIFT
    #使用sift提取特征点和描述子
    kp1, des1 = sift.detectAndCompute(img1,None)
    kp2, des2 = sift.detectAndCompute(img2,None)
 #BFMatcher with default params
    bf = cv.BFMatcher()
    matches = bf.knnMatch(des1,des2, k=2)
    matches1 = bf.knnMatch(des2,des1, k=2)
#for i in range(len(matches)):
#    matches[i]=matches[i][:2]
# Apply ratio test
    #正向匹配
    good = []
    pts1=[]
    pts2=[]
    ratio=[]
    for m,n in matches:
        if m.distance < 0.7*n.distance:
            good.append([m])
            ratio.append(m.distance/n.distance)
            pts2.append(kp2[m.trainIdx].pt)
            pts1.append(kp1[m.queryIdx].pt) 
    pts1=np.float32(pts1) 
    pts2=np.float32(pts2)
    pts=np.hstack((pts1,pts2))
    #逆向匹配
    good1 = []
    pts1_i=[]
    pts2_i=[]
    ratio1=[]
    for m,n in matches1:
        if m.distance < 0.7*n.distance:
            ratio1.append(m.distance/n.distance)
            good1.append([m]) 
            pts1_i.append(kp1[m.trainIdx].pt)
            pts2_i.append(kp2[m.queryIdx].pt)
    pts1_i=np.float32(pts1_i) 
    pts2_i=np.float32(pts2_i)
    pts_i=np.hstack((pts1_i,pts2_i))
    #进行双向匹配判断
    a=0
    pts_bi=[]
    ratio_bi=[]
    for i in range(pts.shape[0]):
        for j in range(pts_i.shape[0]):
            if pts[i][0]==pts_i[j][0] and pts[i][1]==pts_i[j][1] \
                    and pts[i][2]==pts_i[j][2] and pts[i][3]==pts_i[j][3]:
                a+=1
                pts_bi.append(pts[i])
                ratio_bi.append([ratio[i],ratio1[j]])
                print(i,j)
                print('yes')
    pts_bi=np.array(pts_bi)
    return pts_bi,kp1,kp2,ratio_bi
    
    
def main(in_file1,in_file2,out_file):
    img1 = cv.imread(in_file1, 0)  # queryImage
    img2 = cv.imread(in_file2, 0)  # trainImage
    pts_bi,kp1,kp2,ratio_bi=Bi_match(img1,img2)
    #保存双向匹配点对和欧式距离比值
    data=np.c_[pts_bi,ratio_bi]
    np.savetxt(out_file,data,delimiter=',')

if __name__ == "__main__":
    start_time = time.time()
    # in_file1 = r"D:\work\project\image_registration\test\test7.5\1\1.tif"  # 参数1
    # in_file2 = r"D:\work\project\image_registration\test\test7.5\1\2_new.tif"  # 参数2
    # out_file = r"D:\work\project\image_registration\test\test7.5\1\bi_match_points.csv"  # 参数3
    # main(in_file1,in_gile2,in_file3)

    if len(sys.argv[1:]) < 3:
        sys.exit('Problem reading input')
    main(sys.argv[1], sys.argv[2], sys.argv[3])

    end_time = time.time()
    print( "time: %.2f min." % ((end_time - start_time) / 60))
