import os
from utils.json_ops import read_json, write_file, write_json
from utils.print_log import start_process, end_process
import pprint as pp
CUR_DIR = os.path.dirname(os.path.abspath(__file__))
import csv
import numpy as np
import json


# 我这里只考虑与CFG node相关的边
edgeType_cfg_node = {
    'FLOWS_TO': 0,  # Control Flow, 只涉及到CFG node
    'CONTROLS': 1,  # Control Dependency edge, 只涉及到CFG node
    'REACHES': 2, #数据流图, 只涉及到CFG node

}

total_edge_attrs = np.eye(len(edgeType_cfg_node))


def clean_graph(graph: dict):
    '''
    :param graph: 需要清理的图，joern生成的CPG会出现一些问题，比如1个CFG node会被解析成
    :return: 清理后的图
    '''
    # 建立从line number到statement type的索引
    line2stat_type = dict()
    for i in range(len(graph["node-line-number"])):
        line2stat_type[graph["node-line-number"][i]] = graph["statement-type"][i]


    # 合并line number
    node_lines = sorted(list(set(graph["node-line-number"])))
    line2new_idx = {line: i for i, line in enumerate(node_lines)}
    index_map = [line2new_idx[line] for line in graph["node-line-number"]]

    # 合并content内容
    contents = [[] for i in range(len(node_lines))]
    for i in range(len(graph["node-line-number"])):
        line_number = graph["node-line-number"][i]
        idx = line2new_idx[line_number]

        graph["node-line-content"][i] = graph["node-line-content"][i].replace("L '\\\\0'", "L'\0'")
        graph["node-line-content"][i] = graph["node-line-content"][i].replace("L '", "L'")

        contents[idx].append(graph["node-line-content"][i])

    contents = [' '.join(content) for content in contents]

    # 合并statement type内容
    statement_types = [line2stat_type[line] for line in node_lines]

    # 合并edge
    ## control flow edge
    cf_edge = []
    for edge in graph["control_flow_edge"]:
        start = index_map[edge[0]]
        end = index_map[edge[1]]
        if start != end:
            cf_edge.append([start, end])

    ## control dependency edge
    cd_edge = []
    for edge in graph["control_dependency_edge"]:
        start = index_map[edge[0]]
        end = index_map[edge[1]]
        if start != end:
            cd_edge.append([start, end])

    ## data dependency edge
    dd_edge = []
    for edge in graph["data_dependency_edge"]:
        start = index_map[edge[0]]
        end = index_map[edge[1]]
        if start != end:
            dd_edge.append([start, end])

    ## data dependency value
    dd_value = dict()
    for key, value in graph["data_dependency_value"].items():
        start = index_map[key[0]]
        end = index_map[key[1]]
        if start != end:
            dd_value[str((start, end))] = value

    graph["node-line-number"] = node_lines
    graph["node-line-content"] = contents
    graph["statement-type"] = statement_types

    graph["control_flow_edge"] = cf_edge
    graph["control_dependency_edge"] = cd_edge
    graph["data_dependency_edge"] = dd_edge
    graph["data_dependency_value"] = dd_value

    return graph


def inputGeneration(nodeCSV, edgeCSV, edge_type_map=edgeType_cfg_node, cfg_only=True):
    # 一个graph信息如下保存：
    # dict-> edge, node-line-number, node-line-content, functionName, edge-feature
    #
    all_graph = list()
    graph_idx = 0

    edge_type = ["control_flow_edge", "control_dependency_edge", "data_dependency_edge"]

    nodekey2graph_idx = {} # 用于指名该node属于哪个graph

    nc = open(nodeCSV, 'r')
    nodes = csv.DictReader(nc, delimiter='\t')
    nodeMap = dict()  # 将csv中的nodekey映射为最终图中的node_idx

    node_idx = 0
    for idx, node in enumerate(nodes):
        node_type = node['type']  # IdentifierDeclStatement之类
        if node_type == 'File':
            continue

        if node_type == "Function": # 创建新graph
            gInput = dict()

            gInput["node-line-number"] = list()
            gInput["node-line-content"] = list()
            gInput["statement-type"] = list()
            gInput["functionName"] = node['code'].strip()
            all_graph.append(gInput)
            graph_idx += 1
            node_idx = 0
            continue

        cfgNode = node['isCFGNode'].strip()
        if (cfgNode == '' or cfgNode == 'False') and cfg_only: # 如果这个node不是cfgNode并且只要cfgNode
            continue
        nodeKey = node['key']  # 结点索引号

        location = node['location']
        if location == '':
            continue
        line_num = int(location.split(':')[0])
        node_content = node['code'].strip()


        all_graph[graph_idx - 1]["node-line-number"].append(line_num)
        all_graph[graph_idx - 1]["node-line-content"].append(node_content)
        all_graph[graph_idx - 1]["statement-type"].append(node_type)

        nodekey2graph_idx[nodeKey] = graph_idx - 1

        nodeMap[nodeKey] = node_idx
        node_idx += 1
    if node_idx == 0 or node_idx >= 500:
        return None


    # 处理edge
    for graph in all_graph:
        graph["control_flow_edge"] = list()
        graph["control_dependency_edge"] = list()
        graph["data_dependency_edge"] = list()
        graph["data_dependency_value"] = dict()

    ec = open(edgeCSV, 'r')
    reader = csv.DictReader(ec, delimiter='\t')
    for e in reader:
        start, end, eType = e["start"], e["end"], e["type"]
        if eType != "IS_FILE_OF":
            if not start in nodeMap or not end in nodeMap or not eType in edge_type_map:
                continue
            graph_idx = nodekey2graph_idx[start]

            edge = [nodeMap[start], nodeMap[end]] # 暂时不考虑边的分类
            all_graph[graph_idx][edge_type[edge_type_map[eType]]].append(edge)

            if eType == "REACHES":
                value = e["var"] # ddg变量
                all_graph[graph_idx]["data_dependency_value"][tuple(edge)] = value

    return_graph = list()

    for graph in all_graph: # 对每个graph进行合并操作
        if len(graph["node-line-number"]) <= 1 or graph["functionName"] == "main":
            continue
        graph = clean_graph(graph)
        return_graph.append(graph)

    return return_graph



def clean_json(datas, path):
    if datas is None:
        return []
    for graph in datas:
        for i in range(len(graph["node-line-content"])):
            graph["node-line-content"][i] = graph["node-line-content"][i].replace("L '\\\\0'", "L'\0'")
            graph["node-line-content"][i] = graph["node-line-content"][i].replace("L '", "L'")
        graph['file_path'] = path
    return datas



def joern_parse(data_path, gen_csv:bool=False):
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
   
    output = os.path.join(os.path.dirname(data_path), 'csv')
    
    cmd = CUR_DIR + '/joern/joern-parse {} {}'.format(output, data_path)
    print('CMD: '+cmd)
    if gen_csv:
        start_process('joern parse generate csv')
        os.system(cmd)
        end_process('joern parse generate csv')
    return output, os.path.abspath(data_path)

def write_reveal_data_to_cfile():
    benign_reveal_data_path = '/home/public/rmt/niexu/dataset/vul/reveal_data/non-vulnerables.json'
    vul_reveal_data_path = '/home/public/rmt/niexu/dataset/vul/reveal_data/vulnerables.json'
    benign_funcs = [code['code'] for code in read_json(benign_reveal_data_path)]
    vul_funcs = [code['code'] for code in read_json(vul_reveal_data_path)]
    
    for idx, code in enumerate(benign_funcs):
        path = f'/home/public/rmt/niexu/dataset/vul/reveal_data/source_code/benign/{idx}.c'
        write_file(code, path, is_need_create_dir=True)
        
    for idx, code in enumerate(vul_funcs):
        path = f'/home/public/rmt/niexu/dataset/vul/reveal_data/source_code/vulnerable/{idx}.c'
        write_file(code, path, is_need_create_dir=True)
        
def write_devign_data_to_cfile():
    source_data_path = '/home/public/rmt/niexu/dataset/vul/devign/function.json'
    all_functions = read_json(source_data_path)
    benign_funcs = []
    vul_funcs = []
    for func in all_functions:
        if func['target'] == 0:
            benign_funcs.append(func['func'])
        else:
            vul_funcs.append(func['func'])
    print('benign', len(benign_funcs))
    print('vulnerable', len(vul_funcs))
    for idx, code in enumerate(benign_funcs):
        path = f'/home/public/rmt/niexu/dataset/vul/devign_data/source_code/benign/{idx}.c'
        write_file(code, path, is_need_create_dir=True)
        
    for idx, code in enumerate(vul_funcs):
        path = f'/home/public/rmt/niexu/dataset/vul/devign_data/source_code/vulnerable/{idx}.c'
        write_file(code, path, is_need_create_dir=True)
        
def generate_cpgs(source_code_path, is_gencsv=False):
    output, data_path = joern_parse(source_code_path, is_gencsv)
    csv_dir = f'{output}{data_path}'
    benign_dir = os.path.join(source_code_path, 'benign')
    vul_dir = os.path.join(source_code_path, 'vulnerable')
    positive_path = os.path.join(os.path.dirname(source_code_path),'data', 'positive.json')
    negative_path = os.path.join(os.path.dirname(source_code_path),'data', 'negative.json')
    positive_cpgs = []
    negative_cpgs = []
    cnt = 0
    for f in os.listdir(benign_dir):
        benign_csv_path = f'{csv_dir}/benign/{f}'
        path = os.path.join(benign_dir, f)
        cpgs = inputGeneration(os.path.join(benign_csv_path, 'nodes.csv'), os.path.join(benign_csv_path, 'edges.csv'))
        cpgs = clean_json(cpgs, path)
        negative_cpgs.extend(cpgs)
        cnt+=len(cpgs)
        print(f'getting {cnt} cpgs!!!', end='\r')
        
    for f in os.listdir(vul_dir):
        vul_csv_path = f'{csv_dir}/vulnerable/{f}'
        path = os.path.join(vul_dir, f)
        cpgs = inputGeneration(os.path.join(vul_csv_path, 'nodes.csv'), os.path.join(vul_csv_path, 'edges.csv'))
        cpgs = clean_json(cpgs, path)
        positive_cpgs.extend(cpgs)
        cnt+=len(cpgs)
        print(f'getting {cnt} cpgs!!!', end='\r')
    
    os.makedirs(os.path.dirname(positive_path), exist_ok=True)
    os.makedirs(os.path.dirname(negative_path), exist_ok=True)
    write_json(positive_cpgs, positive_path)
    write_json(negative_cpgs, negative_path)
    
