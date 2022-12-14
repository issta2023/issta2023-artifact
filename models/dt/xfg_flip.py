from ast import dump
import json
import os
from pickle import encode_long
import numpy as np
from numpy.core.defchararray import count
from scipy.sparse.construct import random
from utils.json_ops import read_json

def dwk_downsample(ws ,ds_count, noise_rate):
    """
    @description  :differential training down sample
    ---------
    @param  :
    ws:whole samples
    ds_count: down sample count
    -------
    @Returns  :
    ds:down samples
    ds_idx:index of down sample in ws
    -------
    """
    d_samples = np.random.choice(ws, ds_count,replace=False)
    new_d_samples = []
    ds_idx = []
    for d in d_samples:
        ds_idx.append(d['xfg_id'])
        new_d_samples.append(d)
    # print(ds_idx)

    return new_d_samples, ds_idx

def remove_xfg(ws, rm_id_list, reserved_id_list):
    re_list = []
    true_xfg_ids = []
    for xfg in ws:
        xfg_id = xfg['xfg_id']
        if xfg_id in rm_id_list and xfg_id not in reserved_id_list:
            continue
        if xfg_id not in rm_id_list:
            true_xfg_ids.append(xfg_id)
        re_list.append(xfg)
    np.random.shuffle(re_list)
    return re_list, true_xfg_ids


def xfg_downsample_from_cl(ws, _config, ws_ids, cl_error_ids, noise_rate):
    
    
    
    
    
    sub_error_ids = np.random.choice(cl_error_ids, 300, replace=False)
    sub_ws_ids = np.random.choice(ws_ids, 3000, replace=False)

    all_ds_ids = []
    all_ds_ids.extend(sub_error_ids)
    all_ds_ids.extend(sub_ws_ids)
    np.random.shuffle(all_ds_ids)

    ws_train_ids = list(set(ws_ids) | set(sub_error_ids))

    ws_train = []

    for xfg in ws:
        xfg_id = xfg['xfg_id']
        if xfg_id in ws_train_ids:
            ws_train.append(xfg)

    np.random.shuffle(ws_train)

    ds_idx = []
    ds_samples = []
    ds_list = []
    for xfg in ws:
        xfg_id = xfg['xfg_id']
        if xfg_id in all_ds_ids:
            ds_list.append([xfg, xfg_id])

    np.random.shuffle(ds_list)

    for data in ds_list:
        ds_samples.append(data[0])
        ds_idx.append(data[1])
    print('ds_samples', len(ds_samples))

    return ds_samples, ws_train, ds_idx


if __name__ == "__main__":
    bigjson_path = '/home/niexu/project/python/deepwukong/data/diff_train/CWE119/bigjson_flip.json'
    
    big_json_flip = []
    with open(bigjson_path, 'r', encoding = 'utf8') as f:
        big_json_flip = json.load(f)
        f.close()
    
    ds, ds_idx = xfg_downsample(big_json_flip, 3000)