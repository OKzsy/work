#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
Optimized Random Forest based on the original program.
模型选择逻辑
明确主要指标
    Micro-F1：综合衡量分类性能，尤其是类别不平衡时很有用。
    Accuracy：整体正确率。
    Kappa：考虑随机正确率后的校正一致性指标。
如果你的数据类别分布不平衡，Micro-F1往往比Accuracy更可靠。
优先级选择策略
一般做法：
    首先根据 Micro-F1 排序，选最大的。
    如果 Micro-F1 相同或差别很小（如 0.0001 以内），再比较 Kappa，选更高的。
    Accuracy 可作为参考，但不要是唯一标准。

组合指标加权
    如果希望综合考虑：
    score=w1*Micro-F1+w2*Accuracy+w3*Kappa
    比如：w1=0.5, w2=0.3, w3=0.2，然后选 score 最高的模型。
"""

import os
import time
import math
import pickle
import numpy as np
import numba as nb
import multiprocessing as mp

from osgeo import gdal, ogr, osr, gdalconst

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


# ============================================================
# progress bar
# ============================================================


class Bar:
    """用于多线程显示进度条"""

    members = 0

    def __init__(self, total):
        self.total = total

    def update(self):
        Bar.members += 1
        progress(Bar.members / self.total)

    def shutdown(self):
        Bar.members = 0


# ============================================================
# shared memory globals
# ============================================================

global_train_share = global_label_share = None
DATA_SHAPE = LABEL_SHAPE = None
DATA_DTYPE = LABEL_DTYPE = None
global_predict_share = predict_SHAPE = predict_DTYPE = None


def init_pool_train(
    data_share, label_share, data_shape, label_shape, data_dtype, label_dtype
):
    global global_train_share, global_label_share
    global DATA_SHAPE, LABEL_SHAPE
    global DATA_DTYPE, LABEL_DTYPE

    global_train_share = data_share
    global_label_share = label_share
    DATA_SHAPE = data_shape
    LABEL_SHAPE = label_shape
    DATA_DTYPE = data_dtype
    LABEL_DTYPE = label_dtype


# ============================================================
# numba helpers
# ============================================================


@nb.njit(cache=True)
def cal_gini_hist(hist, total):
    if total <= 0:
        return 0.0
    gini = 1.0
    inv_total = 1.0 / total
    for i in range(hist.shape[0]):
        if hist[i] > 0:
            p = hist[i] * inv_total
            gini -= p * p
    return gini


@nb.njit(cache=True)
def label_stat_by_index(labels, sample_index):
    """
    统计 sample_index 对应样本的标签分布。
    支持负标签。
    """
    n = sample_index.shape[0]
    first_label = labels[sample_index[0]]
    min_label = first_label
    max_label = first_label

    for i in range(n):
        lbl = labels[sample_index[i]]
        if lbl < min_label:
            min_label = lbl
        if lbl > max_label:
            max_label = lbl

    hist_size = max_label - min_label + 1
    hist = np.zeros(hist_size, dtype=np.int32)
    for i in range(n):
        lbl = labels[sample_index[i]]
        hist[lbl - min_label] += 1

    used = 0
    for i in range(hist_size):
        if hist[i] > 0:
            used += 1

    label_arr = np.empty(used, dtype=np.int32)
    count_arr = np.empty(used, dtype=np.int32)
    p = 0
    for i in range(hist_size):
        if hist[i] > 0:
            label_arr[p] = i + min_label
            count_arr[p] = hist[i]
            p += 1

    return label_arr, count_arr, hist, min_label


# def best_split_sorted_scan(
#     data, labels, sample_index, feature_ids, total_hist, min_label
# ):
#     """
#     在当前节点内，从随机特征 feature_ids 中寻找最佳 Gini 划分。
#     使用排序扫描，向量化实现。
#     """
#     n = sample_index.shape[0]
#     class_num = total_hist.shape[0]
#     base_gini = cal_gini_hist(total_hist, n)

#     best_gain = 0.0
#     best_feature = -1
#     best_threshold = 0.0

#     # Ensure contiguous
#     data_c = np.ascontiguousarray(data)
#     labels_c = np.ascontiguousarray(labels)
#     sample_index = np.asarray(sample_index, dtype=np.intp)

#     for f_idx, fea in enumerate(feature_ids):
#         # === 关键修改：向量化取列 ===
#         feat_values = data_c[sample_index, fea].astype(np.float64)

#         order = np.argsort(feat_values)
#         sorted_feat = feat_values[order]

#         # 对应标签
#         labels_in_node = labels_c[sample_index]
#         hidx_all = labels_in_node - min_label  # shape (n,)

#         left_hist = np.zeros(class_num, dtype=np.int32)
#         right_hist = total_hist.copy()
#         left_n = 0
#         right_n = n

#         # === 向量化扫描 ===
#         # 遍历排序后的样本（0 ~ n-2），因为阈值在 i 和 i+1 之间
#         for i in range(n - 1):
#             # 获取 sampled label for i-th sorted sample
#             hidx = hidx_all[order[i]]
#             left_hist[hidx] += 1
#             right_hist[hidx] -= 1
#             left_n += 1
#             right_n -= 1

#             # 相同特征值跳过
#             if sorted_feat[i] == sorted_feat[i + 1]:
#                 continue

#             gl = cal_gini_hist(left_hist, left_n)
#             gr = cal_gini_hist(right_hist, right_n)
#             weighted_gini = (left_n * gl + right_n * gr) / n
#             gain = base_gini - weighted_gini

#             if gain > best_gain:
#                 best_gain = gain
#                 best_feature = fea
#                 best_threshold = (sorted_feat[i] + sorted_feat[i + 1]) * 0.5

#     return best_gain, best_feature, best_threshold


@nb.njit(cache=True)
def best_split_sorted_scan(
    data, labels, sample_index, feature_ids, total_hist, min_label
):
    """
    在当前节点内，从随机特征 feature_ids 中寻找最佳 Gini 划分。
    使用排序扫描，不再为每个候选阈值复制左右子集。

    返回：best_gain, best_feature, best_threshold
    """
    n = sample_index.shape[0]
    class_num = total_hist.shape[0]
    base_gini = cal_gini_hist(total_hist, n)

    best_gain = 0.0
    best_feature = -1
    best_threshold = 0.0

    for f_idx in range(feature_ids.shape[0]):
        fea = feature_ids[f_idx]

        feat_values = np.empty(n, dtype=np.float64)
        for i in range(n):
            feat_values[i] = data[sample_index[i], fea]

        order = np.argsort(feat_values)
        sorted_feat = feat_values[order]
        sample_index_sorted = sample_index[order]

        left_hist = np.zeros(class_num, dtype=np.int32)
        right_hist = total_hist.copy()
        left_n = 0
        right_n = n

        for i in range(n - 1):
            sid = sample_index_sorted[i]
            lbl = labels[sid]
            hidx = lbl - min_label

            left_hist[hidx] += 1
            right_hist[hidx] -= 1
            left_n += 1
            right_n -= 1

            # 相同特征值不能形成有效新阈值
            if sorted_feat[i] == sorted_feat[i + 1]:
                continue

            gl = cal_gini_hist(left_hist, left_n)
            gr = cal_gini_hist(right_hist, right_n)
            weighted_gini = (left_n * gl + right_n * gr) / n
            gain = base_gini - weighted_gini

            if gain > best_gain:
                best_gain = gain
                best_feature = fea
                # 标准 CART 连续特征阈值：相邻不同值中点
                best_threshold = (sorted_feat[i] + sorted_feat[i + 1]) * 0.5

    return best_gain, best_feature, best_threshold


# ============================================================
# tree build
# ============================================================


def build_tree(
    data,
    label,
    sample_index,
    depth=1,
    threshold=0.95,
    limit_depth=4,
    max_depth=None,
    min_samples_split=2,
    min_samples_leaf=1,
    rng=None,
):
    """
    构建单棵树。

    保留原逻辑：
        if (max_lable_rate >= threshold) and (depth >= 4):
            return leaf

    改进逻辑：
        每个节点随机选择 k = log2(feature_num)+1 个特征寻找最佳划分。
    """
    node = {
        "fea": -1,
        "value": None,
        "results": None,
        "right": None,
        "left": None,
    }

    depth += 1

    if sample_index.shape[0] == 0:
        return node

    label_cate, label_count, total_hist, min_label = label_stat_by_index(
        label, sample_index
    )
    max_lable_rate = label_count.max() / label_count.sum()

    # 1. 单一类别，停止
    if label_cate.shape[0] == 1:
        node["results"] = (label_cate, label_count)
        return node

    # 2. 保留你的原始模糊停止逻辑
    if (max_lable_rate >= threshold) and (depth >= limit_depth):
        argsort_idx = np.argsort(label_count)[::-1]
        node["results"] = (label_cate[argsort_idx], label_count[argsort_idx])
        return node

    # 3. 可选停止条件：避免过深、过小叶子；默认不强行限制原行为
    if max_depth is not None and depth >= max_depth:
        argsort_idx = np.argsort(label_count)[::-1]
        node["results"] = (label_cate[argsort_idx], label_count[argsort_idx])
        return node

    if sample_index.shape[0] < min_samples_split:
        argsort_idx = np.argsort(label_count)[::-1]
        node["results"] = (label_cate[argsort_idx], label_count[argsort_idx])
        return node

    # 4. 每个节点随机选择特征，更接近标准随机森林
    feature_num = data.shape[1]
    if feature_num <= 0:
        argsort_idx = np.argsort(label_count)[::-1]
        node["results"] = (label_cate[argsort_idx], label_count[argsort_idx])
        return node

    k = int(math.log(feature_num, 2)) + 1 if feature_num > 2 else 1
    k = min(k, feature_num)
    feature_ids = rng.choice(feature_num, size=k, replace=False).astype(np.int32)

    best_gain, best_feature, best_threshold = best_split_sorted_scan(
        data, label, sample_index.astype(np.int32), feature_ids, total_hist, min_label
    )

    if best_gain <= 0.0 or best_feature < 0:
        argsort_idx = np.argsort(label_count)[::-1]
        node["results"] = (label_cate[argsort_idx], label_count[argsort_idx])
        return node

    feat = data[sample_index, best_feature]
    left_ids = sample_index[feat < best_threshold]
    right_ids = sample_index[feat >= best_threshold]

    # 防止过小叶子或异常空分裂
    if left_ids.shape[0] < min_samples_leaf or right_ids.shape[0] < min_samples_leaf:
        argsort_idx = np.argsort(label_count)[::-1]
        node["results"] = (label_cate[argsort_idx], label_count[argsort_idx])
        return node

    node["fea"] = int(best_feature)
    node["value"] = float(best_threshold)
    node["left"] = build_tree(
        data,
        label,
        left_ids.astype(np.int32),
        depth=depth,
        threshold=threshold,
        limit_depth=limit_depth,
        max_depth=max_depth,
        min_samples_split=min_samples_split,
        min_samples_leaf=min_samples_leaf,
        rng=rng,
    )
    node["right"] = build_tree(
        data,
        label,
        right_ids.astype(np.int32),
        depth=depth,
        threshold=threshold,
        limit_depth=limit_depth,
        max_depth=max_depth,
        min_samples_split=min_samples_split,
        min_samples_leaf=min_samples_leaf,
        rng=rng,
    )
    return node


# ============================================================
# train
# ============================================================


def _typecode(dtype):
    type2ctype = {
        "uint8": "B",
        "int8": "b",
        "uint16": "H",
        "int16": "h",
        "uint32": "I",
        "int32": "i",
        "float32": "f",
        "float64": "d",
    }
    name = np.dtype(dtype).name
    if name not in type2ctype:
        raise TypeError("Unsupported dtype for shared memory: {}".format(name))
    return type2ctype[name]


def multi_build_tree(args):
    (
        tree_id,
        threshold,
        limit_depth,
        max_depth,
        min_samples_split,
        min_samples_leaf,
        random_state,
    ) = args
    data = np.frombuffer(global_train_share, dtype=DATA_DTYPE).reshape(DATA_SHAPE)
    label = np.frombuffer(global_label_share, dtype=LABEL_DTYPE).reshape(LABEL_SHAPE)

    seed = None if random_state is None else int(random_state) + int(tree_id)
    rng = np.random.default_rng(seed)

    n = data.shape[0]
    # bootstrap 有放回抽样
    sample_index = rng.choice(n, size=n, replace=True).astype(np.int32)

    tree = build_tree(
        data,
        label,
        sample_index,
        depth=1,
        threshold=threshold,
        limit_depth=limit_depth,
        max_depth=max_depth,
        min_samples_split=min_samples_split,
        min_samples_leaf=min_samples_leaf,
        rng=rng,
    )
    return tree


def random_forest_training(
    feat_train,
    labels_train,
    trees_num,
    threshold=0.95,
    limit_depth=4,
    max_depth=None,
    min_samples_split=2,
    min_samples_leaf=1,
    random_state=None,
):
    """
    构建随机森林。

    与原程序相比：
    - 返回 trees_result
    """
    if trees_num <= 0:
        raise ValueError("trees_num must be positive")

    feat_train = np.ascontiguousarray(feat_train)
    labels_train = np.ascontiguousarray(labels_train)

    feat_train_share = mp.RawArray(_typecode(feat_train.dtype), feat_train.ravel())
    labels_train_share = mp.RawArray(
        _typecode(labels_train.dtype), labels_train.ravel()
    )
    tasks = trees_num < os.cpu_count() and trees_num or os.cpu_count()

    pool = mp.Pool(
        processes=tasks,
        initializer=init_pool_train,
        initargs=(
            feat_train_share,
            labels_train_share,
            feat_train.shape,
            labels_train.shape,
            feat_train.dtype,
            labels_train.dtype,
        ),
    )

    bar = Bar(trees_num)
    async_results = []
    for tree_id in range(trees_num):
        args = (
            tree_id,
            threshold,
            limit_depth,
            max_depth,
            min_samples_split,
            min_samples_leaf,
            random_state,
        )
        async_results.append(
            pool.apply_async(
                multi_build_tree, args=(args,), callback=lambda _: bar.update()
            )
        )

    pool.close()
    pool.join()
    bar.shutdown()

    trees_result = [r.get() for r in async_results]
    return trees_result


# ============================================================
# predict
# ============================================================
def flatten_forest(trees_result):
    """
    将字典格式的随机森林模型拍平为 Numba 易于读取的扁平化 NumPy 数组。
    """
    all_features = []
    all_thresholds = []
    all_lefts = []
    all_rights = []
    all_is_leaf = []
    all_labels = []

    tree_offsets = np.empty(len(trees_result), dtype=np.int32)
    current_global_offset = 0

    for i, tree in enumerate(trees_result):
        tree_offsets[i] = current_global_offset
        nodes = []

        def parse_node(node):
            nonlocal current_global_offset
            node_idx = len(nodes)

            # 初始化当前节点项
            entry = {
                "fea": node["fea"],
                "value": node["value"] if node["value"] is not None else 0.0,
                "left": -1,
                "right": -1,
                "is_leaf": 0,
                "label": -1,
            }
            nodes.append(entry)

            if node["results"] is not None:
                entry["is_leaf"] = 1
                entry["label"] = int(node["results"][0][0])
            else:
                # 递归解析子节点
                left_child_rel_idx = parse_node(node["left"])
                entry["left"] = left_child_rel_idx

                right_child_rel_idx = parse_node(node["right"])
                entry["right"] = right_child_rel_idx

            return node_idx

        parse_node(tree)
        tree_size = len(nodes)

        # 将局部相对索引转换为全局绝对索引
        for node_idx, entry in enumerate(nodes):
            all_features.append(entry["fea"])
            all_thresholds.append(entry["value"])
            all_is_leaf.append(entry["is_leaf"])
            all_labels.append(entry["label"])

            if entry["is_leaf"] == 0:
                all_lefts.append(current_global_offset + entry["left"])
                all_rights.append(current_global_offset + entry["right"])
            else:
                all_lefts.append(-1)
                all_rights.append(-1)

        current_global_offset += tree_size

    # 转换为连续数组返回
    features = np.ascontiguousarray(
        np.array(all_features, dtype=np.int32), dtype=np.int32
    )
    thresholds = np.ascontiguousarray(
        np.array(all_thresholds, dtype=np.float64), dtype=np.float64
    )
    lefts = np.ascontiguousarray(np.array(all_lefts, dtype=np.int32), dtype=np.int32)
    rights = np.ascontiguousarray(np.array(all_rights, dtype=np.int32), dtype=np.int32)
    is_leaf = np.ascontiguousarray(np.array(all_is_leaf, dtype=np.int8), dtype=np.int8)
    labels = np.ascontiguousarray(np.array(all_labels, dtype=np.int32), dtype=np.int32)
    tree_offsets = np.ascontiguousarray(tree_offsets, dtype=np.int32)
    return (features, thresholds, lefts, rights, is_leaf, labels, tree_offsets)


@nb.njit(parallel=True)
def nb_predict_forest_pixels(
    data,
    features,
    thresholds,
    left_children,
    right_children,
    is_leaf,
    labels,
    tree_offsets,
    background=50,
    class_num=10,
):
    """
    利用 Numba 的 parallel=True 自动进行多线程并行化像元预测。
    非常适合遥感大图预测。
    """
    n_samples = data.shape[0]
    n_trees = tree_offsets.shape[0]
    final_outputs = np.full(n_samples, background, dtype=np.uint8)

    # 对所有样本（像素点）进行并行循环
    for i in nb.prange(n_samples):
        if np.sum(data[i]) == 0:
            continue
        # 收集该像素在每棵树上的投票结果, numba官方建议局部数组用empty，手动初始化
        votes = np.empty(class_num, np.int32)
        for k in range(class_num):
            votes[k] = 0
        # 初始化有效投票次数
        valid_votes = 0
        for t in range(n_trees):
            node_idx = tree_offsets[t]  # 找到这棵树的根节点绝对索引
            while True:
                if is_leaf[node_idx] == 1:
                    lbl = labels[node_idx]
                    if 0 <= lbl < class_num:
                        votes[lbl] += 1
                        valid_votes += 1
                    break
                # 决策树分支判定
                idx = features[node_idx]
                if data[i, idx] >= thresholds[node_idx]:
                    node_idx = right_children[node_idx]
                else:
                    node_idx = left_children[node_idx]

        # 多数投票
        # 假设标签不包含负数。如果有负数标签，可以使用更通用的求众数方法
        # max_val = np.max(votes)
        # counts = np.zeros(max_val + 1, dtype=np.int32)
        # for v in votes:
        #     counts[v] += 1

        # final_outputs[i] = np.argmax(counts)
        if valid_votes > 0:
            final_outputs[i] = np.argmax(votes)
        else:
            final_outputs[i] = background
    return final_outputs


def get_predict(trees_result, sample_verify):
    # 将模型展平为数组，便于加速
    features, thresholds, lefts, rights, is_leaf, labels, tree_offsets = flatten_forest(
        trees_result
    )
    # 推理
    sample_verify_trans = np.ascontiguousarray(sample_verify, dtype=np.float64)
    sample_verify = None
    final_predict = nb_predict_forest_pixels(
        sample_verify_trans,
        features,
        thresholds,
        lefts,
        rights,
        is_leaf,
        labels,
        tree_offsets,
    )
    sample_verify_trans = None
    return final_predict


# ============================================================
# metrics and save
# ============================================================


def cal_corr_rate(sample_labels, final_predict):

    flags = np.unique(sample_labels)
    mat = np.zeros((flags.size, flags.size), dtype=np.float64)

    for ipre in range(len(flags)):
        pre_index = np.where(final_predict == flags[ipre])[0]
        tr_value = sample_labels[pre_index]
        for itr in range(len(flags)):
            mat[ipre, itr] = np.sum(tr_value == flags[itr])

    micro_ppv = np.zeros(len(flags), dtype=np.float64)
    micro_trp = np.zeros(len(flags), dtype=np.float64)

    for iflag in range(len(flags)):
        tp = mat[iflag, iflag]
        fp = np.sum(mat[iflag, :]) - tp
        fn = np.sum(mat[:, iflag]) - tp

        ppv = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        trp = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * ppv * trp / (ppv + trp) if (ppv + trp) > 0 else 0.0

        micro_ppv[iflag] = ppv
        micro_trp[iflag] = trp

        print("The flag is: {}".format(flags[iflag]))
        print("The Precision is: {:<5.4}".format(ppv))
        print("The Sensitivity is: {:<5.4}".format(trp))
        print("The F1-Score is: {:<5.4}".format(f1))

    micro_p = np.average(micro_ppv)
    micro_t = np.average(micro_trp)
    micro_f1 = (
        2 * micro_p * micro_t / (micro_p + micro_t) if (micro_p + micro_t) > 0 else 0.0
    )
    acc = np.trace(mat) / np.sum(mat) if np.sum(mat) > 0 else 0.0

    pe_rows = np.sum(mat, axis=0)
    pe_cols = np.sum(mat, axis=1)
    sum_total = np.sum(pe_cols)
    pe = np.dot(pe_rows, pe_cols) / float(sum_total**2) if sum_total > 0 else 0.0
    po = np.trace(mat) / float(sum_total) if sum_total > 0 else 0.0
    kappa = (po - pe) / (1 - pe) if (1 - pe) != 0 else 0.0
    score = 0.5 * micro_f1 + 0.3 * acc + 0.2 * kappa

    print("The Micro-F1-Score is: {:<5.4}".format(micro_f1))
    print("The Accuracy is: {:<5.4}".format(acc))
    print("The Kappa is: {:<5.4}".format(kappa))
    print("The Score is: {:<5.4}".format(score))
    return [micro_f1, acc, kappa, score]


def save_model(trees_result, model_file):
    with open(model_file, "wb") as f:
        pickle.dump(trees_result, f)


def main(
    sample_file,
    model_dir,
    model_name,
    tree_num,
    threshold=0.95,
    limit_depth=4,
    max_depth=None,
    min_samples_split=2,
    min_samples_leaf=1,
    random_state=2000,
):
    print("--------------------load data---------------------")
    # 如果你的标签确定是 int16 且特征也是 int16，可改为 dtype=np.int16。
    # 这里用 float32 兼容连续特征，标签会在统计时转 int。
    data_all = np.loadtxt(sample_file, delimiter=",", dtype=np.float32)
    # 打乱数据，分训练和验证数据集
    idx = np.random.permutation(data_all.shape[0])
    split = int(data_all.shape[0] * 0.8)
    sample_feats = data_all[:, :-1]
    sample_labels = data_all[:, -1].astype(np.int32)
    sample_feat_train, sample_label_train = (
        sample_feats[idx[:split]],
        sample_labels[idx[:split]],
    )
    sample_feat_verify, sample_label_verify = (
        sample_feats[idx[split:]],
        sample_labels[idx[split:]],
    )

    print("---------------random forest training-------------")
    trees_result = random_forest_training(
        sample_feat_train,
        sample_label_train,
        tree_num,
        threshold=threshold,
        limit_depth=limit_depth,
        max_depth=max_depth,
        min_samples_split=min_samples_split,
        min_samples_leaf=min_samples_leaf,
        random_state=random_state,
    )

    print("---------------get prediction correct rate--------")
    result = get_predict(trees_result, sample_feat_verify)
    precision = cal_corr_rate(sample_label_verify, result)
    corr_rate = "_".join([str(round(x, 4)) for x in precision])

    model_name = os.path.splitext(os.path.basename(model_name))[0]
    if not os.path.exists(model_dir):
        os.makedirs(model_dir)

    model_file = (
        os.path.join(model_dir, model_name)
        + "_"
        + str(tree_num)
        + "_"
        + corr_rate
        + "_mdl.pkl"
    )

    print("--------------------save model---------------------")
    save_model(trees_result, model_file)
    return None


if __name__ == "__main__":
    if gdal is not None:
        gdal.SetConfigOption("GDAL_FILENAME_IS_UTF8", "YES")
        gdal.SetConfigOption("SHAPE_ENCODING", "GBK")
        if ogr is not None:
            ogr.RegisterAll()
        gdal.AllRegister()

    start_time = time.time()
    threshold = 0.98
    limit_depth = 4
    samplefile = r"F:\cotton\sample\L2A_T45TUK_A025799_20200531T051701_sample_new.csv"
    model_dir = r"F:\cotton\sample\model_new"
    model_name = (
        "_".join(["S2", str(200531), str(limit_depth), str(threshold)]) + "_mdl.pkl"
    )

    for tree_num in range(10, 31, 5):
        for iround in range(3):
            print(
                "Start the {} round of training for {} trees".format(
                    str(iround + 1), str(tree_num)
                )
            )
            main(
                samplefile,
                model_dir,
                model_name,
                tree_num,
                threshold=threshold,  # 保留 max_lable_rate >= 0.95
                limit_depth=limit_depth,  # 用于和threshold配合使用, 防止因样本不均衡过早结束
                max_depth=None,  # 默认不限制深度，接近原程序
                min_samples_split=2,
                min_samples_leaf=1,
                random_state=None,  # 如需复现实验，可设为固定整数，例如 2024
            )

    end_time = time.time()
    print("time: %.4f secs." % (end_time - start_time))
