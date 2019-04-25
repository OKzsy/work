
# -*- coding: utf-8 -*-
"""
Created on Thu May 24 11:29:04 2018

@author: 01
"""

import os
import cv2 as cv
import numpy as np


#三角形相似性准则
def Similarity_of_triangle(index1,index2):
    similar=[]
    for i in range(index1.shape[0]):
        a=0
        for j in range(index1.shape[0]):
            if j!=i and j!=index1.shape[0]-1:
                for k in range(j+1,index1.shape[0]):
                    
                    L12=np.linalg.norm(index1[j]-index1[i])
                    L13=np.linalg.norm(index1[k]-index1[i])
                    L23=np.linalg.norm(index1[k]-index1[j])
                    p1=(L12+L13+L23)/2
                    S1=np.sqrt(p1*(p1-L12)*(p1-L13)*(p1-L23))
    
                    l12=np.linalg.norm(index2[j]-index2[i])
                    l13=np.linalg.norm(index2[k]-index2[i])
                    l23=np.linalg.norm(index2[k]-index2[j])
                    p2=(l12+l13+l23)/2
                    S2=np.sqrt(p2*(p2-l12)*(p2-l13)*(p2-l23))
                    #value=(1-L12/(l12*np.sqrt(S1/S2)))**2+(1-L13/(l13*np.sqrt(S1/S2)))**2+(1-L23/(l23*np.sqrt(S1/S2)))**2
                    value=(1-(L12/l12))**2+(1-(L13/l13))**2+(1-(L23/l23))**2
                    if S1<0.1 and S2<0.1:
                        a=1
                        break
                    else:
                        #print(i,j,k,p1,L12,L13,L23)
                        if value<0.1:
                            similar.append(i)
                            a=1
                            break
            if a==1:
                break
    return similar    
    
def main(in_path,out_path):
    file_list = os.listdir(in_path)
    for i in range(len(file_list)):
        in_file=os.path.join(in_path,file_list[i])

        data=np.loadtxt(in_file,delimiter=',')
        
        #print(data.shape)
        
        if len(data.shape)>1 and data.shape[0]>3:
            
            pts1=data[:,2]
            pts2=data[:,2:4]
            
            similar=Similarity_of_triangle(pts1,pts2)
            print(similar)
            if len(similar)>0:
                data=data[similar]
                out_file=os.path.join(out_path,file_list[i])
                np.savetxt(out_file,data,delimiter=',') 
        else:
            out_file=os.path.join(out_path,file_list[i])
            np.savetxt(out_file,data,delimiter=',') 
            
        
if __name__ == '__main__':

    # in_path=r"E:\remote_sensing_data\no_sampling\equ\patch_result\bi_match_trans"
    #
    # out_path=r"E:\remote_sensing_data\no_sampling\equ\patch_result\bi_match_trans_similar"
    # main(in_path,out_path)

    if len(sys.argv[1:]) < 2:
        sys.exit('Problem reading input')
    main(sys.argv[1], sys.argv[2])
     