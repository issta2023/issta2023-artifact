from itertools import combinations
from operator import xor
import os
import sys
import json
import numpy as np
# temporary solution for relative imports in case pyod is not installed
# if pyod is installed, no need to use the following line
# sys.path.append(
#     os.path.abspath(os.path.join(os.path.dirname("__file__"), '..')))

from pyod.models.knn import KNN
from pyod.models.abod import ABOD
from pyod.utils.data import generate_data
from pyod.utils.data import evaluate_print
from pyod.utils.example import visualize
from pyod.models.auto_encoder import AutoEncoder
from pyod.models.cblof import CBLOF
from pyod.models.hbos import HBOS
from pyod.models.iforest import IForest
from pyod.models.lof import LOF
from pyod.models.mcd import MCD
from pyod.models.so_gaal import SO_GAAL
from pyod.models.ocsvm import OCSVM
from pyod.models.sos import SOS
from pyod.models.pca import PCA
from sklearn.covariance import EllipticEnvelope


def read_json(path):
    json_dict = []
    with open(path, 'r', encoding='utf8') as f:
        
        json_dict = json.load(f)
        f.close()
    return json_dict


def flip_data(method, src_data, noise_ids):
    if method == 'deepwukong':
        key = 'target'
    else:
        key = 'val'
    for xfg in src_data:
        xfg_id = xfg['xfg_id']
        if xfg_id in noise_ids:
            xfg[key] = xfg[key] ^ 1
            xfg['flip'] = not xfg['flip']
    return src_data
def knn_outlier(X_train, Y_train, contamination, flipped):
    """
    @description  :KNN离群分析(0 inlier 1 outlier)
    ---------
    @param  :
    -------
    @Returns  :
    -------
    """
    
    
    clf_name = 'KNN'
    clf = KNN(n_neighbors = 500 ,contamination=contamination)
    clf.fit(X_train)
    # get the prediction labels and outlier scores of the training data
    y_train_pred = clf.labels_  # binary labels (0: inliers, 1: outliers)
    y_train_scores = clf.decision_scores_  # raw outlier scores
   
    # evaluate and print the results
    flipped = np.array(flipped)
    outlier_flip = flipped[y_train_pred == 1]


    print(np.sum(outlier_flip), len(outlier_flip))
    return y_train_pred.tolist()
    
    

def abod_outlier(X_train, Y_train, contamination, flipped):
    """
    @description  :ABOD 离群分析(0 inlier 1 outlier)
    ---------
    @param  :
    -------
    @Returns  :
    -------
    """
    # train ABOD detector
    clf_name = 'ABOD'
    clf = ABOD( contamination=contamination, method='fast')
    clf.fit(X_train)

    # get the prediction labels and outlier scores of the training data
    y_train_pred = clf.labels_  # binary labels (0: inliers, 1: outliers)
    y_train_scores = clf.decision_scores_  # raw outlier scores
    flipped = np.array(flipped)
    outlier_flip = flipped[y_train_pred == 1]


    print(np.sum(outlier_flip), len(outlier_flip))
    return y_train_pred.tolist()
    

def autoEncoder_outlier(X_train, Y_train, contamination, flipped):
    """
    @description  :autoEncoder 离群分析(0 inlier 1 outlier)
    ---------
    @param  :
    -------
    @Returns  :
    -------
    """
    clf_name = 'AutoEncoder'
    size = len(X_train[0])
    clf = AutoEncoder(hidden_neurons=[64,32,16,16,32,64], dropout_rate=0.5 ,verbose = 0, contamination=contamination)
    clf.fit(X_train)

    # get the prediction labels and outlier scores of the training data
    y_train_pred = clf.labels_  # binary labels (0: inliers, 1: outliers)
    y_train_scores = clf.decision_scores_  # raw outlier scores
    flipped = np.array(flipped)
    outlier_flip = flipped[y_train_pred == 1]


    print(np.sum(outlier_flip), len(outlier_flip))
    return y_train_pred.tolist()

def cblof_outlier(X_train, Y_train, contamination, flipped):
    """
    @description  :CBLOF 离群分析(0 inlier 1 outlier)
    ---------
    @param  :
    -------
    @Returns  :
    -------
    """
    # train CBLOF detector
    clf_name = 'CBLOF'
    clf = CBLOF(n_clusters = 8, contamination=contamination)
    clf.fit(X_train)

    # get the prediction labels and outlier scores of the training data
    y_train_pred = clf.labels_  # binary labels (0: inliers, 1: outliers)
    y_train_scores = clf.decision_scores_  # raw outlier scores
    flipped = np.array(flipped)
    outlier_flip = flipped[y_train_pred == 1]


    print(np.sum(outlier_flip), len(outlier_flip))
    return y_train_pred.tolist()

def hbos_outlier(X_train, Y_train, contamination, flipped):
    """
    @description  :HBOS 离群分析(0 inlier 1 outlier)
    ---------
    @param  :
    -------
    @Returns  :
    -------
    """
     # train HBOS detector
    clf_name = 'HBOS'
    clf = HBOS(contamination=contamination)
    clf.fit(X_train)

    # get the prediction labels and outlier scores of the training data
    y_train_pred = clf.labels_  # binary labels (0: inliers, 1: outliers)
    y_train_scores = clf.decision_scores_  # raw outlier scores
    flipped = np.array(flipped)
    outlier_flip = flipped[y_train_pred == 1]


    print(np.sum(outlier_flip), len(outlier_flip))
    return y_train_pred.tolist()

def I_forest_outlier(X_train, Y_train, contamination, flipped):
    """
    @description  :I-forest 离群分析(0 inlier 1 outlier)
    ---------
    @param  :
    -------
    @Returns  :
    -------
    """
    clf_name = 'IForest'
    clf = IForest(contamination=contamination)
    clf.fit(X_train)

    # get the prediction labels and outlier scores of the training data
    y_train_pred = clf.labels_  # binary labels (0: inliers, 1: outliers)
    y_train_scores = clf.decision_scores_  # raw outlier scores
    flipped = np.array(flipped)
    outlier_flip = flipped[y_train_pred == 1]


    print(np.sum(outlier_flip), len(outlier_flip))
    return y_train_pred.tolist()

def lof_outlier(X_train, Y_train, contamination, flipped):
    """
    @description  :LOF 离群分析(0 inlier 1 outlier)
    ---------
    @param  :
    -------
    @Returns  :
    -------
    """
     # train LOF detector
    clf_name = 'LOF'
    # clf = LOF(n_neighbors = len(X_train), p=4, contamination=contamination)

    clf = LOF(n_neighbors = len(X_train) // 2, p=4, contamination=contamination)
    clf.fit(X_train)

    # get the prediction labels and outlier scores of the training data
    y_train_pred = clf.labels_  # binary labels (0: inliers, 1: outliers)
    y_train_scores = clf.decision_scores_  # raw outlier scores
    flipped = np.array(flipped)
    outlier_flip = flipped[y_train_pred == 1]

    
    print(np.sum(outlier_flip), len(outlier_flip))
    return y_train_pred.tolist()

def mcd_outlier(X_train, Y_train, contamination, flipped):
    """
    @description  :MCD 离群分析(0 inlier 1 outlier)
    ---------
    @param  :
    -------
    @Returns  :
    -------
    """
    # train LOF detector
    clf_name = 'MCD'
    clf = MCD(contamination=contamination)
    clf.fit(X_train)

    # get the prediction labels and outlier scores of the training data
    y_train_pred = clf.labels_  # binary labels (0: inliers, 1: outliers)
    y_train_scores = clf.decision_scores_  # raw outlier scores
    flipped = np.array(flipped)
    outlier_flip = flipped[y_train_pred == 1]


    print(np.sum(outlier_flip), len(outlier_flip))
    return y_train_pred.tolist()

def so_gaal_outlier(X_train, Y_train, contamination, flipped):
    """
    @description  :So-gaal 离群分析(0 inlier 1 outlier)
    ---------
    @param  :
    -------
    @Returns  :
    -------
    """
    # train SO_GAAL detector
    clf_name = 'SO_GAAL'
    # clf = SO_GAAL(stop_epochs=20 ,contamination=contamination)

    clf = SO_GAAL(stop_epochs=20 ,contamination=contamination)
    clf.fit(X_train)

    # get the prediction labels and outlier scores of the training data
    y_train_pred = clf.labels_  # binary labels (0: inliers, 1: outliers)
    y_train_scores = clf.decision_scores_  # raw outlier scores
    flipped = np.array(flipped)
    outlier_flip = flipped[y_train_pred == 1]


    print(np.sum(outlier_flip), len(outlier_flip))
    return y_train_pred.tolist()

def ocsvm_outlier(X_train, Y_train, contamination, flipped):
    """
    @description  :OCSVM 离群分析(0 inlier 1 outlier)
    ---------
    @param  :
    -------
    @Returns  :
    -------
    """
    # train one_class_svm detector
    clf_name = 'OneClassSVM'
    clf = OCSVM(contamination=contamination)
    clf.fit(X_train)

    # get the prediction labels and outlier scores of the training data
    y_train_pred = clf.labels_  # binary labels (0: inliers, 1: outliers)
    y_train_scores = clf.decision_scores_  # raw outlier scores
    flipped = np.array(flipped)
    outlier_flip = flipped[y_train_pred == 1]


    print(np.sum(outlier_flip), len(outlier_flip))
    return y_train_pred.tolist()

def sos_outlier(X_train, Y_train, contamination, flipped):
    """
    @description  :SOS 离群分析(0 inlier 1 outlier)
    ---------
    @param  :
    -------
    @Returns  :
    -------
    """
    # train SOS detector
    clf_name = 'SOS'
    clf = SOS(perplexity = 100,contamination=contamination, metric = 'mahalanobis')
    clf.fit(X_train)

    # get the prediction labels and outlier scores of the training data
    y_train_pred = clf.labels_  # binary labels (0: inliers, 1: outliers)
    y_train_scores = clf.decision_scores_  # raw outlier scores
    flipped = np.array(flipped)
    outlier_flip = flipped[y_train_pred == 1]


    print(np.sum(outlier_flip), len(outlier_flip))
    return y_train_pred.tolist()

def pca_outlier(X_train, Y_train, contamination, flipped):
    """
    @description  :PCA 离群分析(0 inlier 1 outlier)
    ---------
    @param  :
    -------
    @Returns  :
    -------
    """
    # train PCA detector
    clf_name = 'PCA'
    clf = PCA(contamination=contamination)
    clf.fit(X_train)

    # get the prediction labels and outlier scores of the training data
    y_train_pred = clf.labels_  # binary labels (0: inliers, 1: outliers)
    y_train_scores = clf.decision_scores_  # raw outlier scores
    flipped = np.array(flipped)
    outlier_flip = flipped[y_train_pred == 1]


    print(np.sum(outlier_flip), len(outlier_flip))
    return y_train_pred.tolist()

def ellipticEnvelope_outlier(X_train, Y_train, contamination, flipped):
    """
    @description  :EllipticEnvelope 离群分析(1 inlier -1 outlier)
    ---------
    @param  :
    -------
    @Returns  :
    -------
    """
    clf_name = 'EllipticEnvelope'
    
    X = np.array(X_train)
    clf = EllipticEnvelope(contamination=contamination)
    y_train_pred = clf.fit_predict(X)
    # get the prediction labels and outlier scores of the training data
    # y_train_pred = clf.predict(X) # binary labels (0: inliers, 1: outliers)
    # y_train_scores = clf.score_samples(X)  # raw outlier scores
    # decisions = clf.decision_function(X)
    
    flipped = np.array(flipped)
    outlier_flip = flipped[y_train_pred == -1]

    
    print(np.sum(outlier_flip), len(outlier_flip))
    return y_train_pred.tolist()
    
    # print(y_train_scores)
    # print(decisions)

def get_train_data(ws, wds, dds):
    """
    @description  :获取离群训练所需要的数据
    ---------
    @param  :
    ws 全部数据集
    wds ws中ds的loss vector
    dds ds中ds的loos vector
    -------
    @Returns  :
    -------
    """
    
    
    
    
    

    X_train = []
    Y_train = []
    flipped = []
    xfg_ids = []

    for xfg in ws:
        xfg_id = xfg['xfg_id']
        if str(xfg_id) in dds.keys():
            x = dds[str(xfg_id)]
            x.extend(wds[str(xfg_id)])
            # x = wds[str(xfg_id)]
            
            X_train.append(x)
            if 'target' in xfg.keys():
                key = 'target'
            else:
                key = 'val'
            Y_train.append(xfg[key])
            flipped.append(xfg['flip'])
            xfg_ids.append(xfg['xfg_id'])

    
    
    return X_train, Y_train, flipped ,xfg_ids

def vote(X_train, Y_train, flipped, rate ,xfg_ids, contamination):
    knn_pre = knn_outlier(X_train=X_train, Y_train=Y_train, contamination=contamination, flipped = flipped)
    # abod_pre = abod_outlier(X_train=X_train, Y_train=Y_train, contamination=0.1, flipped = flipped)
    autoEncoder_pre = autoEncoder_outlier(X_train=X_train, Y_train=Y_train, contamination=contamination, flipped = flipped)
    cblof_pre = cblof_outlier(X_train=X_train, Y_train=Y_train, contamination=contamination, flipped = flipped)
    hbos_pre = hbos_outlier(X_train=X_train, Y_train=Y_train, contamination=contamination, flipped = flipped)
    I_forest_pre = I_forest_outlier(X_train=X_train, Y_train=Y_train, contamination=contamination, flipped = flipped)
    lof_pre = lof_outlier(X_train=X_train, Y_train=Y_train, contamination=contamination, flipped = flipped)
    mcd_pre = mcd_outlier(X_train=X_train, Y_train=Y_train, contamination=contamination, flipped = flipped)
    so_gaal_pre = so_gaal_outlier(X_train=X_train, Y_train=Y_train, contamination=contamination, flipped = flipped)
    ocsvm_pre = ocsvm_outlier(X_train=X_train, Y_train=Y_train, contamination=contamination, flipped = flipped)
    # sos_pre = sos_outlier(X_train=X_train, Y_train=Y_train, contamination=0.1, flipped = flipped)
    pca_pre = pca_outlier(X_train=X_train, Y_train=Y_train, contamination=contamination, flipped = flipped)
    ellipticEnvelope_pre = ellipticEnvelope_outlier(X_train=X_train, Y_train=Y_train, contamination=contamination, flipped = flipped)
    
    outlier_list = [] 
    for i in range(len(Y_train)):
        outlier = 0
        if knn_pre[i] == 1:
            outlier += 1
        # if abod_pre[i] == 1:
        #     outlier += 1 
        if autoEncoder_pre[i] == 1:
            outlier += 1 
        if cblof_pre[i] == 1:
            outlier += 1 
        if hbos_pre[i] == 1:
            outlier += 1 
        if I_forest_pre[i] == 1:
            outlier += 1 
        if lof_pre[i] == 1:
            outlier += 1 
        if mcd_pre[i] == 1:
            outlier += 1 
        if so_gaal_pre[i] == 1:
            outlier += 1 
        if ocsvm_pre[i] == 1:
            outlier += 1 
        # if sos_pre[i] == 1:
        #     outlier += 1 
        if pca_pre[i] == 1:
            outlier += 1 
        if ellipticEnvelope_pre[i] == -1:
            outlier += 1 
        if outlier >= (rate * 11):
            outlier_list.append([xfg_ids[i], Y_train[i], flipped[i]])
    return outlier_list

def get_data_json(data_path):
    with open(data_path,'r',encoding = 'utf8') as f:
        data_json = json.load(f)
        for key in data_json:           
            for idx,xfg in enumerate(data_json[key], start=0):
                xfg['xfg_id'] = idx
        f.close()
    return data_json

if __name__ == "__main__":
    ws_path = '/home/niexu/project/python/noise_reduce/data/sysevr/CWE119/CWE119.json'
    noise_info_path = '/home/niexu/project/python/noise_reduce/data/sysevr/CWE119/noise_info.json'

    ws = read_json(ws_path)
    noise_info = read_json(noise_info_path)
    noise_key = '10_percent'
    noise_xfg_ids = noise_info[noise_key]['noise_xfg_ids']
    flip_data('sysevr', ws, noise_xfg_ids)
    with open('/home/niexu/project/python/noise_reduce/wds_loss.json', 'r', encoding = 'utf8') as f:
        wds_loss = json.load(f)
        f.close()
    with open('/home/niexu/project/python/noise_reduce/dds_loss.json', 'r', encoding = 'utf8') as f:
        dds_loss = json.load(f)
        f.close()
    
    X_train, Y_train, flipped, xfg_ids = get_train_data(ws, wds_loss, dds_loss)
    
    # print(X_train)
    # y_pre = knn_outlier(X_train=X_train, Y_train=Y_train, contamination=0.1, flipped = flipped) #280
    # y_pre = abod_outlier(X_train=X_train, Y_train=Y_train, contamination=0.25, flipped = flipped) # 等会跑一下 360
    # y_pre = autoEncoder_outlier(X_train=X_train, Y_train=Y_train, contamination=0.1, flipped = flipped) #279
    # y_pre = cblof_outlier(X_train=X_train, Y_train=Y_train, contamination=0.1, flipped = flipped) #283
    # y_pre = hbos_outlier(X_train=X_train, Y_train=Y_train, contamination=0.1, flipped = flipped) #263
    # y_pre = I_forest_outlier(X_train=X_train, Y_train=Y_train, contamination=0.1, flipped = flipped) #283 
    # y_pre = lof_outlier(X_train=X_train, Y_train=Y_train, contamination=0.1, flipped = flipped) #已调整 275
    # y_pre = mcd_outlier(X_train=X_train, Y_train=Y_train, contamination=0.1, flipped = flipped) #275
    # y_pre = so_gaal_outlier(X_train=X_train, Y_train=Y_train, contamination=0.1, flipped = flipped) #272
    # y_pre = ocsvm_outlier(X_train=X_train, Y_train=Y_train, contamination=0.1, flipped = flipped) #281
    # y_pre = sos_outlier(X_train=X_train, Y_train=Y_train, contamination=0.1, flipped = flipped) #效果差320
    # y_pre = pca_outlier(X_train=X_train, Y_train=Y_train, contamination=0.1, flipped = flipped) #279
    y_pre = ellipticEnvelope_outlier(X_train=X_train, Y_train=Y_train, contamination=0.1, flipped = flipped)#275
    