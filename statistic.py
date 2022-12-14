#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@Description:       :  statistic all data 
@Date     :2021/08/15 19:46:44
@Author      :ives-nx
@version      :1.0
'''
import json
from logging import error
import os
import jsonlines
from numpy.lib.utils import info
from scipy.sparse import data
from scipy.sparse.construct import random
from models.sysevr.buffered_path_context import BufferedPathContext as BPC_sys
from models.vuldeepecker.buffered_path_context import BufferedPathContext as BPC_vdp
from utils.common import CWEID_NOISE, NOISE_RATES
from utils.json_ops import read_json, write_json
import numpy as np
import math
from argparse import ArgumentParser
from utils.common import print_config, filter_warnings, get_config_dwk
import copy
import pprint
from collections import defaultdict
pp = pprint.PrettyPrinter(indent=2)
def statistic_dwk_data(cwe_id:str, noisy_rate:float = None):
    """
    @description  : statistic data distribution for deepwukong
    ---------
    @param  :
    -------
    @Returns  :
    -------
    """
    
    
    if noisy_rate:
        data_path = 'data/CWES/{}/{}_{}_percent.json'.format(cwe_id, cwe_id, int(noisy_rate * 100))
        data = read_json(data_path)
        all_xfg_count = len(data)
        safe_count = 0
        vul_count = 0
        fliped_count = 0
        fliped_safe_count = 0
        fliped_vul_count = 0
        for xfg in data:
            if xfg['target'] == 1:
                vul_count += 1
            else:
                safe_count += 1
            if xfg['flip']:
                fliped_count += 1
                if xfg['target'] == 1:
                    fliped_safe_count += 1
                else:
                    fliped_vul_count += 1
        result = dict()
        result['title'] = 'dwk_{}_{}_percent'.format(cwe_id, int(noisy_rate * 100))
        result['all_xfg_count'] = all_xfg_count
        result['safe_count'] = safe_count
        result['vul_count'] = vul_count
        result['fliped_count'] = fliped_count
        result['fliped_safe_count'] = fliped_safe_count
        result['fliped_vul_count'] = fliped_vul_count
    else:
        data_path = 'data/CWES/{}/{}.json'.format(cwe_id, cwe_id)
        data = read_json(data_path)
        all_xfg_count = len(data)
        safe_count = 0
        vul_count = 0
        fliped_count = 0
        fliped_safe_count = 0
        fliped_vul_count = 0
        for xfg in data:
            if xfg['target'] == 1:
                vul_count += 1
            else:
                safe_count += 1
        result = dict()
        result['title'] = 'dwk_{}_{}_percent'.format(cwe_id, 0)
        result['all_xfg_count'] = all_xfg_count
        result['safe_count'] = safe_count
        result['vul_count'] = vul_count
    print(result)
    return result

def statistic_manual_dwk():
    manual_noise_path = '/home/niexu/project/python/noise_reduce/res/deepwukong/cl_result/BUFFER_OVERRUN/manual_noise.json'
    noise_info_path = '/home/niexu/project/python/noise_reduce/res/deepwukong/cl_result/BUFFER_OVERRUN/noise_info.json'
    manual_noise = read_json(manual_noise_path)
    noise_info = read_json(noise_info_path)
    flipped = np.array(manual_noise['flip'])
    error_label = np.array(manual_noise['error_label'])
    xfg_ids = np.array(manual_noise['xfg_id'])
    noise_filpped = flipped[error_label]
    noise_xfg_ids = xfg_ids[error_label]
    true_noise_xfg_ids = noise_xfg_ids[noise_filpped]
    print(true_noise_xfg_ids)
    print(len(true_noise_xfg_ids))
    find_true_noise_info = defaultdict(list)
    for key in noise_info:
        for xfg_id in true_noise_xfg_ids:
            if xfg_id in noise_info[key]:
                find_true_noise_info[key].append(xfg_id.tolist())
    find_true_noise_info_path = '/home/niexu/project/python/noise_reduce/res/deepwukong/cl_result/BUFFER_OVERRUN/find_true_noise_info.json'
    print(find_true_noise_info)
    write_json(find_true_noise_info, output=find_true_noise_info_path)
def statistic_sys_data(cwe_id:str, noisy_rate:float = None):
    """
    @description  : statistic data distribution for sysevr
    ---------
    @param  :
    -------
    @Returns  :
    -------
    """
    if noisy_rate:
        data_path = 'data/sysevr/{}/{}_{}_percent.pkl'.format(cwe_id, cwe_id, int(noisy_rate * 100))
    else:
        data_path = 'data/sysevr/{}/train.pkl'.format(cwe_id)
    data = BPC_sys.joblib_load(data_path)
    all_cdg_count = len(data)
    safe_count = 0
    vul_count = 0
    fliped_count = 0
    fliped_safe_count = 0
    fliped_vul_count = 0
    for d in data:
        if d[1] == 1:
            vul_count += 1
        else:
            safe_count += 1
        if d[4]:
            fliped_count += 1
            if d[1] == 1:
                fliped_safe_count += 1
            else:
                fliped_vul_count += 1
    result = dict()
    result['title'] = 'sys_{}_{}_percent'.format(cwe_id, int(noisy_rate * 100))
    result['all_cdg_count'] = all_cdg_count
    result['safe_count'] = safe_count
    result['vul_count'] = vul_count
    result['fliped_count'] = fliped_count
    result['fliped_safe_count'] = fliped_safe_count
    result['fliped_vul_count'] = fliped_vul_count
    print(result)
    return result

def statistic_vdp_data(cwe_id:str, noisy_rate:float = None):

    if noisy_rate:
        data_path = 'data/vuldeepecker/{}/{}_{}_percent.pkl'.format(cwe_id, cwe_id, int(noisy_rate * 100))
    else:
        data_path = 'data/vuldeepecker/{}/train.pkl'.format(cwe_id)
    data = BPC_vdp.joblib_load(data_path)
    all_cdg_count = len(data)
    safe_count = 0
    vul_count = 0
    fliped_count = 0
    fliped_safe_count = 0
    fliped_vul_count = 0
    for d in data:
        if d[1] == 1:
            vul_count += 1
        else:
            safe_count += 1
        if d[5]:
            fliped_count += 1
            if d[1] == 1:
                fliped_safe_count += 1
            else:
                fliped_vul_count += 1
    result = dict()
    result['title'] = 'vdp_{}_{}_percent'.format(cwe_id, int(noisy_rate * 100))
    result['all_cdg_count'] = all_cdg_count
    result['safe_count'] = safe_count
    result['vul_count'] = vul_count
    result['fliped_count'] = fliped_count
    result['fliped_safe_count'] = fliped_safe_count
    result['fliped_vul_count'] = fliped_vul_count
    print(result)
    return result




def statistic_cl_result(config, noisy_rate:float = None):
    """
    @description  : statistic confident learning result
    ---------
    @param  :
    -------
    @Returns  :
    -------
    """
    method = config.name
    cwe_id = config.dataset.name
    res = config.res_folder
    if method not in ['deepwukong', 'sysevr', 'vuldeepecker', 'reveal', 'stack']:
        raise RuntimeError('{} name error !'.format(method))

    # if noisy_rate not in [0.1, 0.2, 0.3, 0.4]:
    #     raise RuntimeError('{} noisy rate error !'.format(noisy_rate))
    # data_path = '{}/{}/cl_result/{}/{}_percent_res.json'.format(res, method, cwe_id, int(noisy_rate*100))
    data_path = '{}/{}/cl_cv_dwk/{}/{}_percent_res.json'.format(res, method, cwe_id, int(noisy_rate*100))

    if method in ['deepwukong', 'reveal', 'stack']:
        id_key = 'xfg_id'
        flip_key = 'flip'
    else:
        id_key = 'idx'
        flip_key = 'flips'
    data = read_json(data_path)
    labels = data['s']
    error_label = data['error_label']
    fliped = data[flip_key]
    idxs = data[id_key]
    fliped = np.array(fliped)
    found_noise_count = len(fliped[error_label])
    found_true_count = np.sum(fliped[error_label])
    found_labels = np.array(labels)[error_label]
    found_1_count = found_labels.sum()
    found_0_count = len(found_labels) - found_labels.sum()
    flipped = np.sum(fliped)
    
    # idxs = np.array(idxs)
    

    
    result = dict()
    result['title'] = '{}_{}_{}_{}_percent'.format(method, 'cl', cwe_id, int(noisy_rate * 100))
    result['sample_count'] = len(fliped)
    result['flipped'] = flipped
    result['found_noisy_count'] = found_noise_count
    result['found_1_count'] = found_1_count
    result['found_0_count'] = found_0_count
    result['TP_count'] = found_true_count
    result['FP_count'] = found_noise_count - found_true_count
    result['recall'] = round(found_true_count / flipped ,2)
    result['precision'] = round( found_true_count / found_noise_count ,2)
    result['noisy_rate_after_cl'] = round((flipped - found_true_count) 
     / (len(fliped) - found_noise_count), 2)
    print(result)
    return result



def statistic_dt_result(config, noisy_rate:float = None):
    """
    @description  : statistic differential training result
    ---------
    @param  :
    -------
    @Returns  :
    -------
    """
    method = config.dt.model_name
    cwe_id = config.dataset.name
    res = config.res_folder
    if method not in ['deepwukong', 'sysevr', 'vuldeepecker']:
        raise RuntimeError('{} name error !'.format(method))

    # if noisy_rate not in [0.1, 0.2, 0.3]:
    #     raise RuntimeError('{} noisy rate error !'.format(noisy_rate))
    dt_data_path = '{}/{}/dt_result/{}/{}_percent_ws.json'.format(res, method, cwe_id, int(noisy_rate*100))
    if method == 'deepwukong':
        raw_data_path = 'data/CWES/{}/{}.json'.format(cwe_id, cwe_id)
        noise_info_path = 'data/CWES/{}/noise_info.json'.format(cwe_id)
    else:
        raw_data_path = 'data/{}/{}/{}.json'.format(method, cwe_id, cwe_id)
        noise_info_path = 'data/{}/{}/noise_info.json'.format(method, cwe_id)
    noise_key = '{}_percent'.format(int(100 * noisy_rate))
    noise_info = read_json(noise_info_path)
    raw_data = read_json(raw_data_path) 
    if config.res_folder == 'res_d2a_flip':
        noise_xfg_ids = []
        for xfg in raw_data:
            if xfg['flip']:
                noise_xfg_ids.append(xfg['xfg_id'])
    else:

        noise_xfg_ids = noise_info[noise_key]['noise_xfg_ids']
    if method == 'deepwukong':
        key = 'target'
        
    else:
        key = 'val'
    dt_nosie_xfg_ids = []  
    dt_data = read_json(dt_data_path)
       
    for xfg in dt_data:
        xfg_id = xfg['xfg_id']
        if xfg['flip']:
            dt_nosie_xfg_ids.append(xfg_id)
    noise_xfg_ids = set(noise_xfg_ids)
    dt_nosie_xfg_ids = set(dt_nosie_xfg_ids)

    # dt - noise  = found false
    # noise - dt = found true 
    # dt & noise = unfound

    found_noise_count = len(noise_xfg_ids ^ dt_nosie_xfg_ids)
    found_true_count = len(noise_xfg_ids - dt_nosie_xfg_ids)
    fount_false_count = len(dt_nosie_xfg_ids - noise_xfg_ids)

    
    result = dict()
    result['title'] = '{}_{}_{}_{}_percent'.format(method, 'dt', cwe_id, int(noisy_rate * 100))
    result['sample_count'] = len(raw_data)
    result['flipped'] = len(noise_xfg_ids)
    result['found_noisy_count'] = found_noise_count
    result['TP_count'] = found_true_count
    result['FP_count'] = fount_false_count
    result['recall'] = round(found_true_count / len(noise_xfg_ids) ,2)
    result['precision'] = round(found_true_count / found_noise_count ,2)
    result['noisy_rate_after_cl'] = round( (len(noise_xfg_ids) - found_true_count) / (len(raw_data) - found_noise_count), 2)
    print(result)
    return result

def get_dt_found_noise_ids(config, noisy_rate:float = None):
    """
    @description  : statistic differential training result
    ---------
    @param  :
    -------
    @Returns  :
    -------
    """
    method = config.dt.model_name
    cwe_id = config.dataset.name
    res = config.res_folder
    if method not in ['deepwukong', 'sysevr', 'vuldeepecker']:
        raise RuntimeError('{} name error !'.format(method))

    # if noisy_rate not in [0.1, 0.2, 0.3]:
    #     raise RuntimeError('{} noisy rate error !'.format(noisy_rate))
    dt_data_path = '{}/{}/dt_result/{}/{}_percent_ws.json'.format(res, method, cwe_id, int(noisy_rate*100))
    if method == 'deepwukong':
        raw_data_path = 'data/CWES/{}/{}.json'.format(cwe_id, cwe_id)
        noise_info_path = 'data/CWES/{}/noise_info.json'.format(cwe_id)
    else:
        raw_data_path = 'data/{}/{}/{}.json'.format(method, cwe_id, cwe_id)
        noise_info_path = 'data/{}/{}/noise_info.json'.format(method, cwe_id)
    noise_key = '{}_percent'.format(int(100 * noisy_rate))
    noise_info = read_json(noise_info_path)
    raw_data = read_json(raw_data_path) 
    if config.res_folder == 'res_d2a_flip':
        noise_xfg_ids = []
        for xfg in raw_data:
            if xfg['flip']:
                noise_xfg_ids.append(xfg['xfg_id'])
    else:

        noise_xfg_ids = noise_info[noise_key]['noise_xfg_ids']
    if method == 'deepwukong':
        key = 'target'
        
    else:
        key = 'val'
    dt_nosie_xfg_ids = []  
    dt_data = read_json(dt_data_path)
       
    for xfg in dt_data:
        xfg_id = xfg['xfg_id']
        if xfg['flip']:
            dt_nosie_xfg_ids.append(xfg_id)
    noise_xfg_ids = set(noise_xfg_ids)
    dt_nosie_xfg_ids = set(dt_nosie_xfg_ids)

    # dt - noise  = found false
    # noise - dt = found true 
    # dt & noise = unfound

    found_noise_xfg_ids = list(noise_xfg_ids ^ dt_nosie_xfg_ids)


    return found_noise_xfg_ids

def statistic_all_cl_metric(method, res_path):
    cwe_ids = CWEID_NOISE
    noise_rates = NOISE_RATES
    recall_list = []
    precision_list = []
    for cwe in cwe_ids:
        for noise_rate in noise_rates:
            config = get_config_dwk(cwe, method)
            config.res_folder = res_path
            metric = statistic_cl_result(config, noisy_rate=noise_rate)
            recall_list.append(metric['recall'])
            precision_list.append(metric['precision'])

    recall = np.array(recall_list)
    precision = np.array(precision_list)
    result = dict()
    result['recall_average'] = recall.mean()
    result['precision_average'] = precision.mean()
    pp.pprint(result)


def statistic_cl_and_dt(method):
    cl_data_path = '/home/niexu/project/python/noise_reduce/res/deepwukong/cl_result/CWE119_0.7/10_percent_res.json'
    dt_data_path = '/home/niexu/project/python/noise_reduce/res/deepwukong/dt_result/CWE119/10_percent_res_v4.jsonl'
    if method == 'deepwukong':
        id_key = 'xfg_id'
        flip_key = 'flip'
    else:
        id_key = 'idx'
        flip_key = 'flips'
    data = read_json(cl_data_path)
    error_label = data['error_label']
    fliped = data[flip_key]
    idxs = np.array(data[id_key])
    fliped = np.array(fliped)
    cl_tp_ids = set(idxs[error_label])

    outlier_list = []
    with jsonlines.open(dt_data_path) as reader:
        for obj in reader:
            outlier_list.extend(obj['outlier_list']) 
    dt_all_ids = set()
    dt_tp_ids = set()
    print(outlier_list)
    for outlier in outlier_list:
        dt_all_ids.add(outlier[0])
        if outlier[2]:
            dt_tp_ids.add(outlier[0])
    inter_ids = dt_all_ids & cl_tp_ids
    inter_tp_ids = dt_tp_ids & cl_tp_ids
    print('dt_all', len(dt_all_ids))
    print('dt_tp', len(dt_tp_ids))


    print('dt_all_in_cl_result', len(inter_ids))
    
    print('dt_tp_in_cl_result', len(inter_tp_ids))
    return list(inter_ids)

def analysis_cl(config):

    cl_data_path = '{}/{}/cl_result/{}/{}_percent_res.json'.format(config.res_folder,
                    config.name, config.dataset.name, int(config.noise_rate * 100))
    
    if config.name in ['deepwukong', 'reveal']:
        id_key = 'xfg_id'
        flip_key = 'flip'
        if config.name != 'deepwukong':
            method = config.name
        else:    
            method = 'CWES'
        label_key = 'target'
    else:
        id_key = 'idx'
        flip_key = 'flips'
        method = config.name
        label_key = 'val'
    
    data_path = '{}{}/{}/{}.json'.format(config.data_folder, method, config.dataset.name, config.dataset.name)
    output = 'result_analysis/{}/{}/cl'.format(config.name, config.dataset.name)
    os.makedirs(output, exist_ok=True)
    cl_data = read_json(cl_data_path)
    data = read_json(data_path)
    error_label = cl_data['error_label']
    fliped = cl_data[flip_key]
    idxs = np.array(cl_data[id_key])[error_label].tolist()
    
    choice_idxs = np.random.choice(idxs, 100, False)

    all_info = list()

    for xfg in data :
        if xfg['xfg_id'] not in choice_idxs:
            continue
        info = dict()
        info['code_path'] = xfg['file_path']
        info['code'] = xfg['node-line-content']
        info['target'] = xfg['target']
        # info['xfg_id'] = xfg['xfg_id']
        # info['vul_line'] = xfg['vul_line']
        # info['file_path'] = xfg['file_path']
        # info['target'] = xfg[label_key]
        # info['flip'] = xfg['flip']
        all_info.append(info)
    write_json(all_info, os.path.join(output, 'samples.json'))

def analysis_dt(method, cwe_id, noisy_rate):
    dt_data_path = 'res/{}/dt_result/{}/{}_percent_res.jsonl'.format(method, cwe_id, int(noisy_rate*100))
    outlier_list = []
    with jsonlines.open(dt_data_path) as reader:
        for obj in reader:
            outlier_list.extend(obj['outlier_list']) 
    

    # dds_loss = read_json('dds_loss.json')
    # wds_loss = read_json('wds_loss.json')
    info_list = set()
    flip_list = list()
    for outlier in outlier_list:
        xfg_id = outlier[0]
        label = outlier[1]
        flip = outlier[2]
        info_list.add(xfg_id)
        flip_list.append(flip)
        # info_list.append((xfg_id, label, flip, wds_loss[str(xfg_id)], dds_loss[str(xfg_id)]))
    # write_json(info_list, 'sard_simple_analysis/dt_result.json')
    print(len(info_list))
    flip_arr = np.array(flip_list)
    print(np.sum(flip_arr))

    print(len(info_list) - np.sum(flip_arr))

def average(config):
    cwe_ids = ['CWE119','CWE020',  'CWE125', 'CWE190', 'CWE400', 'CWE787']
    result_average = dict()
    result_average['0'] = []
    result_average['10'] = []
    result_average['20'] = []
    result_average['30'] = []
    result_average['cl_10'] = []
    result_average['cl_20'] = []
    result_average['cl_30'] = []
    result_average['dt_10'] = []
    result_average['dt_20'] = []
    result_average['dt_30'] = []
    result_average['ds_10'] = []
    result_average['ds_20'] = []
    result_average['ds_30'] = []
    metric_average = copy.deepcopy(result_average)
    for cwe in cwe_ids:
        path = os.path.join(config.res_folder, f'{config.name}_{cwe}.json')
        result_data = read_json(path)
        for key in result_average:
            keys = result_data.keys()
            if 'cl' in key and f'{cwe}_{key}' in keys:
                result_average[key].append(result_data[f'{cwe}_{key}']) 
            elif 'dt' in key and f'{cwe}_{key}' in keys:
                result_average[key].append(result_data[f'{cwe}_{key}']) 
            elif 'ds' in key and f'{cwe}_{key}' in keys:
                result_average[key].append(result_data[f'{cwe}_{key}']) 
            elif 'cl' not in key and 'dt' not in key and 'ds' not in key :
                result_average[key].append(result_data[f'{cwe}__{key}']) 
    # metric_average = dict()
    # metric_average['loss'] = 0
    # metric_average['fpr'] = 0
    # metric_average['precision'] = 0
    # metric_average['recall'] = 0
    # metric_average['accuracy'] = 0
    # metric_average['f1'] = 0
    metrics = ['loss', 'fpr', 'precision', 'recall', 'accuracy', 'f1']
    for key in metric_average:
        metric_average[key] = dict()
        for item in result_average[key]:
            
            for metric in metrics:
                if metric not in metric_average[key].keys():
                    metric_average[key][metric] = 0
                    metric_average[key][metric] += item[metric]
                else:

                    metric_average[key][metric] += item[metric]

    for key in metric_average:
        for metric in metric_average[key]:
            metric_average[key][metric] /= 6 
    
    
    pp.pprint(metric_average)
    noise_resistance = []
    for key in ['0', '10', '20', '30']:
        noise_resistance.append(metric_average[key]['f1'])
    noise_resistance = np.array(noise_resistance)
    pp.pprint({'noise_resistance': noise_resistance.var()})
            
    return metric_average

def count_test1(metric_average):
    result = dict()
    noise_levels = ['10', '20', '30']
    for noise in noise_levels:
        result[f'cl_{noise}'] = metric_average[f'cl_{noise}']['f1'] - metric_average[noise]['f1']
        if f'f1' in metric_average[f'dt_{noise}'].keys():
            result[f'dt_{noise}'] = metric_average[f'dt_{noise}']['f1'] - metric_average[noise]['f1']
    
    pp.pprint(result)
    


if __name__ == '__main__':
    # from cleanlab.pruning import get_noise_indices


    # result1 = statistic_dt_result('vuldeepecker', 'CWE119', 0.05)
    # result2 = statistic_cl_result('sysevr', 'CWE119', 0.07)
    # result3 = statistic_cl_result('sysevr', 'CWE119', 0.09)
    # print(result1)
    # print(result2)
    # print(result3)
    # statistic_cl_and_dt('deepwukong')
    # statistic_dt_result('deepwukong', 'CWE119_v1', 0.1)
    # statistic_dt_result('deepwukong', 'CWE787', 0.3)
    # statistic_cl_result('deepwukong', 'CWE787', 0.3)
    # statistic_cl_result('sysevr', 'CWE119', 0.3)
    # analysis_dt('deepwukong', 'CWE119', 0.1)
    # result1 = statistic_dt_result('sysevr', 'CWE787', 0.1)
    # result2 = statistic_cl_result('sysevr', 'CWE119', 0.2)
    # result3 = statistic_cl_result('sysevr', 'CWE119', 0.3)
    # result1 = statistic_cl_result('deepwukong', 'CWE119', 0.1)
    # result2 = statistic_cl_result('deepwukong', 'CWE119', 0.2)
    # result3 = statistic_cl_result('deepwukong', 'CWE119', 0.3)
    # result4 = statistic_cl_result('deepwukong', 'CWE119', 0.4)

    # result3 = statistic_cl_result('sysevr', 'CWE119_v2_bind', 0.3)

    arg_parser = ArgumentParser()
    # arg_parser.add_argument("model", type=str)
    # arg_parser.add_argument("--dataset", type=str, default=None)
    arg_parser.add_argument("--offline", action="store_true")
    # arg_parser.add_argument("--resume", type=str, default=None)
    args = arg_parser.parse_args()
    config = get_config_dwk('CWE190', 'stack', log_offline=args.offline)
    # config.data_folder = 'data/'
    config.res_folder = 'res1'
    config.noise_set = 'training'
    # # analysis_cl(config)
    # # statistic_ls_result(config=config, noise_rate=0.2, threshold = 25)
    # # statistic_cl_result(config, 0.1)
    # # statistic_cl_result(config, 0.2)
    statistic_cl_result(config, 0.1)
    statistic_cl_result(config, 0.2)
    statistic_cl_result(config, 0.3)

    # statistic_manual_dwk()
    # average = average(config=config)
    # count_test1(average)
    # statistic_all_cl_metric('reveal', 'res')
    # config.noise_rate = 0
    # analysis_cl(config=config)
    # metric = average(config)
    # print(metric)
    # count_test1(metric)
    # statistic_cl_result(config, 0.1)
    # statistic_cl_result(config, 0.2)
    # statistic_cl_result(config, 0.3)
    # statistic_cl_result(config, 0.1)
    # result = statistic_cl_result(config, 0)
    # result = statistic_cl_result(config, 0)
    # result = statistic_dt_result(config, 0.3)
    # result = statistic_cl_result(config, 0.2)
    # result = statistic_cl_result(config, 0.3)
    # print(result)
    # result = statistic_cl_result('deepwukong', 'CWE119', 0.3)
    # print(result)
    # result = statistic_cl_result('deepwukong', 'CWE119', 0.4)
    # print(result)
    # cl_result = read_json('res/deepwukong/cl_result/CWE119/10_percent_res.json')
    # labels = cl_result['s']
    # xfg_ids = cl_result['xfg_id']
    # flip = cl_result['flip']
    # pre_labels = cl_result['psx']
    # error_labels = cl_result['error_label']
    
    
    # error_labels = get_noise_indices(np.array(labels), np.array(pre_labels), num_to_remove_per_class=1000)
    # print(np.sum(error_labels))
    # flip = np.array(flip)
    # print(np.sum(flip[error_labels]))
    # with open("statistic_res.txt","a") as file:
    #    file.write(str(result)+"\n")
    # statistic_all_cl('deepwukong', 'CWE119')
    # data = read_json('/home/niexu/project/python/noise_reduce/data/CWES/CWE119_v2/0_percent/xfgs.json')
    # xfg_safe = []
    # for key in data:
    #     for xfg in data[key]:
    #         if xfg['target'] == 1:
    #            xfg_safe.append(xfg)
    # write_json(xfg_safe, 'xfg_vul.json')