import csv
import os
from utils.json_ops import write_json, read_json
import shutil
from numpy import random
from tools.joern_slicer.slicing import get_data_label_d2a, get_slice_for_cdg, get_slice_for_cdg_sfv, get_data_label_d2a_test
from utils.print_log import start_process, end_process
import sys
sys.path.append("..")
import xml.etree.ElementTree as ET
import json
import numpy as np
from utils.git_checkout import checkout_to
from tools.joern_slicer.uniqueJson import unique_xfgs, getMD5, writeBigJson_d2a
from tools.joern_slicer.joern_parse import joern_parse
from utils.json_ops import read_json, write_json
CUR_DIR = os.path.dirname(os.path.abspath(__file__))

def get_bug_type(bug_type):
    BUFFER_OVERRUN = ['BUFFER_OVERRUN_L1', 'BUFFER_OVERRUN_L2',
                        'BUFFER_OVERRUN_L3', 'BUFFER_OVERRUN_L4', 
                        'BUFFER_OVERRUN_L5', 'BUFFER_OVERRUN_S2',
                        'BUFFER_OVERRUN_U5']
    INTEGER_OVERFLOW = ['INTEGER_OVERFLOW_L1', 'INTEGER_OVERFLOW_L2',
                            'INTEGER_OVERFLOW_L5', 'INTEGER_OVERFLOW_R2',
                            'INTEGER_OVERFLOW_U5']
    NULL_DEREFERENCE = ['DANGLING_POINTER_DEREFERENCE',
                        'NULL_DEREFERENCE',
                        'NULLPTR_DEREFERENCE']   
    MEMOREY_LEAK = ['MEMORY_LEAK', 'PULSE_MEMORY_LEAK']  
    result = ''
    if bug_type in BUFFER_OVERRUN:
        result = 'BUFFER_OVERRUN'
    elif bug_type in INTEGER_OVERFLOW:
        result = 'INTEGER_OVERFLOW'
    elif bug_type in NULL_DEREFERENCE:
        result = 'NULL_DEREFERENCE'
    elif bug_type in MEMOREY_LEAK:
        result = 'MEMOREY_LEAK'
    else:
        result = None
    return result


def d2a_classify_as_bug_type(projects):
    """
    @description  :classsify d2a as bug type 
    ---------
    @param  :
    -------
    @Returns  :
    -------
    """
    
    
    label_info = dict()
    rears = ['_labeler_1.json', '_labeler_0.json']
    d2a_src_dir = '/home/niexu/dataset/vul/d2a/d2a_json'
    for project in projects:
        for rear in rears:
            if rear == '_labeler_1.json':
                info_type = 'vul'
            else:
                info_type = 'safe'
            json_file_path = os.path.join(d2a_src_dir, project + rear) 
            # print(json_file_path)
            json_list = read_json(json_file_path)
            # print(json_list)
            for json_str in json_list:
                label = json_str['label']
                sample_type = json_str['sample_type']
                bug_type = get_bug_type(json_str['bug_type']) 
                project = json_str['project']
                bug_info = json_str['bug_info']
                trace = json_str['trace']
                functions = json_str['functions']
                adjusted_bug_loc = json_str['adjusted_bug_loc']
                if sample_type == 'before_fix':
                    commit_id = json_str['versions']['before']
                elif sample_type == 'after_fix':
                    commit_id = json_str['versions']['after']
                # print(bug_type)
                if bug_type == None:
                    continue
                if bug_type not in label_info.keys():
                    label_info[bug_type] = list()

                if adjusted_bug_loc != None :
                    file_path = adjusted_bug_loc['file']
                    line = adjusted_bug_loc['line']
                else :
                    file_path = bug_info['file']
                    line = bug_info['line']
                info = dict()
                info['project'] = project
                info['commit_id'] = commit_id
                info['file_path'] = file_path
                info['line'] = line
                info['type'] = info_type
                label_info[bug_type].append(info)
    for bug_type in label_info:
        print(len(label_info[bug_type]))
        out_path = '/home/niexu/dataset/vul/d2a/label_json/{}.json'.format(bug_type)
        write_json(json_dict=label_info[bug_type] ,output=out_path)
        extract_label_file_code(label_json=label_info[bug_type])

def extract_label_file_code(label_json):
    last_commit_id = ''
    for info in label_json:
        project = info['project']
        commit_id = info['commit_id']
        file_path = info['file_path']
        source_path = os.path.join('/home/niexu/dataset/vul/d2a/source_code', project)
        target_path = os.path.join('/home/niexu/dataset/vul/d2a/tmp', project)
        

        source_file = os.path.join(target_path, file_path)
        target_file = os.path.join('/home/niexu/dataset/vul/d2a/extract_code', project, commit_id, file_path)
        if os.path.exists(target_file):
            print(target_file + ' has done!')
            continue
        if last_commit_id != commit_id:
            if os.path.exists(target_path):
                shutil.rmtree(target_path)
                print(target_path + ' exist ! remove it')
                shutil.copytree(source_path, target_path)
                checkout_to(target_path, commit_id, project)
            
        path = os.path.split(target_file)
        if not os.path.exists(path[0]):
            os.makedirs(path[0])
        shutil.copyfile(source_file, target_file)
        last_commit_id = commit_id

def get_d2a_label_list(d2a_bug_type:str):
    bug_types = ['BUFFER_OVERRUN', 'INTEGER_OVERFLOW', 'MEMOREY_LEAK', 'NULL_DEREFERENCE']
    if d2a_bug_type not in bug_types:
        raise RuntimeError('{} not in {} !'.format(d2a_bug_type, bug_types))
    label_json_path = '/home/niexu/dataset/vul/d2a/label_json/{}.json'.format(d2a_bug_type)
    label_json = read_json(label_json_path)

    
    flaw_hash_dict = dict()
    safe_hash_dict = dict()

    for label_info in label_json:
        project = label_info['project']
        commit_id = label_info['commit_id']
        file_path = label_info['file_path']
        line = label_info['line']
        b_type = label_info['type']
        src_rel_path = os.path.join(project, commit_id, file_path)
        info = dict()
        info['path'] = src_rel_path
        info['line'] = line
        info['type'] = b_type
        hash_str = getMD5(str(info))
        if b_type == 'vul':
            if hash_str not in flaw_hash_dict.keys():
               flaw_hash_dict[hash_str] = info
        else:
            if hash_str not in safe_hash_dict.keys():
               safe_hash_dict[hash_str] = info

    flaw_label_list = [flaw_hash_dict[key] for key in flaw_hash_dict]

    safe_label_list = [safe_hash_dict[key] for key in safe_hash_dict]


    return flaw_label_list, safe_label_list

def d2a_xfg_label(d2a_bug_type ,gen_csv:bool=False):
    """
    @description  : use joern to parse c/cpp
    ---------
    @param  : data_path: c/cpp dir
    -------
    @Returns  : xfg_list with label
    -------
    """
    source_code_dir = '/home/niexu/dataset/vul/d2a/extract_code'
    

    flaw_label_list, safe_label_list = get_d2a_label_list(d2a_bug_type)

    output_dir, abs_data_path = joern_parse(source_code_dir, d2a_bug_type, gen_csv)
    # output_dir = CUR_DIR + '/joern/output_{}'.format('d2a')
    all_xfgs = []
    np.random.seed(7)
    if len(safe_label_list) >= len(flaw_label_list) * 3:
        safe_label_list = np.random.choice(safe_label_list, 3*len(flaw_label_list), replace=False)
    else:
        safe_label_list = safe_label_list

    for flaw_info in flaw_label_list:

        flaw_xfgs = get_data_label_d2a(flaw_info, output_dir, abs_data_path, type='flaw')
        flaw_md5Dict = unique_xfgs(flaw_xfgs)
        flaw_xfgs = writeBigJson_d2a(flaw_md5Dict)
        all_xfgs.extend(flaw_xfgs)

    for safe_info in safe_label_list:
        
        safe_xfgs = get_data_label_d2a(safe_info, output_dir, abs_data_path, type='safe')
        safe_md5Dict = unique_xfgs(safe_xfgs)
        safe_xfgs = writeBigJson_d2a(safe_md5Dict)
        all_xfgs.extend(safe_xfgs)
    #??????
    md5Dict = unique_xfgs(all_xfgs)
    xfgs = writeBigJson_d2a(md5Dict)

    out_path = '/home/public/rmt/niexu/projects/python/noise_reduce/data/d2a/dwk/{}.json'.format(d2a_bug_type)
    write_json(json_dict=xfgs, output=out_path)
    return xfgs

def d2a_xfg_test_label(d2a_bug_type ,gen_csv:bool=False):
    """
    @description  : use joern to parse c/cpp
    ---------
    @param  : data_path: c/cpp dir
    -------
    @Returns  : xfg_list with label
    -------
    """
    source_code_dir = '/home/niexu/dataset/vul/d2a/extract_code'
    

    true_label_list_path = 'data/CWES/{}/raw/true_label_info.json'.format(d2a_bug_type)
    
    true_label_list = read_json(true_label_list_path)
    output_dir, abs_data_path = joern_parse(source_code_dir, d2a_bug_type, gen_csv)
    # output_dir = CUR_DIR + '/joern/output_{}'.format('d2a')
    all_xfgs = []
    

    for info in true_label_list:
        vul_info = dict()
        vul_info['path'] = info['file_path']
        vul_info['line'] = info['vul_line']
        flaw_xfgs = get_data_label_d2a_test(vul_info, output_dir, abs_data_path)
        all_xfgs.extend(flaw_xfgs)
    
    #??????
    md5Dict = unique_xfgs(all_xfgs)
    xfgs = writeBigJson_d2a(md5Dict)

    out_path = 'data/CWES/{}/raw/test.json'.format(d2a_bug_type)
    write_json(json_dict=xfgs, output=out_path)
    return xfgs

def d2a_cdg_label(d2a_bug_type, method, gen_csv:bool=False):
    source_code_dir = '/home/niexu/dataset/vul/d2a/extract_code'

    flaw_label_list, safe_label_list = get_d2a_label_list(d2a_bug_type)
    flaw_info_dict = dict()
    for flaw in flaw_label_list:
        path = flaw['path']
        line = flaw['line']
        if path not in flaw_info_dict.keys():
            flaw_info_dict[path] = list()
            flaw_info_dict[path].append(line)
        else:
            flaw_info_dict[path].append(line)
    # np.random.seed(7)
    # if len(safe_label_list) >= len(flaw_label_list) * 5:
    #     safe_label_list = np.random.choice(safe_label_list, 5*len(flaw_label_list), replace=False)
    # else:
    #     safe_label_list = safe_label_list
    output_dir, abs_data_path = joern_parse(source_code_dir, d2a_bug_type, gen_csv)

    # output_dir = CUR_DIR + '/joern/output_{}'.format('d2a')

    all_info_list = []

    # output_path = 'data/{}/{}'.format(method, cwe_id)

    # all_label_list = []
    # all_label_list.extend(flaw_label_list)
    # all_label_list.extend(safe_label_list)
    for path in flaw_info_dict:
        vul_info = dict()
        vul_info['path'] = path
        vul_info['line'] = flaw_info_dict[path]
        data_instance = get_slice_for_cdg(vul_info, output_dir, abs_data_path)

        if data_instance == None:
            continue      
        info_list = write_cdg_d2a(vul_info, data_instance, method, type='flaw')
        if info_list != [] :
            all_info_list.extend(info_list)
    # for info in all_info_list:
        # with open(output_path+'/all.txt',
        #                              "a",
        #                             encoding="utf-8",
        #                             errors="ignore") as f:
        #                 f.write(info)
        #                 f.close()
    # write_json(all_info_list, output_path+'/{}_raw.json'.format(cwe_id) )
    return all_info_list

def d2a_cdg_test_label(d2a_bug_type, method, gen_csv:bool=False):
    source_code_dir = '/home/niexu/dataset/vul/d2a/extract_code'

    true_label_list_path = 'data/{}/{}/raw/true_label_info.json'.format(method,d2a_bug_type)
    true_label_list = read_json(true_label_list_path)
    output_dir, abs_data_path = joern_parse(source_code_dir, d2a_bug_type, gen_csv)
    all_info_list = []
    for info in true_label_list:
        vul_info = dict()
        vul_info['path'] = info['file_path']
        vul_info['line'] = info['vul_line']
        data_instance = get_slice_for_cdg(vul_info, output_dir, abs_data_path)
        if data_instance == None:
            continue      
        info_list = write_test_cdg_d2a(vul_info, data_instance, method)
        if info_list != [] :
            all_info_list.extend(info_list)
    # out_put_path = 'data/{}/{}/test_data_raw.json'.format(method,d2a_bug_type)
    return all_info_list

def write_test_cdg_d2a(info_dict, data_instance, method):
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


    for slis in slices:
        if(len(slis) < 3):
            continue
        info = dict()
        flag = False
        for line in slis:
            if int(line) == vul_lines:
                flag = True
                break
        if flag:
            target = 1
        else:
            target = 0
            # info = file_path + '|' + 'vul_line:{}'.format(line) + '|' + 'pair_id:{}\n'.format(pair_id)
            # content = get_slice_content(file_content, slis)                         
        
        info['file_path'] = file_path
        info['vul_line'] = vul_lines
        info['content'] = get_slice_content(file_content, slis)
        info['target'] = target
        info_list.append(info)
            # info_list.append(info + content + str(target) + "\n" +
            #                             "---------------------------------" + "\n")

    return info_list 


def write_cdg_d2a(info_dict, data_instance, method, type):
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

    
    for slis in slices:
        if(len(slis) < 3):
            continue
        info = dict()
        vul_line = 0
        flag = False
        for line in slis:
            if int(line) in vul_lines:
                flag = True
                vul_line = int(line)
                break
        if flag:
            target = 1
        else:
            target = 0
            # info = file_path + '|' + 'vul_line:{}'.format(line) + '|' + 'pair_id:{}\n'.format(pair_id)
            # content = get_slice_content(file_content, slis)                   
        # if type == 'vul':
        #     target = 1
        # else:
        #     target = 0         
        
        info['file_path'] = file_path
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