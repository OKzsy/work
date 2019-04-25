import numpy as np
#计算互相关系数
def Correlation(img1,img2,pt1,pt2,size): #img1img2分别参数1，参数2,pts1,pts2为参数3，size为参数4
    x1,y1=pt1
    x2,y2=pt2
    roi1=img1[x1-int(size/2):x1+int(size/2)+1,y1-int(size/2):y1+int(size/2)+1]
    roi2=img2[x2-int(size/2):x2+int(size/2)+1,y2-int(size/2):y2+int(size/2)+1]
    E1=np.mean(roi1)
    E2=np.mean(roi2)

    top=np.sum((roi1-E1)*(roi2-E2))
    bottom=np.sqrt(np.sum(np.square(roi1-E1))*np.sum(np.square(roi2-E2)))
    rho=np.abs(top/bottom)
    return rho #参数5
