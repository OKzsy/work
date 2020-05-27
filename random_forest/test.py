import random, os, time, json
from numpy import *
import numpy as np
import pandas as pd
import multiprocessing, threading

from sklearn.externals.joblib import Parallel, delayed

'''
Author: ZTao-z
Time: 2019/06/30
'''

'''
dataset为matrix，且最后一列为label

算法流程：
# 随机筛选N个样本
# 随机抽取M个特征
# 遍历N个样本上的特征m，找到最优分割阈值，分割成两堆
    记录此特征及阈值
    若满足分裂条件：
        生成此结点的左右子节点，左节点小于该阈值，右节点大于该阈值
        将数据分成两堆，分别保存到左右节点
    否则：
        终止分裂
'''


class CART_tree:
    def __init__(self):
        # data为样本序号
        self.min_leaf_size = 100
        self.varThres = 0

    # 划分数据集
    def datasetSplit(self, dataset, feaNum, thres):
        dataL = dataset[nonzero(dataset[:, feaNum] < thres)[0], :]
        dataR = dataset[nonzero(dataset[:, feaNum] >= thres)[0], :]
        return dataL, dataR

    # 计算总的方差
    def getAllVar(self, dataset):
        return var(dataset[:, -1]) * shape(dataset)[0]

    def findFeatureAndThresParallel(self, feature, dataset):
        # 样本子集根据特征进行排序
        m = shape(dataset)[0]
        dataset_t = dataset[np.lexsort(dataset[:, feature].T)]
        # 分割阈值列表
        thresList = np.array(dataset_t[0][:, feature].T.tolist()[0])
        # 累加y标签和y^2标签
        sum_List = np.array(np.cumsum(dataset_t[0][:, -1]).tolist()[0])
        sq_sum_List = np.array(np.cumsum(np.square(dataset_t[0][:, -1])).tolist()[0])
        # 获取标签总和
        sum = sum_List[-1]
        sq_sum = sq_sum_List[-1]
        # 分割阈值去重
        new_thresList, index = np.unique(thresList, return_index=True)
        # 计算分割后数据集的大小N1，N2
        left_size = index
        right_size = m - left_size
        # 计算N1的y总和以及y^2总和
        left_sum = sum_List[left_size - 1]
        left_sq_sum = sq_sum_List[left_size - 1]
        # 计算N2的y总和以及y^2总和
        right_sum = sum - left_sum
        right_sq_sum = sq_sum - left_sq_sum
        # 防止0做除数
        left_size[0] = 1
        # 计算N1和N2的方差
        var_left = left_sq_sum / left_size - np.square(left_sum / left_size)
        var_right = right_sq_sum / right_size - np.square(right_sum / right_size)
        # 计算MSE
        total_lost = var_left * left_size + var_right * right_size
        # 计算最小MSE及其对应分割阈值
        if shape(thresList)[0] <= 2 * self.min_leaf_size:
            return
        l = index >= self.min_leaf_size
        r = index < m - self.min_leaf_size
        listRange = nonzero(l & r)[0]
        if shape(listRange)[0] == 0:
            return
        index = np.argmin(total_lost[listRange], axis=0)
        if total_lost[listRange[0] + index] < self.lowError:
            self.lowError = total_lost[listRange[0] + index]
            self.bestFeature = feature
            self.bestThres = new_thresList[listRange[0] + index]

    def chooseBestFeature(self, dataset, featureList, max_depth):
        # 停止条件 1：标签相同
        if len(set(dataset[:, -1].T.tolist()[0])) == 1 or max_depth == 0:
            regLeaf = mean(dataset[:, -1])
            return None, regLeaf

            # 停止条件 2：已完成所有标签分类
        if len(featureList) == 1:
            regLeaf = mean(dataset[:, -1])
            return None, regLeaf

        m, n = shape(dataset)
        totalVar = self.getAllVar(dataset)
        self.bestFeature = -1
        self.bestThres = float('-inf')
        self.lowError = inf

        # 遍历剩余划分特征 i
        for feature in featureList:
            self.findFeatureAndThresParallel(feature, dataset)

        # 停止条件3：划分后方差更大，则取消划分
        if totalVar - self.lowError < self.varThres:
            return None, mean(dataset[:, -1])

        # 停止条件4：划分后数据集太小
        dataL, dataR = self.datasetSplit(dataset, self.bestFeature, self.bestThres)
        if shape(dataL)[0] < self.min_leaf_size or shape(dataR)[0] < self.min_leaf_size:
            return None, mean(dataset[:, -1])

        # 成功则返回最佳特征和最小方差
        return self.bestFeature, self.bestThres

    # dataset: 数据集, featureList: 随机特征
    def createTree(self, dataset, max_depth=100):
        m, n = shape(dataset)
        featureList = list(range(n - 1))
        bestFeat, bestThres = self.chooseBestFeature(dataset, featureList, max_depth)  # 最耗时

        if bestFeat == None:
            return bestThres
        regTree = {}
        # 记录此特征及阈值
        regTree['spliteIndex'] = bestFeat
        regTree['spliteValue'] = bestThres
        # 划分数据集
        dataL, dataR = self.datasetSplit(dataset, bestFeat, bestThres)
        regTree['left'] = self.createTree(dataL, max_depth - 1)
        regTree['right'] = self.createTree(dataR, max_depth - 1)
        return regTree

    def isTree(self, tree):
        return type(tree).__name__ == 'dict'

    def predict(self, tree, testData):
        if not self.isTree(tree):
            return float(tree)
        if testData[tree['spliteIndex']] < tree['spliteValue']:
            if not self.isTree(tree['left']):
                return float(tree['left'])
            else:
                return self.predict(tree['left'], testData)
        else:
            if not self.isTree(tree['right']):
                return float(tree['right'])
            else:
                return self.predict(tree['right'], testData)


class RandomForest:
    def __init__(self, n):
        self.treeNum = n
        self.treeList = []
        self.ct = CART_tree()
        self.n_jobs = 1

    def fit(self, dataset, jobs=1):
        m, n = shape(dataset)
        self.n_jobs = jobs
        pool = multiprocessing.Pool(processes=self.n_jobs)
        for i in range(self.treeNum):
            # 有放回采样
            # data_t = np.random.choice(range(m), 2000000).tolist()
            data_t = list(range(2000000))
            random_dataset = dataset[data_t, :]
            tt = createTreeThread(random_dataset, i)
            self.treeList.append(pool.apply_async(tt.run))
        pool.close()
        pool.join()
        for treeNum in range(len(self.treeList)):
            self.treeList[treeNum] = self.treeList[treeNum].get()

    def writeToFile(self, tree):
        if not os.path.exists("./model"):
            os.mkdir("./model")
        with open("./model/tree1.json", "w") as f:
            json.dump(tree, f)

    def loadFromFile(self):
        for root, dirs, files in os.walk("./model"):
            for file in files:
                with open(file, "r") as f:
                    for line in f.readlines():
                        self.treeList.append(json.loads(line))

    def predict(self, testData):
        result = []
        for i in range(len(testData)):
            res = []
            for tree in self.treeList:
                res.append(self.ct.predict(tree, testData[i]))
            result.append(res)

        return np.matrix(result).mean(1).T.tolist()

    def predictParell(self, testData):
        result = []
        pool = multiprocessing.Pool(processes=self.n_jobs)
        for tree in self.treeList:
            tt = predictTreeThread(tree, testData)
            result.append(pool.apply_async(tt.run))
        pool.close()
        pool.join()
        for i in range(len(result)):
            result[i] = result[i].get()
        return np.matrix(result).mean(0).tolist()

    def saveModel(self):
        self.writeToFile(self.treeList)


class createTreeThread:
    def __init__(self, dataset, number=0):
        self.data = dataset
        self.ct = CART_tree()
        self.n = number

    def run(self):
        begin = time.time()
        self.tree = self.ct.createTree(self.data)
        end = time.time()
        print("Tree", self.n, " Finish in :", end - begin)
        return self.tree


class predictTreeThread:
    def __init__(self, tree, testData):
        self.ct = CART_tree()
        self.tree = tree
        self.datas = testData

    def run(self):
        self.datas = np.matrix(self.datas)
        index = np.array(range(shape(self.datas)[0]))
        self.result = np.array([0.0] * shape(self.datas)[0])
        self.predict_v2(self.tree, index)
        return self.result.tolist()

    def predict_v2(self, tree, index):
        if not self.ct.isTree(tree):
            self.result[index] = float(tree)
            return
        temp_index_smaller = nonzero(self.datas[index, tree['spliteIndex']] < tree['spliteValue'])[0]
        temp_index_bigger = nonzero(self.datas[index, tree['spliteIndex']] >= tree['spliteValue'])[0]
        if shape(temp_index_smaller)[0] > 0:
            self.predict_v2(tree['left'], index[temp_index_smaller])
        if shape(temp_index_bigger)[0] > 0:
            self.predict_v2(tree['right'], index[temp_index_bigger])


def readDataset():
    trainSet = []
    labelSet = []
    for i in range(1, 6):
        trainData = pd.read_csv(os.path.join('data/', 'train{}.csv'.format(i)), header=None, \
                                delimiter="\t", quoting=3)
        labelData = pd.read_csv(os.path.join('data/', 'label{}.csv'.format(i)), header=None, \
                                delimiter="\t", quoting=3)
        for example in list(trainData[0]):
            cur_example = example.strip().split(',')
            fin_example = map(float, cur_example)
            trainSet.append(list(fin_example))
        for label in list(labelData[0]):
            labelSet.append(float(label))

    tS_matrix = np.matrix(trainSet)
    tL_matrix = np.matrix(labelSet)
    final_trainSet = np.insert(tS_matrix, 13, values=tL_matrix, axis=1)

    return final_trainSet


def readTestData():
    testSet = []
    for i in range(1, 7):
        testData = pd.read_csv(os.path.join('data/', 'test{}.csv'.format(i)), header=None, \
                               delimiter="\t", quoting=3)
        for example in list(testData[0]):
            cur_example = example.strip().split(',')
            fin_example = map(float, cur_example)
            testSet.append(list(fin_example))

    return testSet


def R2Loss(y_test, y_true):
    return 1 - (np.sum(np.square(y_test - y_true))) / (np.sum(np.square(y_true - np.mean(y_true))))


if __name__ == "__main__":
    print("read dataset")
    trainData = readDataset()

    print("begin generate forest")
    rf = RandomForest(1)
    rf.fit(trainData, jobs=1)

    print("begin predict")
    begin = time.time()
    result = rf.predictParell(trainData.tolist())
    end = time.time()
    print("Predict use:", end - begin, "second")

    print("R2 Loss:", R2Loss(np.array(result[0]), np.array(trainData[:, -1].T.tolist()[0])))
    '''
    begin = time.time()
    test = readTestData()
    result = rf.predictParell(test)
    end = time.time()
    print("Predict use:", end-begin,"second")
    '''
    '''
    r = list(range(1,len(test)+1))
    output = pd.DataFrame( data={"id": r, "Predicted":result[0]} )
    # Use pandas to write the comma-separated output file
    output.to_csv(os.path.join(os.path.dirname(__file__), 'data', 'result_my_1.csv'), index=False, quoting=3)

    rf.saveModel()
    '''
