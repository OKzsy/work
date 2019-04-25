
# -*- coding: utf-8 -*-
"""
Created on Mon May 28 18:05:28 2018

@author: 01
"""
#待配准影像与基准影像平移量的限制
import os
import numpy as np
def Calulate_matchpoint_translation(pts1,pts2,):
    trans_small_index=[]
    if len(pts1.shape)==1:
        sub12=np.abs(pts1-pts2)
        if sub12.max()<10:
            trans_small_index.append(0)
    else:
        for i in range(pts1.shape[0]):
            sub12=np.abs(pts1[i]-pts2[i])
            if sub12.max()<10:
                trans_small_index.append(i)
    return trans_small_index
    


def main(in_path,out_path):
    file_list = os.listdir(in_path)
    for i in range(len(file_list)):
        in_file=os.path.join(in_path,file_list[i])
        
        
        data=np.loadtxt(in_file,delimiter=',')
        if len(data.shape)==1:
            print(data)
            
            pts1=data[:2]
            pts2=data[2:4]
        else:
            pts1=data[:,:2]
            pts2=data[:,2:4]
        #print(data.shape)
        trans_small_index=Calulate_matchpoint_translation(pts1,pts2)
        print(trans_small_index)
            
        
        if len(trans_small_index)>0:
                print(trans_small_index)
                if len(data.shape)>1:
                    
                    data=data[trans_small_index]
                    print(data.shape)
                out_file=os.path.join(out_path,file_list[i])
                np.savetxt(out_file,data,delimiter=',') 
        


if __name__ == '__main__':
    
    # in_path=r"E:\remote_sensing_data\no_sampling\equ\patch_result\bi_match"
    # out_path=r"E:\remote_sensing_data\no_sampling\equ\patch_result\bi_match_trans"
    # main(in_path,out_path)
    if len(sys.argv[1:]) < 2:
        sys.exit('Problem reading input')
    main(sys.argv[1], sys.argv[2])








    
