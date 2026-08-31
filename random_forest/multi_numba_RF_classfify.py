#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2026/08/03
# Description:
使用 multiprocessing 技术利用随机森林方法并行进行多景影像分类
"""

import os

# 必须在导入 numpy 和 numba 之前设置这些环境变量！
# 强制限制底层 BLAS 运算库和 Numba 仅使用 1 个线程，防止多进程间产生剧烈的 CPU 核夺权冲突
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
os.environ["NUMBA_NUM_THREADS"] = "1"  # 限制 Numba 自身的线程池大小
import sys
import glob
import time
import pickle
import fnmatch
import gc
import numba as nb
import numpy as np
from tinydb import TinyDB, Query
import multiprocessing as mp
from osgeo import gdal, ogr, osr, gdalconst

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


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
                left_child_rel_idx = parse_node(node["left"])
                entry["left"] = left_child_rel_idx

                right_child_rel_idx = parse_node(node["right"])
                entry["right"] = right_child_rel_idx

            return node_idx

        parse_node(tree)
        tree_size = len(nodes)

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


@nb.njit(fastmath=True)
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
    n_samples = data.shape[0]
    n_trees = tree_offsets.shape[0]
    final_outputs = np.full(n_samples, background, dtype=np.uint8)

    for i in range(n_samples):
        if np.sum(data[i]) == 0:
            continue
        votes = np.empty(class_num, np.int32)
        for k in range(class_num):
            votes[k] = 0
        valid_votes = 0
        for t in range(n_trees):
            node_idx = tree_offsets[t]
            while True:
                if is_leaf[node_idx] == 1:
                    lbl = labels[node_idx]
                    if 0 <= lbl < class_num:
                        votes[lbl] += 1
                        valid_votes += 1
                    break
                idx = features[node_idx]
                if data[i, idx] >= thresholds[node_idx]:
                    node_idx = right_children[node_idx]
                else:
                    node_idx = left_children[node_idx]

        if valid_votes > 0:
            final_outputs[i] = np.argmax(votes)
        else:
            final_outputs[i] = background
    return final_outputs


def process_single_image(args):
    """
    单个影像处理的目标函数，供进程池调用。
    """
    img_file, out_file, model_arrays = args
    features, thresholds, lefts, rights, is_leaf, labels, tree_offsets = model_arrays

    try:
        in_ds = gdal.Open(img_file)
        if in_ds is None:
            return f"Error: Cannot open {img_file}"

        rpj = in_ds.GetProjection()
        geo = in_ds.GetGeoTransform()
        xsize = in_ds.RasterXSize
        ysize = in_ds.RasterYSize

        ori_data = in_ds.ReadAsArray()
        channels, rows, cols = ori_data.shape

        ori_data_trans = np.ascontiguousarray(
            ori_data.reshape(channels, rows * cols).T, dtype=np.float64
        )
        ori_data = None
        del ori_data
        in_ds = None

        # 推理
        final_predict = nb_predict_forest_pixels(
            ori_data_trans,
            features,
            thresholds,
            lefts,
            rights,
            is_leaf,
            labels,
            tree_offsets,
        )
        ori_data_trans = None
        del ori_data_trans

        # 输出结果
        clas_res = final_predict.reshape(rows, cols)
        clas_res += 100
        final_predict = None
        del final_predict

        # 创建输出目录
        outdir = os.path.dirname(out_file)
        if not os.path.exists(outdir):
            try:
                os.makedirs(outdir, exist_ok=True)
            except FileExistsError:
                pass

        tif_driver = gdal.GetDriverByName("GTiff")
        out_ds = tif_driver.Create(out_file, xsize, ysize, 1, gdal.GDT_Byte)
        out_ds.SetProjection(rpj)
        out_ds.SetGeoTransform(geo)
        out_band = out_ds.GetRasterBand(1)
        out_band.WriteArray(clas_res)
        out_ds.FlushCache()

        clas_res = None
        out_band = None
        out_ds = None
        del clas_res
        del out_ds
        gc.collect()
        return f"Success: {out_file}"
    except Exception as e:
        return f"Failed {img_file} due to error: {str(e)}"


if __name__ == "__main__":
    gdal.SetConfigOption("GDAL_FILENAME_IS_UTF8", "YES")
    gdal.SetConfigOption("SHAPE_ENCODING", "GBK")
    ogr.RegisterAll()
    gdal.AllRegister()

    start_time = time.time()

    region = "north"
    year = "2026"
    dir_dict = {"2025": "sdb", "2026": "sdc"}
    model_file = "/home/liming/cotton-classification/model/north-south_2026_new/S2_260801_4_0.98_mdl_25_0.9835_0.9835_0.9669_0.9802_mdl.pkl"

    start_date = f"{year}-06-20"
    end_date = f"{year}-07-31"
    base_dir = f"/mnt/{dir_dict[year]}/XinJiang/{year}/S2_VI_Product"

    if os.name == "nt":
        record_path = r"C:\Users\01\Desktop\record.json"
    else:
        record_path = f"/mnt/nvme2n1/liming/record-{year}06-{region}.json"

    # 主进程一次性加载和展平模型数据
    print("正在加载并解析模型文件...")
    with open(model_file, "rb") as f:
        trees_result = pickle.load(f)
    model_arrays = flatten_forest(trees_result)
    trees_result = None
    gc.collect()

    # 1. 收集区县列表
    shp_dir = f"/mnt/nvme2n1/liming/xzqh_shp/{region}"
    county_list = []
    if os.path.exists(shp_dir):
        file_list = os.listdir(shp_dir)
        for file in file_list:
            if file.endswith(".shp"):
                county_name = os.path.splitext(file)[0].split("_")[-1]
                if county_name.endswith("11"):
                    county_name = county_name[:-2]
                county_list.append(county_name)

    # 2. 统一收集所有待处理的任务列表
    tasks = []
    tif_db = TinyDB(record_path)
    q = Query()

    for county in county_list:
        out_dir = f"/mnt/{dir_dict[year]}/XinJiang/{year}/{region}_{year}/S2_Classification/{county}"
        tif_list = tif_db.search(
            ((q.farmID.any([f"{county}"])) | (q.farmID.any([f"{county}11"])))
            & (q.generationdate >= start_date)
            & (q.generationdate <= end_date)
        )

        for tif in tif_list:
            tile_id = tif["tileid"]
            tif_date = tif["generationdate"]
            tif_files = glob.glob(f"{base_dir}/{tile_id}/{tif_date}/**.tif")

            for tif_file in tif_files:
                out_file_name = os.path.basename(tif_file).replace(
                    "vi.tif", "vi_class.tif"
                )
                out_file = os.path.join(out_dir, out_file_name)

                # 如果文件已经存在，跳过不加入任务队列
                if os.path.exists(out_file):
                    continue

                # 打包成任务元组：(待处理文件, 输出文件, 模型数组)
                tasks.append((tif_file, out_file, model_arrays))

    tif_db.close()

    total_tasks = len(tasks)
    print(f"任务收集完毕，共有 {total_tasks} 景影像需要推理。")

    # 3. 多进程并行执行
    if total_tasks > 0:
        process_num = min(total_tasks, 8)
        print(f"启动多进程池，进程数: {process_num}")

        # 使用 imap_unordered 可以在每处理完一个时就立即返回结果，便于打印进度
        with mp.Pool(processes=process_num) as pool:
            for i, result in enumerate(
                pool.imap_unordered(process_single_image, tasks)
            ):
                # 打印进度
                progress((i + 1) / total_tasks)
                if "Failed" in result or "Error" in result:
                    print(f"\n{result}")

    end_time = time.time()
    print("\n全部处理完成！总耗时: %.4f secs." % (end_time - start_time))
