#!/usr/bin/env python
# -*- encoding: utf-8 -*-

from genericpath import exists
import os
from os.path import join, isdir
import csv

from tools.joern_slicer.real_world_symbolic import clean_gadget,  tokenize_gadget_tolist

CUR_DIR = os.path.dirname(os.path.abspath(__file__))
def extract_line_number(idx, nodes):
    while idx >= 0:
        c_node = nodes[idx]
        if 'location' in c_node.keys():
            location = c_node['location']
            if location.strip() != '':
                try:
                    ln = int(location.split(':')[0])
                    return ln
                except:
                    pass
        idx -= 1
    return -1


def read_csv(csv_file_path):
    data = []
    with open(csv_file_path) as fp:
        header = fp.readline()
        header = header.strip()
        h_parts = [hp.strip() for hp in header.split('\t')]
        for line in fp:
            line = line.strip()
            instance = {}
            lparts = line.split('\t')
            for i, hp in enumerate(h_parts):
                if i < len(lparts):
                    content = lparts[i].strip()
                else:
                    content = ''
                instance[hp] = content
            data.append(instance)
        return data


def extract_nodes_with_location_info(nodes):
    # Will return an array identifying the indices of those nodes in nodes array,
    # another array identifying the node_id of those nodes
    # another array indicating the line numbers
    # all 3 return arrays should have same length indicating 1-to-1 matching.
    node_indices = []
    node_ids = []
    line_numbers = []
    node_id_to_line_number = {}
    for node_index, node in enumerate(nodes):
        assert isinstance(node, dict)
        if 'location' in node.keys():
            location = node['location']
            if location == '':
                continue
            line_num = int(location.split(':')[0])
            node_id = node['key'].strip()
            node_indices.append(node_index)
            node_ids.append(node_id)
            line_numbers.append(line_num)
            node_id_to_line_number[node_id] = line_num
    return node_indices, node_ids, line_numbers, node_id_to_line_number


def create_adjacency_list(line_numbers,
                          node_id_to_line_numbers,
                          edges,
                          data_dependency_only=False):
    adjacency_list = {}
    for ln in set(line_numbers):
        adjacency_list[ln] = [set(), set()]
    for edge in edges:
        edge_type = edge['type'].strip()
        if True:  #edge_type in ['IS_AST_PARENT', 'FLOWS_TO']:
            start_node_id = edge['start'].strip()
            end_node_id = edge['end'].strip()
            if start_node_id not in node_id_to_line_numbers.keys(
            ) or end_node_id not in node_id_to_line_numbers.keys():
                continue
            start_ln = node_id_to_line_numbers[start_node_id]
            end_ln = node_id_to_line_numbers[end_node_id]
            if not data_dependency_only:
                if edge_type == 'CONTROLS':  #Control Flow edges
                    adjacency_list[start_ln][0].add(end_ln)
            if edge_type == 'REACHES':  # Data Flow edges
                adjacency_list[start_ln][1].add(end_ln)
    return adjacency_list


def create_forward_slice(adjacency_list, line_no):
    sliced_lines = set()
    sliced_lines.add(line_no)
    stack = list()
    stack.append(line_no)
    while len(stack) != 0:
        cur = stack.pop()
        if cur not in sliced_lines:
            sliced_lines.add(cur)
        adjacents = adjacency_list[cur]
        for node in adjacents:
            if node not in sliced_lines:
                stack.append(node)
    sliced_lines = sorted(sliced_lines)
    return sliced_lines


def combine_control_and_data_adjacents(adjacency_list):
    cgraph = {}
    data_graph = {}
    for ln in adjacency_list:
        cgraph[ln] = set()
        cgraph[ln] = cgraph[ln].union(adjacency_list[ln][0])
        cgraph[ln] = cgraph[ln].union(adjacency_list[ln][1])

        data_graph[ln] = set()
        data_graph[ln] = data_graph[ln].union(adjacency_list[ln][1])
    return cgraph, data_graph


def invert_graph(adjacency_list):
    igraph = {}
    for ln in adjacency_list.keys():
        igraph[ln] = set()
    for ln in adjacency_list:
        adj = adjacency_list[ln]
        for node in adj:
            igraph[node].add(ln)
    return igraph
    pass


def create_backward_slice(adjacency_list, line_no):
    inverted_adjacency_list = invert_graph(adjacency_list)
    return create_forward_slice(inverted_adjacency_list, line_no)

def get_slice_for_cdg(info_dict, output_dir, abs_file_path):
    
    sensi_api_path = CUR_DIR + "/resources/sensiAPI.txt"
    


    with open(sensi_api_path, "r", encoding="utf-8") as f:
        sensi_api_set = set([api.strip() for api in f.read().split(",")])

    
    path = info_dict['path']
    vul_line = info_dict['line']

    src = os.path.join(abs_file_path, path)
    csv_root = output_dir + src
    
    nodes_path = join(csv_root, "nodes.csv")
    edges_path = join(csv_root, "edges.csv")
    if not exists(nodes_path):
        return None
    with open(nodes_path, "r") as f:
        nodes = [node for node in csv.DictReader(f, delimiter='\t')]
    call_lines = set()
    array_lines = set()
    ptr_lines = set()
    arithmatic_lines = set()
    if len(nodes) == 0:
        return 
    for node_idx, node in enumerate(nodes):
        ntype = node['type'].strip()
        if ntype == 'CallExpression':
            function_name = nodes[node_idx + 1]['code']
            if function_name is None or function_name.strip() == '':
                continue
            if function_name.strip() in sensi_api_set:
                line_no = extract_line_number(node_idx, nodes)
                if line_no > 0:
                    call_lines.add(line_no)
        elif ntype == 'ArrayIndexing':
            line_no = extract_line_number(node_idx, nodes)
            if line_no > 0:
                array_lines.add(line_no)
        elif ntype == 'PtrMemberAccess':
            line_no = extract_line_number(node_idx, nodes)
            if line_no > 0:
                ptr_lines.add(line_no)
        elif node['operator'].strip() in ['+', '-', '*', '/']:
            line_no = extract_line_number(node_idx, nodes)
            if line_no > 0:
                arithmatic_lines.add(line_no)
    nodes = read_csv(nodes_path)
    edges = read_csv(edges_path)
    node_indices, node_ids, line_numbers, node_id_to_ln = extract_nodes_with_location_info(nodes)
    adjacency_list = create_adjacency_list(line_numbers, node_id_to_ln, edges,
                                           False)
    combined_graph, data_graph = combine_control_and_data_adjacents(adjacency_list)
    array_slices = []
    array_slices_bdir = []
    call_slices = []
    call_slices_bdir = []
    arith_slices = []
    arith_slices_bdir = []
    ptr_slices = []
    ptr_slices_bdir = []
    all_slices = []
    all_slices_vd = []
    all_keys = set()
    _keys = set()
    for slice_ln in call_lines:
        forward_sliced_lines = create_forward_slice(combined_graph, slice_ln)
        backward_sliced_lines = create_backward_slice(combined_graph, slice_ln)
        all_slice_lines = forward_sliced_lines
        all_slice_lines.extend(backward_sliced_lines)
        all_slice_lines = sorted(list(set(all_slice_lines)))
        vdp_bk_lines = create_backward_slice(data_graph, slice_ln)
        vdp_for_lines = create_forward_slice(data_graph, slice_ln)
        vdp_bk_lines.extend(vdp_for_lines)
        vdp_lines = sorted(list(set(vdp_bk_lines)))
        call_slices.append(vdp_lines)
        call_slices_bdir.append(all_slice_lines)
        all_slices.append(all_slice_lines)
        all_slices_vd.append(vdp_lines)
    _keys = set()
    for slice_ln in array_lines:
        forward_sliced_lines = create_forward_slice(combined_graph, slice_ln)
        backward_sliced_lines = create_backward_slice(combined_graph, slice_ln)
        all_slice_lines = forward_sliced_lines
        all_slice_lines.extend(backward_sliced_lines)
        all_slice_lines = sorted(list(set(all_slice_lines)))
        vdp_bk_lines = create_backward_slice(data_graph, slice_ln)
        vdp_for_lines = create_forward_slice(data_graph, slice_ln)
        vdp_bk_lines.extend(vdp_for_lines)
        vdp_lines = sorted(list(set(vdp_bk_lines)))
        array_slices.append(vdp_lines)
        array_slices_bdir.append(all_slice_lines)
        all_slices.append(all_slice_lines)
        all_slices_vd.append(vdp_lines)
    _keys = set()
    for slice_ln in arithmatic_lines:
        forward_sliced_lines = create_forward_slice(combined_graph, slice_ln)
        backward_sliced_lines = create_backward_slice(combined_graph, slice_ln)
        all_slice_lines = forward_sliced_lines
        all_slice_lines.extend(backward_sliced_lines)
        all_slice_lines = sorted(list(set(all_slice_lines)))
        vdp_bk_lines = create_backward_slice(data_graph, slice_ln)
        vdp_for_lines = create_forward_slice(data_graph, slice_ln)
        vdp_bk_lines.extend(vdp_for_lines)
        vdp_lines = sorted(list(set(vdp_bk_lines)))
        arith_slices.append(vdp_lines)
        arith_slices_bdir.append(all_slice_lines)
        all_slices.append(all_slice_lines)
        all_slices_vd.append(vdp_lines)
    _keys = set()
    for slice_ln in ptr_lines:
        forward_sliced_lines = create_forward_slice(combined_graph, slice_ln)
        backward_sliced_lines = create_backward_slice(combined_graph, slice_ln)
        all_slice_lines = forward_sliced_lines
        all_slice_lines.extend(backward_sliced_lines)
        all_slice_lines = sorted(list(set(all_slice_lines)))
        vdp_bk_lines = create_backward_slice(data_graph, slice_ln)
        vdp_for_lines = create_forward_slice(data_graph, slice_ln)
        vdp_bk_lines.extend(vdp_for_lines)
        vdp_lines = sorted(list(set(vdp_bk_lines)))
        ptr_slices.append(vdp_lines)
        ptr_slices_bdir.append(all_slice_lines)
        all_slices.append(all_slice_lines)
        all_slices_vd.append(vdp_lines)

    file_content = [] 
    with open(src, 'r', encoding='utf8', errors="ignore") as f:
        file_content = f.readlines()

    data_instance = {
        'file_path': path,
        'call_slices_vd': call_slices,
        'call_slices_sy': call_slices_bdir,
        'array_slices_vd': array_slices,
        'array_slices_sy': array_slices_bdir,
        'arith_slices_vd': arith_slices,
        'arith_slices_sy': arith_slices_bdir,
        'ptr_slices_vd': ptr_slices,
        'ptr_slices_sy': ptr_slices_bdir,
        'all_slices_sy': all_slices,
        'all_slices_vd': all_slices_vd,
        'file_content' : file_content
    }

    return data_instance

def get_slice_for_cdg_sfv(info_dict, output_dir, abs_file_path, type):
    sensi_api_path = CUR_DIR + "/resources/sensiAPI.txt"
    
    path = info_dict['path']
    vul_line = info_dict['line']

    src = os.path.join(abs_file_path, path)
    csv_root = output_dir + src

    with open(sensi_api_path, "r", encoding="utf-8") as f:
        sensi_api_set = set([api.strip() for api in f.read().split(",")])


    
    nodes_path = join(csv_root, "nodes.csv")
    edges_path = join(csv_root, "edges.csv")
    with open(nodes_path, "r") as f:
        nodes = [node for node in csv.DictReader(f, delimiter='\t')]
    call_lines = set()
    array_lines = set()
    ptr_lines = set()
    arithmatic_lines = set()
    if len(nodes) == 0:
        return 
    nodes = read_csv(nodes_path)
    edges = read_csv(edges_path)
    node_indices, node_ids, line_numbers, node_id_to_ln = extract_nodes_with_location_info(nodes)
    adjacency_list = create_adjacency_list(line_numbers, node_id_to_ln, edges,
                                           False)
    combined_graph, data_graph = combine_control_and_data_adjacents(adjacency_list)
    
    
    
    
    all_slices = []
    all_slices_vd = []
    all_keys = set()
    _keys = set()
    for slice_ln in [vul_line]:
        forward_sliced_lines = create_forward_slice(combined_graph, slice_ln)
        backward_sliced_lines = create_backward_slice(combined_graph, slice_ln)
        all_slice_lines = forward_sliced_lines
        all_slice_lines.extend(backward_sliced_lines)
        all_slice_lines = sorted(list(set(all_slice_lines)))
        vdp_bk_lines = create_backward_slice(data_graph, slice_ln)
        vdp_for_lines = create_forward_slice(data_graph, slice_ln)
        vdp_bk_lines.extend(vdp_for_lines)
        vdp_lines = sorted(list(set(vdp_bk_lines)))
        all_slices.append(all_slice_lines)
        all_slices_vd.append(vdp_lines)

    file_content = [] 
    with open(src, 'r', encoding='utf8', errors="ignore") as f:
        file_content = f.readlines()

    data_instance = {
        'file_path': path,
        'all_slices_sy': all_slices,
        'all_slices_vd': all_slices_vd,
        'file_content' : file_content
    }

    return data_instance    

def combined_graph_to_dict(combined_graph, file_path):
    file_contents = list()   
    with open( file_path,
                "r",
                encoding="utf-8",
                errors="ignore") as f:
        file_contents=f.readlines()
    pdg = dict()
    nodes = []
    edges = []
    line_to_id_dict = {}
    for index, ln in enumerate(combined_graph, start=0) :
        node_info = dict()
        node_info['id'] = index
        node_info['line'] = ln
        node_info['label'] = file_contents[int(ln)-1]
        nodes.append(node_info)
        line_to_id_dict[ln] = index
    e_index = 0
    for ln_start in combined_graph:
        for ln_end in combined_graph[ln_start]:
            start = line_to_id_dict[ln_start]
            end = line_to_id_dict[ln_end]
            edge_info = dict()
            edge_info['id'] = e_index
            edge_info['source'] = start
            edge_info['target'] = end
            edges.append(edge_info)
    pdg['file'] = file_path
    pdg['nodes'] = nodes
    pdg['edges'] = edges
    return pdg

def get_all_xfg_node_forward(node_id, node_id_to_line, edges, xfg_nodes_list, visted):
    visted.add(node_id)
    if node_id_to_line[str(node_id)] != 0 and node_id not in xfg_nodes_list:
        xfg_nodes_list.append(node_id)
    for edge in edges:
        if edge['source'] == node_id and edge['target'] not in visted:
            get_all_xfg_node_forward(edge['target'], node_id_to_line, edges, xfg_nodes_list, visted)

def get_all_xfg_node_backward(node_id, node_id_to_line, edges, xfg_nodes_list, visted):
    visted.add(node_id)
    if node_id_to_line[str(node_id)] != 0 and node_id not in xfg_nodes_list:
        xfg_nodes_list.append(node_id)
    for edge in edges:
        if edge['target'] == node_id and edge['source'] not in visted:
            get_all_xfg_node_backward(edge['source'], node_id_to_line, edges, xfg_nodes_list, visted)

def xfg_generator(pdg_json, line):
    # pdg_json = dict()
    # with open(file_name+'-PDG.json', 'r', encoding = 'utf-8') as f:
    #     pdg_json = json.load(f)
    #     f.close()

    node_line_to_id = dict()
    node_id_to_line = dict()

    nodes = pdg_json['nodes']
    edges = pdg_json['edges']

    for node in nodes:
        node_id_to_line[str(node['id'])] = str(node['line'])
        node_line_to_id[str(node['line'])] = str(node['id'])
    sensi_id = None
    if str(line) in node_line_to_id.keys():
        sensi_id = int(node_line_to_id[str(line)])
    if sensi_id == None:
        return None
    xfg_nodes_list = list()
    froward_visted = set()
    backward_visted = set()
    get_all_xfg_node_forward(sensi_id, node_id_to_line, edges, xfg_nodes_list, froward_visted)
    get_all_xfg_node_backward(sensi_id, node_id_to_line, edges, xfg_nodes_list, backward_visted)

   

    xfg = dict()
    xfg_nodes = list()
    xfg_edges = list()
    idx = 0
    xfg_node_line_to_id = dict()
    for node in nodes:
        if node['id'] in xfg_nodes_list:
            new_node = dict()
            new_node['id'] = idx
            new_node['line'] = node['line']
            new_node['label'] = node['label'].replace('\t', '')
            xfg_node_line_to_id[str(node['line'])] = idx
            idx = idx + 1
            xfg_nodes.append(new_node)
    xfg_edges_list = list()
    for edge in edges:
        source = edge['source']
        target = edge['target']
        if source in xfg_nodes_list and target in xfg_nodes_list:
            xfg_edges_list.append(node_id_to_line[str(source)]+"_"+node_id_to_line[str(target)])
    
    for idx, edge in enumerate(xfg_edges_list, start=0): 
        lines = edge.split("_")
        source = lines[0]
        target = lines[1]
        new_edge = dict()
        new_edge['id'] = idx
        new_edge['source'] = xfg_node_line_to_id[source]
        new_edge['target'] = xfg_node_line_to_id[target]
        xfg_edges.append(new_edge)
    
    xfg['file'] = pdg_json['file']
    xfg['sensi_line'] = line
    xfg['nodes'] = xfg_nodes
    xfg['edges'] = xfg_edges

    
    # with open(file_name+'-XFG.json', 'w', encoding = 'utf-8') as f:
    #     json.dump(xfg, f, indent = 2)
    #     f.close()
    return xfg

def get_data_label(info_dict, output_dir, abs_file_path, type, dataset_type):
    """
    @description  : slicing xfg from interesting point for srad
    ---------
    @param  :
    -------
    @Returns  :
    -------
    """
    if dataset_type not in ['d2a', 'sard']:
        raise RuntimeError('{} not in {}'.format(dataset_type, ['d2a', 'sard']))
    
    
    
    sensi_api_path =join(CUR_DIR, "resources/sensiAPI.txt") 
    
    # cpg_list = [join(root, fl) for fl in os.listdir(root) if isdir(join(root, fl))]
    path = info_dict['path']
    vul_lines = info_dict['line']

    #?????????vulline == 0 ????????????????????????
    if len(vul_lines) == 1 and vul_lines[0] == 0:
        return []


    src = os.path.join(abs_file_path, path)
    csv_root = output_dir + src

    with open(sensi_api_path, "r", encoding="utf-8") as f:
        sensi_api_set = set([api.strip() for api in f.read().split(",")])
       

    
    
    nodes_path = join(csv_root, "nodes.csv")
    edges_path = join(csv_root, "edges.csv")
    if not exists(nodes_path):
        with open('no_csv_path.txt', 'a', encoding='utf8') as f:
            f.write(csv_root + '\n')
        return []
    with open(nodes_path, "r") as f:
        nodes = [node for node in csv.DictReader(f, delimiter='\t')]
    call_lines = set()
    array_lines = set()
    ptr_lines = set()
    arithmatic_lines = set()
    if len(nodes) == 0:
        return []
    for node_idx, node in enumerate(nodes):
        ntype = node['type'].strip()
        if ntype == 'CallExpression':
            function_name = nodes[node_idx + 1]['code']
            if function_name is None or function_name.strip() == '':
                continue
            if function_name.strip() in sensi_api_set:
                line_no = extract_line_number(node_idx, nodes)
                if line_no > 0:
                    call_lines.add(line_no)
        elif ntype == 'ArrayIndexing':
            line_no = extract_line_number(node_idx, nodes)
            if line_no > 0:
                array_lines.add(line_no)
        elif ntype == 'PtrMemberAccess':
            line_no = extract_line_number(node_idx, nodes)
            if line_no > 0:
                ptr_lines.add(line_no)
        elif node['operator'].strip() in ['+', '-', '*', '/']:
            line_no = extract_line_number(node_idx, nodes)
            if line_no > 0:
                arithmatic_lines.add(line_no)


    nodes = read_csv(nodes_path)
    edges = read_csv(edges_path)
    node_indices, node_ids, line_numbers, node_id_to_ln = extract_nodes_with_location_info(nodes)
    adjacency_list = create_adjacency_list(line_numbers, node_id_to_ln, edges,
                                               False)

    combined_graph, data_graph = combine_control_and_data_adjacents(adjacency_list)
    pdg = combined_graph_to_dict(combined_graph, src)

    if dataset_type == 'sard':
        key_lines = call_lines | arithmatic_lines | array_lines | ptr_lines
    elif dataset_type == 'd2a':
        key_lines = vul_lines
    new_xfg_list = []
    for line in key_lines:
        line = str(line)
        xfg = xfg_generator(pdg, line)
        if xfg == None:
            continue
        new_xfg = dict()
        xfg_nodes = xfg['nodes']
        xfg_edges = xfg['edges']
        new_xfg_nodes = list()
        nodes_line = list()
        xfg_lines = list()
        new_xfg_edges = list()
        if len(xfg_nodes) == 0:
            continue
        for node in xfg_nodes:
            new_xfg_nodes.append(str(node['line']))
            xfg_lines.append(str(node['line']))
            nodes_line.append(node['label'])
        for edge in xfg_edges:
            new_xfg_edges.append([edge['source'], edge['target']])
        new_xfg['nodes-lineNo'] = new_xfg_nodes
        new_xfg['keyLine'] = line   
        new_xfg['edges-No'] = new_xfg_edges
        

        # if len(vul_lines) == 1 and vul_lines[0] == 0:
        #     new_xfg['target'] = 1
        #     new_xfg['nodes-line'] = nodes_line
        #     new_xfg['nodes-line-sym'] = tokenize_gadget_tolist(clean_gadget(nodes_line, sensi_api_set))
        #     if len(nodes_line) > 2:
        #         new_xfg_list.append(new_xfg)
        # else :
            # ?????? xfg ????????? vul_line  ?????? vul_line == 0(??????xfg??????)
        #????????????3??????xfg
        if len(xfg_lines) <= 2:
            continue
        flag = False
        for line in xfg_lines:
            if int(line) in vul_lines:
                flag = True
                break
        if flag:
            new_xfg['target'] = 1
        else:
            new_xfg['target'] = 0
        new_xfg['filePath'] = path
        new_xfg['nodes-line'] = nodes_line
        new_xfg['nodes-line-sym'] = tokenize_gadget_tolist(clean_gadget(nodes_line, sensi_api_set))
        new_xfg_list.append(new_xfg)
    
    return new_xfg_list

def get_data_label_devign(info_dict, output_dir, abs_file_path, type):
    """
    @description  : slicing xfg from interesting point for srad
    ---------
    @param  :
    -------
    @Returns  :
    -------
    """
    sensi_api_path =join(CUR_DIR, "resources/sensiAPI.txt") 
    
    # cpg_list = [join(root, fl) for fl in os.listdir(root) if isdir(join(root, fl))]
    path = info_dict['path']
    vul_lines = info_dict['line']

    # src = os.path.join(abs_file_path, path)
    src = path
    csv_root = output_dir + path

    with open(sensi_api_path, "r", encoding="utf-8") as f:
        sensi_api_set = set([api.strip() for api in f.read().split(",")])
       
    nodes_path = join(csv_root, "nodes.csv")
    edges_path = join(csv_root, "edges.csv")
    if not exists(nodes_path):
        with open('no_csv_path.txt', 'a', encoding='utf8') as f:
            # f.write(csv_root + '\n')
            print(csv_root)
        return []
    with open(nodes_path, "r") as f:
        nodes = [node for node in csv.DictReader(f, delimiter='\t')]
    call_lines = set()
    array_lines = set()
    ptr_lines = set()
    arithmatic_lines = set()
    if len(nodes) == 0:
        return []
    for node_idx, node in enumerate(nodes):
        ntype = node['type'].strip()
        if ntype == 'CallExpression':
            function_name = nodes[node_idx + 1]['code']
            if function_name is None or function_name.strip() == '':
                continue
            if function_name.strip() in sensi_api_set:
                line_no = extract_line_number(node_idx, nodes)
                if line_no > 0:
                    call_lines.add(line_no)
        elif ntype == 'ArrayIndexing':
            line_no = extract_line_number(node_idx, nodes)
            if line_no > 0:
                array_lines.add(line_no)
        elif ntype == 'PtrMemberAccess':
            line_no = extract_line_number(node_idx, nodes)
            if line_no > 0:
                ptr_lines.add(line_no)
        elif node['operator'].strip() in ['+', '-', '*', '/']:
            line_no = extract_line_number(node_idx, nodes)
            if line_no > 0:
                arithmatic_lines.add(line_no)


    nodes = read_csv(nodes_path)
    edges = read_csv(edges_path)
    node_indices, node_ids, line_numbers, node_id_to_ln = extract_nodes_with_location_info(nodes)
    adjacency_list = create_adjacency_list(line_numbers, node_id_to_ln, edges,
                                               False)

    combined_graph, data_graph = combine_control_and_data_adjacents(adjacency_list)
    pdg = combined_graph_to_dict(combined_graph, src)

   
    key_lines = call_lines | arithmatic_lines | array_lines | ptr_lines
    new_xfg_list = []
    for line in key_lines:
        line = str(line)
        xfg = xfg_generator(pdg, line)
        if xfg == None:
            continue
        new_xfg = dict()
        xfg_nodes = xfg['nodes']
        xfg_edges = xfg['edges']
        new_xfg_nodes = list()
        nodes_line = list()
        xfg_lines = list()
        new_xfg_edges = list()
        if len(xfg_nodes) == 0:
            continue
        for node in xfg_nodes:
            new_xfg_nodes.append(str(node['line']))
            xfg_lines.append(str(node['line']))
            nodes_line.append(node['label'])
        for edge in xfg_edges:
            new_xfg_edges.append([edge['source'], edge['target']])
        new_xfg['nodes-lineNo'] = new_xfg_nodes
        new_xfg['keyLine'] = line   
        new_xfg['edges-No'] = new_xfg_edges
        
        #????????????3??????xfg
        if len(xfg_lines) <= 2:
            continue
        flag = False
        # print(xfg_lines)
        # print(vul_lines)
        vul_line = []
        for line in xfg_lines:
            if int(line) in vul_lines:
                flag = True
                vul_line.append(int(line))
                # break
        # if not flag:
        #     continue
        if type == 'flaw':
            if not flag:
                continue
            new_xfg['target'] = 1
        else:
            new_xfg['target'] = 0
        new_xfg['file_path'] = path
        new_xfg['vul_line'] = vul_line
        new_xfg['nodes-line'] = nodes_line
        new_xfg['nodes-line-sym'] = tokenize_gadget_tolist(clean_gadget(nodes_line, sensi_api_set))
        new_xfg_list.append(new_xfg)
    
    return new_xfg_list

def get_data_label_d2a(info_dict, output_dir, abs_file_path, type):
    """
    @description  : slicing xfg from interesting point for srad
    ---------
    @param  :
    -------
    @Returns  :
    -------
    """

    
    
    
    sensi_api_path =join(CUR_DIR, "resources/sensiAPI.txt") 
    
    # cpg_list = [join(root, fl) for fl in os.listdir(root) if isdir(join(root, fl))]
    path = info_dict['path']
    vul_lines = info_dict['line']

    src = os.path.join(abs_file_path, path)
    csv_root = output_dir + src

    with open(sensi_api_path, "r", encoding="utf-8") as f:
        sensi_api_set = set([api.strip() for api in f.read().split(",")])
       

    
    
    nodes_path = join(csv_root, "nodes.csv")
    edges_path = join(csv_root, "edges.csv")
    if not exists(nodes_path):
        with open('no_csv_path.txt', 'a', encoding='utf8') as f:
            f.write(csv_root + '\n')
        return []
    with open(nodes_path, "r") as f:
        nodes = [node for node in csv.DictReader(f, delimiter='\t')]
    call_lines = set()
    array_lines = set()
    ptr_lines = set()
    arithmatic_lines = set()
    if len(nodes) == 0:
        return []
    for node_idx, node in enumerate(nodes):
        ntype = node['type'].strip()
        if ntype == 'CallExpression':
            function_name = nodes[node_idx + 1]['code']
            if function_name is None or function_name.strip() == '':
                continue
            if function_name.strip() in sensi_api_set:
                line_no = extract_line_number(node_idx, nodes)
                if line_no > 0:
                    call_lines.add(line_no)
        elif ntype == 'ArrayIndexing':
            line_no = extract_line_number(node_idx, nodes)
            if line_no > 0:
                array_lines.add(line_no)
        elif ntype == 'PtrMemberAccess':
            line_no = extract_line_number(node_idx, nodes)
            if line_no > 0:
                ptr_lines.add(line_no)
        elif node['operator'].strip() in ['+', '-', '*', '/']:
            line_no = extract_line_number(node_idx, nodes)
            if line_no > 0:
                arithmatic_lines.add(line_no)


    nodes = read_csv(nodes_path)
    edges = read_csv(edges_path)
    node_indices, node_ids, line_numbers, node_id_to_ln = extract_nodes_with_location_info(nodes)
    adjacency_list = create_adjacency_list(line_numbers, node_id_to_ln, edges,
                                               False)

    combined_graph, data_graph = combine_control_and_data_adjacents(adjacency_list)
    pdg = combined_graph_to_dict(combined_graph, src)

   
    key_lines = call_lines | arithmatic_lines | array_lines | ptr_lines
    new_xfg_list = []
    for line in key_lines:
        line = str(line)
        xfg = xfg_generator(pdg, line)
        if xfg == None:
            continue
        new_xfg = dict()
        xfg_nodes = xfg['nodes']
        xfg_edges = xfg['edges']
        new_xfg_nodes = list()
        nodes_line = list()
        xfg_lines = list()
        new_xfg_edges = list()
        if len(xfg_nodes) == 0:
            continue
        for node in xfg_nodes:
            new_xfg_nodes.append(str(node['line']))
            xfg_lines.append(str(node['line']))
            nodes_line.append(node['label'])
        for edge in xfg_edges:
            new_xfg_edges.append([edge['source'], edge['target']])
        new_xfg['nodes-lineNo'] = new_xfg_nodes
        new_xfg['keyLine'] = line   
        new_xfg['edges-No'] = new_xfg_edges
        

        # if len(vul_lines) == 1 and vul_lines[0] == 0:
        #     new_xfg['target'] = 1
        #     new_xfg['nodes-line'] = nodes_line
        #     new_xfg['nodes-line-sym'] = tokenize_gadget_tolist(clean_gadget(nodes_line, sensi_api_set))
        #     if len(nodes_line) > 2:
        #         new_xfg_list.append(new_xfg)
        # else :
            # ?????? xfg ????????? vul_line  ?????? vul_line == 0(??????xfg??????)
        #????????????3??????xfg
        if len(xfg_lines) <= 2:
            continue
        flag = False
        for line in xfg_lines:
            if int(line) == vul_lines:
                flag = True
                break
        # if not flag:
        #     continue

        if flag:
            new_xfg['target'] = 1
        else:
            new_xfg['target'] = 0
        new_xfg['file_path'] = path
        new_xfg['vul_line'] = vul_lines
        new_xfg['nodes-line'] = nodes_line
        new_xfg['nodes-line-sym'] = tokenize_gadget_tolist(clean_gadget(nodes_line, sensi_api_set))
        new_xfg_list.append(new_xfg)
    
    return new_xfg_list


def get_data_label_d2a_test(info_dict, output_dir, abs_file_path):
    """
    @description  : slicing xfg from interesting point for srad
    ---------
    @param  :
    -------
    @Returns  :
    -------
    """

    
    
    
    sensi_api_path =join(CUR_DIR, "resources/sensiAPI.txt") 
    
    # cpg_list = [join(root, fl) for fl in os.listdir(root) if isdir(join(root, fl))]
    path = info_dict['path']
    vul_lines = info_dict['line']

    src = os.path.join(abs_file_path, path)
    csv_root = output_dir + src

    with open(sensi_api_path, "r", encoding="utf-8") as f:
        sensi_api_set = set([api.strip() for api in f.read().split(",")])
       

    
    
    nodes_path = join(csv_root, "nodes.csv")
    edges_path = join(csv_root, "edges.csv")
    if not exists(nodes_path):
        with open('no_csv_path.txt', 'a', encoding='utf8') as f:
            f.write(csv_root + '\n')
        return []
    with open(nodes_path, "r") as f:
        nodes = [node for node in csv.DictReader(f, delimiter='\t')]
    call_lines = set()
    array_lines = set()
    ptr_lines = set()
    arithmatic_lines = set()
    if len(nodes) == 0:
        return []
    for node_idx, node in enumerate(nodes):
        ntype = node['type'].strip()
        if ntype == 'CallExpression':
            function_name = nodes[node_idx + 1]['code']
            if function_name is None or function_name.strip() == '':
                continue
            if function_name.strip() in sensi_api_set:
                line_no = extract_line_number(node_idx, nodes)
                if line_no > 0:
                    call_lines.add(line_no)
        elif ntype == 'ArrayIndexing':
            line_no = extract_line_number(node_idx, nodes)
            if line_no > 0:
                array_lines.add(line_no)
        elif ntype == 'PtrMemberAccess':
            line_no = extract_line_number(node_idx, nodes)
            if line_no > 0:
                ptr_lines.add(line_no)
        elif node['operator'].strip() in ['+', '-', '*', '/']:
            line_no = extract_line_number(node_idx, nodes)
            if line_no > 0:
                arithmatic_lines.add(line_no)


    nodes = read_csv(nodes_path)
    edges = read_csv(edges_path)
    node_indices, node_ids, line_numbers, node_id_to_ln = extract_nodes_with_location_info(nodes)
    adjacency_list = create_adjacency_list(line_numbers, node_id_to_ln, edges,
                                               False)

    combined_graph, data_graph = combine_control_and_data_adjacents(adjacency_list)
    pdg = combined_graph_to_dict(combined_graph, src)

   
    key_lines = call_lines | arithmatic_lines | array_lines | ptr_lines
    new_xfg_list = []
    for line in key_lines:
        line = str(line)
        xfg = xfg_generator(pdg, line)
        if xfg == None:
            continue
        new_xfg = dict()
        xfg_nodes = xfg['nodes']
        xfg_edges = xfg['edges']
        new_xfg_nodes = list()
        nodes_line = list()
        xfg_lines = list()
        new_xfg_edges = list()
        if len(xfg_nodes) == 0:
            continue
        for node in xfg_nodes:
            new_xfg_nodes.append(str(node['line']))
            xfg_lines.append(str(node['line']))
            nodes_line.append(node['label'])
        for edge in xfg_edges:
            new_xfg_edges.append([edge['source'], edge['target']])
        new_xfg['nodes-lineNo'] = new_xfg_nodes
        new_xfg['keyLine'] = line   
        new_xfg['edges-No'] = new_xfg_edges
        

        # if len(vul_lines) == 1 and vul_lines[0] == 0:
        #     new_xfg['target'] = 1
        #     new_xfg['nodes-line'] = nodes_line
        #     new_xfg['nodes-line-sym'] = tokenize_gadget_tolist(clean_gadget(nodes_line, sensi_api_set))
        #     if len(nodes_line) > 2:
        #         new_xfg_list.append(new_xfg)
        # else :
            # ?????? xfg ????????? vul_line  ?????? vul_line == 0(??????xfg??????)
        #????????????3??????xfg
        if len(xfg_lines) <= 2:
            continue
        flag = False
        for line in xfg_lines:
            if int(line) == vul_lines:
                flag = True
                break
        if flag:
            target = 1
        else:
            target = 0

        new_xfg['target'] = target
        new_xfg['file_path'] = path
        new_xfg['vul_line'] = vul_lines
        new_xfg['nodes-line'] = nodes_line
        new_xfg['nodes-line-sym'] = tokenize_gadget_tolist(clean_gadget(nodes_line, sensi_api_set))
        new_xfg_list.append(new_xfg)
    
    return new_xfg_list

def get_pdg_and_keylines(abs_file_path, path, output_dir):
    
    
    # cpg_list = [join(root, fl) for fl in os.listdir(root) if isdir(join(root, fl))]


    src = os.path.join(abs_file_path, path)
    csv_root = output_dir + src

    
       
    sensi_api_path =join(CUR_DIR, "resources/sensiAPI.txt") 
    with open(sensi_api_path, "r", encoding="utf-8") as f:
        sensi_api_set = set([api.strip() for api in f.read().split(",")])
    
    
    nodes_path = join(csv_root, "nodes.csv")
    edges_path = join(csv_root, "edges.csv")
    if not exists(nodes_path):
        with open('no_csv_path.txt', 'a', encoding='utf8') as f:
            f.write(csv_root + '\n')
        return [], []
    with open(nodes_path, "r") as f:
        nodes = [node for node in csv.DictReader(f, delimiter='\t')]
    call_lines = set()
    array_lines = set()
    ptr_lines = set()
    arithmatic_lines = set()
    if len(nodes) == 0:
        return []
    for node_idx, node in enumerate(nodes):
        ntype = node['type'].strip()
        if ntype == 'CallExpression':
            function_name = nodes[node_idx + 1]['code']
            if function_name is None or function_name.strip() == '':
                continue
            if function_name.strip() in sensi_api_set:
                line_no = extract_line_number(node_idx, nodes)
                if line_no > 0:
                    call_lines.add(line_no)
        elif ntype == 'ArrayIndexing':
            line_no = extract_line_number(node_idx, nodes)
            if line_no > 0:
                array_lines.add(line_no)
        elif ntype == 'PtrMemberAccess':
            line_no = extract_line_number(node_idx, nodes)
            if line_no > 0:
                ptr_lines.add(line_no)
        elif node['operator'].strip() in ['+', '-', '*', '/']:
            line_no = extract_line_number(node_idx, nodes)
            if line_no > 0:
                arithmatic_lines.add(line_no)


    nodes = read_csv(nodes_path)
    edges = read_csv(edges_path)
    node_indices, node_ids, line_numbers, node_id_to_ln = extract_nodes_with_location_info(nodes)
    adjacency_list = create_adjacency_list(line_numbers, node_id_to_ln, edges,
                                               False)

    combined_graph, data_graph = combine_control_and_data_adjacents(adjacency_list)
    pdg = combined_graph_to_dict(combined_graph, src)

    
    key_lines = call_lines | arithmatic_lines | array_lines | ptr_lines

    return pdg, key_lines



def label_one_of_pair(info_dict, output_dir, abs_file_path, pair_id, type, flip):

    label_line = info_dict['line']
    path = info_dict['path']

    sensi_api_path =join(CUR_DIR, "resources/sensiAPI.txt") 
    with open(sensi_api_path, "r", encoding="utf-8") as f:
        sensi_api_set = set([api.strip() for api in f.read().split(",")])
    
    
    pdg, key_lines = get_pdg_and_keylines(abs_file_path, path, output_dir)

    if pdg == [] or key_lines == [] :
        return []
    
    new_xfg_list = []
    for line in key_lines:
        line = str(line)
        xfg = xfg_generator(pdg, line)
        if xfg == None:
            continue
        new_xfg = dict()
        xfg_nodes = xfg['nodes']
        xfg_edges = xfg['edges']
        new_xfg_nodes = list()
        nodes_line = list()
        xfg_lines = list()
        new_xfg_edges = list()
        if len(xfg_nodes) == 0:
            continue
        for node in xfg_nodes:
            new_xfg_nodes.append(str(node['line']))
            xfg_lines.append(str(node['line']))
            nodes_line.append(node['label'])
        for edge in xfg_edges:
            new_xfg_edges.append([edge['source'], edge['target']])
        new_xfg['nodes-lineNo'] = new_xfg_nodes
        new_xfg['keyLine'] = line   
        new_xfg['edges-No'] = new_xfg_edges
        new_xfg['filePath'] = path
        new_xfg['nodes-line'] = nodes_line
        new_xfg['nodes-line-sym'] = tokenize_gadget_tolist(clean_gadget(nodes_line, sensi_api_set))
        new_xfg['pair_id'] = pair_id
        if len(xfg_lines) > 2:
            new_xfg_list.append(new_xfg)
        
    result_xfgs = list()

    if flip:
        # ?????? vul ??? fix   fix  ??? vul
        if type == 'flaw':
            for xfg in new_xfg_list:
                xfg_lines = xfg['nodes-lineNo']
                if str(label_line) in xfg_lines or label_line == 0:
                    xfg['target'] = 0
                    xfg['flip'] = True
                else:
                    xfg['target'] = 0
                    xfg['flip'] = False
                result_xfgs.append(xfg)
        elif type == 'fix':
            for xfg in new_xfg_list:
                xfg_lines = xfg['nodes-lineNo']
                if str(label_line) in xfg_lines or label_line == 0:
                    xfg['target'] = 1
                    xfg['flip'] = True
                else:
                    xfg['target'] = 0
                    xfg['flip'] = False
                result_xfgs.append(xfg)
    else:

        if type == 'flaw':
            for xfg in new_xfg_list:
                xfg_lines = xfg['nodes-lineNo']
                if str(label_line) in xfg_lines or label_line == 0:
                    xfg['target'] = 1
                    xfg['flip'] = False
                else:
                    xfg['target'] = 0
                    xfg['flip'] = False
                result_xfgs.append(xfg)
        elif type == 'fix':
            for xfg in new_xfg_list:
                xfg['target'] = 0
                xfg['flip'] = False
                result_xfgs.append(xfg)

    return result_xfgs
    
def label_for_paired(info_dict, output_dir, abs_file_path):
    """
    @description  : slice and label xfg for sard dataset in paired form file
    ---------
    @param  :
    -------
    @Returns  :
    -------
    """

    flip = info_dict['flip']
    pair_id = info_dict['pair_id']

    flaw_dict = info_dict['flaw']
    fix_dict = info_dict['fix']

    flaw_xfgs = label_one_of_pair(flaw_dict, output_dir, abs_file_path, pair_id, 'flaw', flip)
    fix_xfgs = label_one_of_pair(fix_dict, output_dir, abs_file_path, pair_id, 'fix', flip)

    result_xfgs = []
    result_xfgs.extend(flaw_xfgs)
    result_xfgs.extend(fix_xfgs)
    return result_xfgs


def label_for_mixed(info_dict, output_dir, abs_file_path):
    """
    @description  : slice and label xfg for sard dataset in mixed form file
    ---------
    @param  :
    -------
    @Returns  :
    -------
    """

    flip = info_dict['flip']
    pair_id = info_dict['pair_id']
    path = info_dict['path']
    vul_lines = info_dict['vul_line']
    fix_lines = info_dict['fix_line']

    sensi_api_path =join(CUR_DIR, "resources/sensiAPI.txt") 
    with open(sensi_api_path, "r", encoding="utf-8") as f:
        sensi_api_set = set([api.strip() for api in f.read().split(",")])
    
    
    pdg, key_lines = get_pdg_and_keylines(abs_file_path, path, output_dir)

    
    new_xfg_list = []
    for line in key_lines:
        line = str(line)
        xfg = xfg_generator(pdg, line)
        if xfg == None:
            continue
        new_xfg = dict()
        xfg_nodes = xfg['nodes']
        xfg_edges = xfg['edges']
        new_xfg_nodes = list()
        nodes_line = list()
        xfg_lines = list()
        new_xfg_edges = list()
        if len(xfg_nodes) == 0:
            continue
        for node in xfg_nodes:
            new_xfg_nodes.append(str(node['line']))
            xfg_lines.append(str(node['line']))
            nodes_line.append(node['label'])
        for edge in xfg_edges:
            new_xfg_edges.append([edge['source'], edge['target']])
        new_xfg['nodes-lineNo'] = new_xfg_nodes
        new_xfg['keyLine'] = line   
        new_xfg['edges-No'] = new_xfg_edges
        new_xfg['filePath'] = path
        new_xfg['nodes-line'] = nodes_line
        new_xfg['nodes-line-sym'] = tokenize_gadget_tolist(clean_gadget(nodes_line, sensi_api_set))
        new_xfg['pair_id'] = pair_id
        if len(xfg_lines) > 2:
            new_xfg_list.append(new_xfg)

    #?????????????????????xfg????????????
    result_xfgs = list()
    if flip:
        for xfg in new_xfg_list:
            xfg_lines = xfg['nodes-lineNo']
            state = -1
            for xfg_line in xfg_lines:
                xfg_line = int(xfg_line)
                if xfg_line in vul_lines and xfg_line not in fix_lines:
                    state = 0 
                    break
                elif xfg_line in fix_lines and xfg_line not in vul_lines:
                    state = 1
                    break
                elif xfg_line in fix_lines and xfg_line in vul_lines:
                    state = 2
                    break
            if state == 2:
                continue
            elif state == 0:
                xfg['target'] = 0
                xfg['flip'] = True
            elif state == 1:
                xfg['target'] = 1
                xfg['flip'] = True
            elif state == -1:
                xfg['target'] = 0
                xfg['flip'] = False
            result_xfgs.append(xfg)
    else:
        for xfg in new_xfg_list:
            xfg_lines = xfg['nodes-lineNo']
            target = 0
            for vul_line in vul_lines:
                if str(vul_line) in xfg_lines:
                    target = 1
                    break
            xfg['target'] = target
            xfg['flip'] = False
            result_xfgs.append(xfg)    

    return result_xfgs


def get_data_label_sfv(info_dict, output_dir, abs_file_path, type):
    """
    @description  : slicing xfg from vul line for srad
    ---------
    @param  :
    -------
    @Returns  :
    -------
    """
    
    
    sensi_api_path = join(CUR_DIR, "resources/sensiAPI.txt") 
    
    # cpg_list = [join(root, fl) for fl in os.listdir(root) if isdir(join(root, fl))]
    path = info_dict['path']
    vul_line = info_dict['line']

    src = os.path.join(abs_file_path, path)
    csv_root = output_dir + src

    with open(sensi_api_path, "r", encoding="utf-8") as f:
        sensi_api_set = set([api.strip() for api in f.read().split(",")])
       

    
    
    nodes_path = join(csv_root, "nodes.csv")
    edges_path = join(csv_root, "edges.csv")
    if not exists(nodes_path):
        with open('no_csv_path.txt', 'a', encoding='utf8') as f:
            f.write(csv_root + '\n')
        return []
    with open(nodes_path, "r") as f:
        nodes = [node for node in csv.DictReader(f, delimiter='\t')]
    nodes = read_csv(nodes_path)
    edges = read_csv(edges_path)
    node_indices, node_ids, line_numbers, node_id_to_ln = extract_nodes_with_location_info(nodes)
    adjacency_list = create_adjacency_list(line_numbers, node_id_to_ln, edges,
                                               False)

    combined_graph, data_graph = combine_control_and_data_adjacents(adjacency_list)
    pdg = combined_graph_to_dict(combined_graph, src)
    key_lines = [vul_line]
    new_xfg_list = []
    for line in key_lines:
        line = str(line)
        xfg = xfg_generator(pdg, line)
        if xfg == None:
            continue
        new_xfg = dict()
        xfg_nodes = xfg['nodes']
        xfg_edges = xfg['edges']
        new_xfg_nodes = list()
        nodes_line = list()
        xfg_lines = list()
        new_xfg_edges = list()
        if len(xfg_nodes) == 0:
            continue
        for node in xfg_nodes:
            new_xfg_nodes.append(str(node['line']))
            xfg_lines.append(str(node['line']))
            nodes_line.append(node['label'])
        for edge in xfg_edges:
            new_xfg_edges.append([edge['source'], edge['target']])
        new_xfg['nodes-lineNo'] = new_xfg_nodes
        new_xfg['keyLine'] = line   
        new_xfg['edges-No'] = new_xfg_edges
        vul_lines = []
        vul_idx = []
    
        for idx,xfg_line in enumerate(xfg_lines, start=0) :
        
            if int(xfg_line) == vul_line:
                vul_lines.append(xfg_line)
                vul_idx.append(idx)
            
        if len(vul_lines) > 0 or vul_line == 0:
            # ?????? xfg ????????? vul_line  ?????? vul_line == 0(??????xfg??????) 
            if type == 'flaw':
                new_xfg['target'] = 1
            else:
                new_xfg['target'] = 0
            new_xfg['filePath'] = path
            new_xfg['nodes-line'] = nodes_line
            new_xfg['nodes-line-sym'] = tokenize_gadget_tolist(clean_gadget(nodes_line, sensi_api_set))
            if len(nodes_line) >= 2:
                new_xfg_list.append(new_xfg)
    
    
    return new_xfg_list


    