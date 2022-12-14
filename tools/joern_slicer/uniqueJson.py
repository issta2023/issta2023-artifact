'''unique json

@author : jumormt
@version : 1.0
'''
__author__ = "jumormt"

import json
import hashlib
import os
from tempfile import SpooledTemporaryFile

import jsonlines
from difflib import SequenceMatcher

from numpy.lib.function_base import flip#导入库
from utils.json_ops import read_json, write_json

def unique_xfgs(xfg_list):
    """
    @description  : merge xfg in jsonline format to json format, then symbolize , tokenize de-duplication
    ---------
    @param  :xfg_path: the dir of xfg in jsonline format
    -------
    @Returns  :
    -------
    """

    md5Dict = dict()
    
   
    #here cfg is xfg
    for xfg in xfg_list:# for one cfg
        nodes_line_sym = xfg['nodes-line-sym']
        target = xfg['target']
        nodes_line_md5 = list()
        for nls in nodes_line_sym:
            nodes_line_md5.append(getMD5(nls))# md5 each line
        edges_No = xfg['edges-No']
        edges_No_md5 = list()
        for edges in edges_No:
            edges_No_md5.append([nodes_line_md5[edges[0]], nodes_line_md5[edges[1]]])
        edges_No_md5 = sorted(edges_No_md5)
        cfgMD5 = getMD5(str(edges_No_md5))# md5 all edges - cfg

        if cfgMD5 not in md5Dict.keys():
            md5Dict[cfgMD5] = dict()
            md5Dict[cfgMD5]["target"] = target
            md5Dict[cfgMD5]["xfg"] = xfg
        else:# conflict - mark as -1
            md5Target = md5Dict[cfgMD5]["target"]
            if (md5Target != -1 and md5Target != target):
                md5Dict[cfgMD5]["target"] = -1
  
            

    return md5Dict


def writeBigJson(md5Dict):
    '''

    :param OUTDIR:
    :param md5Dict:
    :return:
    '''
    
    xfgs = list()

    for mdd5 in md5Dict:
        if (md5Dict[mdd5]["target"] != -1):# dont write conflict sample
            xfgs.append(md5Dict[mdd5]["xfg"])



    return xfgs

def similarity(a, b):
    return SequenceMatcher(None, a, b).ratio()#引用ratio方法，返回序列相似性的度量


def getMD5(s):
    '''
    得到字符串s的md5加密后的值

    :param s:
    :return:
    '''
    hl = hashlib.md5()
    hl.update(s.encode("utf-8"))
    return hl.hexdigest()
def uniqueDir_d2a(xfg_list):
    """
    @description  : merge xfg in jsonline format to json format, then symbolize , tokenize de-duplication
    ---------
    @param  :xfg_path: the dir of xfg in jsonline format
    -------
    @Returns  :
    -------
    """
    
    md5Dict = dict()
    
   
    #here cfg is xfg
 
    for cfg in xfg_list:# for one cfg
        nodes_line_sym = cfg['nodes-line-sym']
        target = cfg['target']
        nodes_line_md5 = list()
        for nls in nodes_line_sym:
            nodes_line_md5.append(getMD5(nls))# md5 each line
        edges_No = cfg['edges-No']
        edges_No_md5 = list()
        for edges in edges_No:
            edges_No_md5.append([nodes_line_md5[edges[0]], nodes_line_md5[edges[1]]])
        edges_No_md5 = sorted(edges_No_md5)
        cfgMD5 = getMD5(str(edges_No_md5))# md5 all edges - cfg

        if cfgMD5 not in md5Dict.keys():
            md5Dict[cfgMD5] = dict()
            vul_info_list = list()
            safe_info_list = list()
            info = dict()
            info['target'] = target
            info['cfg'] = cfg
            if target == 1:
              vul_info_list.append(info)
            else:
              safe_info_list.append(info)
            md5Dict[cfgMD5]['vul_info_list'] = vul_info_list
            md5Dict[cfgMD5]['safe_info_list'] = safe_info_list
            md5Dict[cfgMD5]['all_count'] = 1
            md5Dict[cfgMD5]['vul_count'] = len(vul_info_list)
            md5Dict[cfgMD5]['safe_count'] = len(safe_info_list)
            
            # md5Dict[cfgMD5]["target"] = target
            # md5Dict[cfgMD5]["cfg"] = cfg
        else:# conflict - mark as -1
            # md5Target = md5Dict[cfgMD5]["target"]
            # if (md5Target != target):
            #     # md5Dict[cfgMD5]["target"] = -1
            #     dulplicate_xfgs.append(cfg)
            info = dict()
            info['target'] = target
            info['cfg'] = cfg
            if target == 1:
              md5Dict[cfgMD5]['vul_info_list'].append(info)
              md5Dict[cfgMD5]['vul_count'] += 1
              md5Dict[cfgMD5]['all_count'] += 1


            else:
              md5Dict[cfgMD5]['safe_info_list'].append(info)
              md5Dict[cfgMD5]['safe_count'] += 1
              md5Dict[cfgMD5]['all_count'] += 1

    return md5Dict  

def uniqueDir_with_flip(xfg_list):
    """
    @description  : merge xfg in jsonline format to json format, then symbolize , tokenize de-duplication
    ---------
    @param  :xfg_path: the dir of xfg in jsonline format
    -------
    @Returns  :
    -------
    """
    
    md5Dict = dict()
    
   
    #here cfg is xfg
 
    for cfg in xfg_list:# for one cfg
        nodes_line_sym = cfg['nodes-line-sym']
        target = cfg['target']
        nodes_line_md5 = list()
        for nls in nodes_line_sym:
            nodes_line_md5.append(getMD5(nls))# md5 each line
        edges_No = cfg['edges-No']
        edges_No_md5 = list()
        for edges in edges_No:
            edges_No_md5.append([nodes_line_md5[edges[0]], nodes_line_md5[edges[1]]])
        edges_No_md5 = sorted(edges_No_md5)
        cfgMD5 = getMD5(str(edges_No_md5))# md5 all edges - cfg

        if cfgMD5 not in md5Dict.keys():
            md5Dict[cfgMD5] = dict()
            vul_info_list = list()
            safe_info_list = list()
            info = dict()
            info['target'] = target
            info['cfg'] = cfg
            # info['flip'] = cfg['flip']
            if target == 1:
              vul_info_list.append(info)
            else:
              safe_info_list.append(info)
            md5Dict[cfgMD5]['vul_info_list'] = vul_info_list
            md5Dict[cfgMD5]['safe_info_list'] = safe_info_list
            md5Dict[cfgMD5]['all_count'] = 1
            md5Dict[cfgMD5]['vul_count'] = len(vul_info_list)
            md5Dict[cfgMD5]['safe_count'] = len(safe_info_list)
            
            # md5Dict[cfgMD5]["target"] = target
            # md5Dict[cfgMD5]["cfg"] = cfg
        else:# conflict - mark as -1
            # md5Target = md5Dict[cfgMD5]["target"]
            # if (md5Target != target):
            #     # md5Dict[cfgMD5]["target"] = -1
            #     dulplicate_xfgs.append(cfg)
            info = dict()
            info['target'] = target
            info['cfg'] = cfg
            # info['flip'] = cfg['flip']
            if target == 1:
              md5Dict[cfgMD5]['vul_info_list'].append(info)
              md5Dict[cfgMD5]['vul_count'] += 1
              md5Dict[cfgMD5]['all_count'] += 1


            else:
              md5Dict[cfgMD5]['safe_info_list'].append(info)
              md5Dict[cfgMD5]['safe_count'] += 1
              md5Dict[cfgMD5]['all_count'] += 1

    return md5Dict

def get_xfg_str(cfg):
  nodes_line_sym = cfg['nodes-line-sym']
  # edges_No = cfg['edges-No']
  # edges_No_md5 = list()
  # for edges in edges_No:
  #     edges_No_md5.append([nodes_line_sym[edges[0]], nodes_line_sym[edges[1]]])
  # edges_No_md5 = sorted(edges_No_md5)
  return str(nodes_line_sym)


def similarity_json(xfg_list):
  #here cfg is xfg
  md5Dict = dict()
  for xfg in xfg_list:# for one cfg
      xfg_str = get_xfg_str(xfg)
      xfgMD5 = getMD5(xfg_str)# md5 all edges - cfg
      if xfgMD5 not in md5Dict.keys():
          md5Dict[xfgMD5] = dict()
          md5Dict[xfgMD5]["target"] = xfg['target']
          md5Dict[xfgMD5]["xfg"] = xfg
  
  md5_set = set()
  for xfg_1 in xfg_list:
    for xfg_2 in xfg_list:
      str_1 = get_xfg_str(xfg_1)
      str_2 = get_xfg_str(xfg_2)
      md5_1 = getMD5(str_1)
      md5_2 = getMD5(str_2)
      sim = similarity(str_1, str_2)
      # print(sim)
      if sim >= 0.6 and md5Dict[md5_1]['target'] == md5Dict[md5_2]['target']:
        if md5_1 not in md5_set and md5_2 not in md5_set:
          md5_set.add(md5_1)
          break
        else:
          break
      else:
        md5_set.add(md5_1)
        break

  xfgs = []
  for md5 in md5_set:
    xfgs.append(md5Dict[md5]['xfg'])
  return xfgs


def writeBigJson_d2a(md5Dict):
  '''

    :param OUTDIR:
    :param md5Dict:
    :return:
    '''
    
  xfgs = list()

  for mdd5 in md5Dict:
      if (md5Dict[mdd5]["target"] != -1):# dont write conflict sample
        xfgs.append(md5Dict[mdd5]["xfg"])
      else:
        md5Dict[mdd5]["xfg"]['target'] = 1
        xfgs.append(md5Dict[mdd5]["xfg"])
  return xfgs
    # '''

    # :param OUTDIR:
    # :param md5Dict:
    # :return:
    # '''
    
    # newJsonFileContent = list()
    # dulpulicate = list()
    # print('md5dict',len(md5Dict))
    # for mdd5 in md5Dict:
    #     # if (md5Dict[mdd5]["target"] != -1):# dont write conflict sample
    #     #     newJsonFileContent.append(md5Dict[mdd5]["cfg"])
    #   all_count = md5Dict[mdd5]['all_count']
    #   vul_count = md5Dict[mdd5]['vul_count']
    #   safe_count = md5Dict[mdd5]['safe_count']
    #   vul_info_list = md5Dict[mdd5]['vul_info_list']
    #   safe_info_list = md5Dict[mdd5]['safe_info_list']

    #   if all_count == 1:
    #     if vul_count == 1:
    #       newJsonFileContent.append(vul_info_list[0]['cfg'])
    #     elif safe_count == 1:
    #       newJsonFileContent.append(safe_info_list[0]['cfg'])
    #   else:
        
    #     # 都没有翻转过,  取没有冲突的只有重复的中的一个
    #     if len(safe_info_list) == 0 and len(vul_info_list) > 0:
    #       cfg = vul_info_list[0]['cfg']
    #     elif len(vul_info_list) == 0 and len(safe_info_list) > 0:
    #       cfg = safe_info_list[0]['cfg']
    #     else:
    #       cfg = vul_info_list[0]['cfg']
    #       # dulpulicate.append(cfg)
    #       # continue
        
    #     newJsonFileContent.append(cfg)
    # # write_json(dulpulicate, 'bfo_duplicate.json')
    # print('newJsonFileContent',len(newJsonFileContent))
    # return newJsonFileContent

def writeBigJson_with_flip(md5Dict):
    '''

    :param OUTDIR:
    :param md5Dict:
    :return:
    '''
    
    newJsonFileContent = list()
   
    print('md5dict',len(md5Dict))
    for mdd5 in md5Dict:
        # if (md5Dict[mdd5]["target"] != -1):# dont write conflict sample
        #     newJsonFileContent.append(md5Dict[mdd5]["cfg"])
      all_count = md5Dict[mdd5]['all_count']
      vul_count = md5Dict[mdd5]['vul_count']
      safe_count = md5Dict[mdd5]['safe_count']
      vul_info_list = md5Dict[mdd5]['vul_info_list']
      safe_info_list = md5Dict[mdd5]['safe_info_list']

      if all_count == 1:
        if vul_count == 1:
          newJsonFileContent.append(vul_info_list[0]['cfg'])
        elif safe_count == 1:
          newJsonFileContent.append(safe_info_list[0]['cfg'])
      else:


        vul_flip = 0
        safe_flip = 0
        for safe_info in safe_info_list:
          if safe_info['flip']:
            safe_flip += 1
        for vul_info in vul_info_list:
          if vul_info['flip']:
            vul_flip += 1

        
        if vul_flip > 0 or safe_flip > 0:
          # 只有重复列表中全部都是flip过的才是没有冲突的，凡是重复列表中flip 既有true 又有false的都是 conflict
          if (vul_flip == 0 and safe_flip == len(safe_info_list)): 
            cfg = safe_info_list[0]['cfg']
            cfg['flip'] = True
          elif (safe_flip == 0 and vul_flip == len(vul_info_list)):
            cfg = vul_info_list[0]['cfg']
            cfg['flip'] = True
          else:
            continue
        else:
          # 都没有翻转过,  取没有冲突的只有重复的中的一个
          if len(safe_info_list) == 0 and len(vul_info_list) > 0:
            cfg = vul_info_list[0]['cfg']
          elif len(vul_info_list) == 0 and len(safe_info_list) > 0:
            cfg = safe_info_list[0]['cfg']
          else:
            
            continue
        newJsonFileContent.append(cfg)
    
    print('newJsonFileContent',len(newJsonFileContent))
    
    return newJsonFileContent



def main(args):
    CWEID = args.CWEID
    DIR = "/home/cry/chengxiao/dataset/svf-related/CWE{}/xfg-sym/".format(CWEID)
    md5Dict = uniqueDir(DIR)

    OUTDIR = "/home/cry/chengxiao/dataset/svf-related/CWE{}/xfg-sym-unique/".format(CWEID)
    if(not os.path.exists(OUTDIR)):
        os.mkdir(OUTDIR)

    xfgNum = writeBigJson(OUTDIR, md5Dict)

    print("end unique - total {} xfgs!".format(xfgNum))


if __name__ == '__main__':
    xfg_list = read_json('test.json')
    str_1 = get_xfg_str(xfg_list[0])
    str_2 = get_xfg_str(xfg_list[1])
    print(str_1)
    print(str_2)
    print(similarity(str_1, str_2))
  
   
