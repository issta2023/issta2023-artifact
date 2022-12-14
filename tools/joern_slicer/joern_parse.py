import csv
from inspect import iscoroutinefunction
import os
from confident_learning import read_json, write_json
import shutil
from numpy import random
from tools.joern_slicer.slicing import get_data_label, get_slice_for_cdg, get_slice_for_cdg_sfv, label_for_mixed, label_for_paired
from utils.print_log import start_process, end_process
import sys
sys.path.append("..")
import xml.etree.ElementTree as ET
import json
import numpy as np
from tools.joern_slicer.uniqueJson import unique_xfgs, uniqueDir_with_flip, writeBigJson
CUR_DIR = os.path.dirname(os.path.abspath(__file__))



def joern_parse(data_path, cwe_id, gen_csv:bool=False):
    """
    @description  : use joern to parse c/cpp
    ---------
    @param  : data_path: c/cpp dir
    -------
    @Returns  : 
    output: joern/output
    os.path.abspath(data_path) : data_path absolute path 
    note: output + os.path.abspath(data_path) is csv_path
    -------
    """
    if cwe_id in ['BUFFER_OVERRUN', 'INTEGER_OVERFLOW', 'NULL_DEREFERENCE', 'MEMOREY_LEAK', 'BUFFER_OVERRUN_test', 'INTEGER_OVERFLOW_test']:
        output = CUR_DIR + '/joern/output_d2a'
    else:
        output = CUR_DIR + '/joern/output_{}'.format(cwe_id)
    
    cmd = CUR_DIR + '/joern/joern-parse {} {}'.format(output, data_path)
    print('CMD: '+cmd)
    if gen_csv:
        start_process('joern parse generate csv')
        os.system(cmd)
        end_process('joern parse generate csv')
    return output, os.path.abspath(data_path)


def add_pair_id_to_xfg(xfgs, idx):
    for xfg in xfgs:
        xfg['pair_id'] = idx

def xfg_label(source_code_dir, all_label_list, gen_csv:bool=False):
    """
    @description  : use joern to parse c/cpp
    ---------
    @param  : data_path: c/cpp dir
    -------
    @Returns  : xfg_list with label
    -------
    """
    
    xfg_list = []
    output_dir, abs_data_path = joern_parse(source_code_dir, gen_csv)

    for idx, label_info in enumerate(all_label_list):
        flaw_info = label_info['flaw']
        fix_info = label_info['fix']
        
        flaw_xfgs = get_data_label(flaw_info, output_dir, abs_data_path, type='flaw')
        fix_xfgs = get_data_label(fix_info, output_dir, abs_data_path, type='fix')
        if flaw_xfgs != [] and fix_xfgs != []:
            add_pair_id_to_xfg(xfgs=flaw_xfgs, idx=idx)
            xfg_list.extend(flaw_xfgs)
        
            add_pair_id_to_xfg(xfgs=fix_xfgs, idx=idx)
            xfg_list.extend(fix_xfgs)
    
    #??????
    md5Dict = uniqueDir_with_flip(xfg_list)
    xfgs = writeBigJson(md5Dict)
    return xfgs

def xfg_label_from_vul_info_list(cwe_id, vul_info_list, gen_csv:bool=False):
    """
    @description  : use joern to parse c/cpp
    ---------
    @param  : data_path: c/cpp dir
    -------
    @Returns  : xfg_list with label
    -------
    """
    
    xfg_list = []
    source_code_dir = '/home/niexu/dataset/CWES/{}/source-code'.format(cwe_id)
    output_dir, abs_data_path = joern_parse(source_code_dir, gen_csv)
    
    for idx, vul_info in enumerate(vul_info_list):
        
        
        flaw_xfgs = get_data_label(vul_info, output_dir, abs_data_path, type='flaw', dataset_type='sard')
        if flaw_xfgs != []:
           
            xfg_list.extend(flaw_xfgs)
        
    
    #??????
    md5Dict = unique_xfgs(xfg_list)
    xfgs = writeBigJson(md5Dict)
    return xfgs


def get_cdg_label(cwe_id, vul_info_list, method, gen_csv:bool=False):
    source_code_dir = '/home/public/rmt/niexu/datasets/CWES/{}/source-code'.format(cwe_id)
    output_dir, abs_data_path = joern_parse(source_code_dir, cwe_id, gen_csv)
    # output_dir = CUR_DIR + '/joern/output_{}'.format(cwe_id)
    all_info_list = []
    # output_path = 'data/{}/{}'.format(method, cwe_id)
    for vul_info in vul_info_list:
        
        data_instance = get_slice_for_cdg(vul_info, output_dir, abs_data_path)

        if data_instance == None:
            continue      
        info_list = write_cdg(vul_info, data_instance, method)
        if info_list != [] :
            all_info_list.extend(info_list)
    return all_info_list







def write_cdg(info_dict, data_instance, method):
    info_list = []
    if not data_instance:
        return info_list
    file_path = data_instance['file_path']
    vul_lines = info_dict['line']
    if method == 'sysevr':
        slices = data_instance['all_slices_sy']
    elif method == 'vuldeepecker':
        slices = data_instance['all_slices_vd']
    file_content = data_instance['file_content']

    if len(vul_lines) == 1 and vul_lines[0] == 0:
            return info_list
    for slis in slices:
        if(len(slis) < 3):
            continue
        flag = False
        for line in slis:
            if int(line) in vul_lines:
                flag = True
                break
        if flag:
            vul_line = int(line)
            target = 1
        else:
            vul_line = 0
            target = 0
            # info = file_path + '|' + 'vul_line:{}'.format(line) + '|' + 'pair_id:{}\n'.format(pair_id)
            # content = get_slice_content(file_content, slis)                   
                    
        info = dict()
        info['file_path'] = file_path
        info['line_no'] = slis
        info['vul_line'] = vul_line
        info['content'] = get_slice_content(file_content, slis)
        info['target'] = target
        info_list.append(info)
            # info_list.append(info + content + str(target) + "\n" +
            #                             "---------------------------------" + "\n")

    return info_list       

def get_slice_content(file_content, slis):
    """
    @description  : get file statements for slice
    ---------
    @param  :
    -------
    @Returns  :
    -------
    """
    content = []
    for line in slis:
        # content.append(file_content[line-1].strip())
        content.append(file_content[line-1].strip())  
    return content
   
def get_file_path_to_line(json_path):
    json_dict = []
    with open(json_path, 'r', encoding='utf8') as f:
        json_dict = json.load(f)
    fp_to_line = dict()
    for bd in json_dict:
        file_path = bd['file_path']
        key_line = bd['key_line']
        fp_to_line[file_path] = key_line
    return fp_to_line 

def create_source_code_dir(fp_to_line):
    
    source_dir = '/home/niexu/dataset/AliGongShouDao/C'
    target_dir = '/home/niexu/project/python/preprocess/joern_slicer/src'
    for fp in fp_to_line:
        source_path = os.path.join(source_dir, fp)
        target_path = os.path.join(target_dir, fp)
        print(source_path + ' ' + target_path)
        if not os.path.exists(os.path.split(target_path)[0]):
            os.makedirs(os.path.split(target_path)[0])
        shutil.copyfile(source_path, target_path)


def create_noise_pair():
    all_label_list = read_json(os.path.join('data', 
        'CWES', 'CWE119', 'all_label_list.json' ))
    random_lables_path = os.path.join('data', 'CWES', 'CWE119', 'random_labels.json')
    noise_info_path = os.path.join('data', 'CWES', 'CWE119', 'noise_info.json')
    random.seed(7)
    random.shuffle(all_label_list) 

    for idx,info in enumerate(all_label_list):
        info['pair_id'] = idx
        info['flip'] = False
    
    #devide train val test#

    sz = len(all_label_list)

    pair_ids = np.arange(sz)

    train_slice = list(range(sz // 10, sz))
    test_slice = list(range(0, sz // 10))
    # test_slice = list(range(sz // 10, sz // 5))

    train_pair_ids = pair_ids[train_slice]
    test_pair_ids = pair_ids[test_slice]

    #create noise for train set 

    noise_rates = [0, 0.1, 0.2, 0.3, 0.4]

    noise_info = dict()
    noise_info['train_pair_ids'] = train_pair_ids.tolist()
    noise_info['test_pair_ids'] = test_pair_ids.tolist()

    for noise_rate in noise_rates:
        noise_key = '{}_percent'.format(int(noise_rate * 100))
        noise_info[noise_key] = dict()
        noise_size = int(noise_rate * len(train_pair_ids))
        noise_pair_ids = random.choice(train_pair_ids, noise_size, replace=False)
        noise_info[noise_key]['noise_pair_ids'] = noise_pair_ids.tolist()
    write_json(all_label_list, random_lables_path)
    write_json(noise_info, noise_info_path)

def xfg_label_for_noise_reduce(cwe_id, noise_rate:float):
    random_labels_path = os.path.join('data', 'CWES', cwe_id, 'random_labels.json')
    noise_info_path = os.path.join('data', 'CWES', cwe_id, 'noise_info.json')
    noise_info = read_json(noise_info_path)
    noise_key =  '{}_percent'.format(int(noise_rate * 100))
    out_dir = os.path.join('data', 'CWES', cwe_id, noise_key)
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
    
    xfg_out_path = os.path.join(out_dir, 'xfgs.json')
    

    random_labels = np.array(read_json(random_labels_path))
    
    train_pair_ids = noise_info['train_pair_ids']
    test_pair_ids = noise_info['test_pair_ids']
    noise_pair_ids = noise_info[noise_key]['noise_pair_ids']

    train_labels = random_labels[train_pair_ids]
    test_pair_labels = random_labels[test_pair_ids]
    
    for label in train_labels:
        pair_id = label['pair_id']
        if pair_id in noise_pair_ids:
            label['flip'] = True
    source_code_dir = '/home/niexu/dataset/CWES/CWE119/source-code'
    train_xfgs = xfg_label_flip(source_code_dir, train_labels, False)

    
    test_xfgs = xfg_label_flip(source_code_dir, test_pair_labels, False)
    xfgs = dict()
    xfgs['train'] = train_xfgs
    xfgs['test'] = test_xfgs
    print(len(train_xfgs))
    print(len(test_xfgs))
    write_json(xfgs, xfg_out_path)



    return train_xfgs, test_xfgs

def xfg_label_flip(source_code_dir, labels, gen_csv):
    """
    @description  : use joern to parse c/cpp
    ---------
    @param  : data_path: c/cpp dir
    -------
    @Returns  : xfg_list with label
    -------
    """
    
    xfg_list = []
    output_dir, abs_data_path = joern_parse(source_code_dir, gen_csv)
    output_dir = CUR_DIR + '/joern/output_cwe119'
    for label_info in labels:
        
        form = label_info['form']
        if form == 'mixed':
            xfgs = label_for_mixed(label_info, output_dir, abs_data_path)
        elif form == 'pair':
            xfgs = label_for_paired(label_info, output_dir, abs_data_path)
        xfg_list.extend(xfgs)
    #??????
    md5Dict = uniqueDir_with_flip(xfg_list)
    xfgs = writeBigJson(md5Dict)
    return xfgs


    

if __name__ == "__main__":
    # create_noise_pair()
    pass    