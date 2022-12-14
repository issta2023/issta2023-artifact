#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@Description:       :This file contains functions that generate noise label for each vulnerable detection method
@Date     :2021/10/15 18:46:56
@Author      :ives-nx
@version      :1.0
'''
from utils.json_ops import read_json, write_json
import os
import numpy as np
def gen_noise_for_dwk(config):
    """
    @description  :for deepwukong training set
    ---------
    @param  :
    -------
    @Returns  :
    -------
    """
    data_path = os.path.join(config.data_folder, 'CWES', '{}/{}.json'.format(config.dataset.name, config.dataset.name)) 
    out_path = os.path.join(config.data_folder, 'CWES', '{}/training_noise_info.json'.format(config.dataset.name))
    data = read_json(data_path)
    sz = len(data)
    train_slice = slice(sz // 5, sz)
    train_data = data[train_slice]
    noise_rates = [0, 0.1, 0.2, 0.3]
    noise_info = dict()
    for noise_rate in noise_rates:
        noise_key = '{}_percent'.format(int(noise_rate * 100))
        noise_info[noise_key] = dict()
        
        xfg_ids = []
        for xfg in train_data:
            xfg_ids.append(xfg['xfg_id'])
        np.random.seed(7)
        noise_xfg_ids = np.random.choice(xfg_ids, int(len(xfg_ids) * noise_rate), replace=False).tolist()

        
        print(len(noise_xfg_ids))
        noise_info[noise_key]['noise_xfg_ids'] = noise_xfg_ids
    write_json(noise_info, out_path)

def gen_noise_for_cdg(config):
    """
    @description  :for sysevr and vuldeepecker training set
    ---------
    @param  :
    -------
    @Returns  :
    -------
    """
    data_path = os.path.join(config.data_folder, config.name, '{}/{}.json'.format(config.dataset.name, config.dataset.name)) 
    out_path = os.path.join(config.data_folder, config.name, '{}/training_noise_info.json'.format(config.dataset.name))
    data = read_json(data_path)
    sz = len(data)
    print(sz)
    train_slice = slice(sz // 5, sz)
    train_data = data[train_slice]
    noise_rates = [0, 0.1, 0.2, 0.3]
    noise_info = dict()
    for noise_rate in noise_rates:
        noise_key = '{}_percent'.format(int(noise_rate * 100))
        noise_info[noise_key] = dict()
        
        xfg_ids = []
        for xfg in train_data:
            xfg_ids.append(xfg['xfg_id'])
        np.random.seed(7)
        noise_xfg_ids = np.random.choice(xfg_ids, int(len(xfg_ids) * noise_rate), replace=False).tolist()

        
        print(len(noise_xfg_ids))
        noise_info[noise_key]['noise_xfg_ids'] = noise_xfg_ids
    write_json(noise_info, out_path)

def gen_true_label(bug_type):
    d2a_true_label_path = f'/home/niexu/dataset/vul/d2a/test/{bug_type}.json'
    d2a_true_labels = read_json(d2a_true_label_path)
    true_lable_info = list()

    for info in d2a_true_labels:
        commit_hash = info['commit_id']['before']
        project = info['project']
        file = info['file']
        line = info['line']
        bug_type = info['bug_type']
        file_path = os.path.join(project, commit_hash, file)
        bug_info = dict()
        bug_info['file_path'] = file_path
        bug_info['vul_line'] = line
        true_lable_info.append(bug_info)

    return true_lable_info

def gen_noise_for_dwk_d2a(config):
    data_path = os.path.join(config.data_folder, 'CWES', '{}/{}.json'.format(config.dataset.name, config.dataset.name)) 
    out_path = os.path.join(config.data_folder, 'CWES', '{}_flip/noise_info.json'.format(config.dataset.name))
    out_data_path = os.path.join(config.data_folder, 'CWES', '{}_flip/{}_flip.json'.format(config.dataset.name, config.dataset.name))
    true_label_info_path = os.path.join(config.data_folder, 'CWES', '{}/true_label_info.json'.format(config.dataset.name))
    data = read_json(data_path)
    true_label_info = read_json(true_label_info_path)
    noise_xfg_ids = set()
    for xfg in data:
        for info in true_label_info:
            if xfg['file_path'] == info['file_path'] and xfg['vul_line'] == info['vul_line']:
                xfg['target'] = xfg['target'] ^ 1
                xfg['flip'] = not xfg['flip']
                noise_xfg_ids.add(xfg['xfg_id'])
                break
    noise_info = dict()
    noise_info['d2a'] = dict()
    noise_info['0_percent'] = dict()
    noise_info['d2a']['noise_xfg_ids'] = list(noise_xfg_ids)
    noise_info['0_percent']['noise_xfg_ids'] = []
    write_json(noise_info, out_path)
    write_json(data, out_data_path)
    print(len(noise_xfg_ids))

def gen_noise_for_cdg_d2a(config):
    data_path = os.path.join(config.data_folder, config.name, '{}/{}.json'.format(config.dataset.name, config.dataset.name)) 
    out_path = os.path.join(config.data_folder, config.name, '{}_flip/noise_info.json'.format(config.dataset.name))
    out_data_path = os.path.join(config.data_folder, config.name, '{}_flip/{}_flip.json'.format(config.dataset.name, config.dataset.name))

    data = read_json(data_path)
    true_label_info = gen_true_label(config.dataset.name)
    noise_xfg_ids = set()
    for xfg in data:
        for info in true_label_info:
            if xfg['file_path'] == info['file_path'] and xfg['vul_line'] == info['vul_line']:
                xfg['val'] = xfg['val'] ^ 1
                xfg['flip'] = not xfg['flip']
                noise_xfg_ids.add(xfg['xfg_id'])
                break
    noise_info = dict()
    noise_info['d2a'] = dict()
    noise_info['0_percent'] = dict()
    noise_info['d2a']['noise_xfg_ids'] = list(noise_xfg_ids)
    noise_info['0_percent']['noise_xfg_ids'] = []
    write_json(noise_info, out_path)
    write_json(data, out_data_path)
    print(len(noise_xfg_ids))