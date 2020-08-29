import cgini
import cunique
import numpy as np
import time


class node:
    """
    cart树的节点类
    """

    def __init__(self, fea=-1, value=None, results=None, right=None, left=None):
        # 用于切分数据集属性的索引
        self.fea = fea
        # 设置划分的值
        self.value = value
        # 存储叶节点所属的类别
        self.results = results
        # 右子树
        self.right = right
        # 左子树
        self.left = left


def build_tree(data):
    """
    构建cart树
    :param data: numpy array 训练样本
    :return: 树的根节点
    """
    # 构建决策树，函数返回该决策树的根节点
    if data.shape[0] == 0:
        return node()
    # 计算当前的gini指数
    currentgini = cgini.cal_gini_index(data[:, -1])
    # 如果对数据集的划分结果达到要求直接返回结果
    if currentgini == 0:
        return node(results=cunique.funique(data[:, -1]))
    bestgini = 0.0
    # 最佳切分属性以及最佳切分点
    bestcriteria = None
    # 存储切分后的两个数据集
    bestsets = None
    # 样本中的可用特征个数
    feature_num = data.shape[1] - 1
    # 寻找最好的切分属性和切分点
    for fea in range(feature_num):
        # 获取所在fea特征所有可能取得的值
        tmp_feature = data[:, fea]
        feature_values = cunique.funique(tmp_feature)
        # 对每一个可能的值进行数据集划分，并计算gini指数
        for value in feature_values[0]:
            # 根据fea特征中的值将数据集划分为左右子树
            index1 = np.where(tmp_feature >= value)
            size1 = index1[0].size
            set1 = data[index1[0], :]
            index2 = np.where(tmp_feature < value)
            size2 = index2[0].size
            set2 = data[index2[0], :]
            # 计算拆分后的gini指数
            nowgini = (size1 * cgini.cal_gini_index(set1[:, -1]) + size2 * cgini.cal_gini_index(set2[:, -1])) / \
                      data.shape[0]
            # 计算gini指数增加量
            gain = currentgini - nowgini
            # 判断此划分是否比当前划分更好
            if gain > bestgini and size1 > 0 and size2 > 0:
                bestgini = gain
                bestcriteria = (fea, value)
                bestsets = (set1, set2)
    # 判断划分是否结束
    if bestgini > 0:
        right = build_tree(bestsets[0])
        left = build_tree(bestsets[1])
        return node(fea=bestcriteria[0], value=bestcriteria[1], right=right, left=left)
    else:
        # 返回当前的类别标签作为最终的类别标签
        return node(results=cunique.funique(data[:, -1]))
def main(sample_file):
    # 导入数据
    print("--------------------load data---------------------")
    data_train = np.loadtxt(sample_file, delimiter=',', dtype=np.int16)

    tree = build_tree(data_train)
    print('end')
    return None

if __name__ == '__main__':
    start_time = time.time()
    samplefile = r"F:\test_data\dengfeng\newsample.csv"

    main(samplefile)
    end_time = time.time()
    print("time: %.4f secs." % (end_time - start_time))
