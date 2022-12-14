import math
from posixpath import join
import numpy
from torch_geometric.nn import GCNConv, TopKPooling, GATConv, GraphSAGE, GatedGraphConv, GraphConv
from torch_geometric.nn import global_mean_pool as gap, global_max_pool as gmp
# from k_gnn import GraphConv as K_GNN
from typing import Tuple, Dict, List, Union
import json

import torch
from pytorch_lightning.core.lightning import LightningModule
from torch.optim import Optimizer
from torch.optim.lr_scheduler import _LRScheduler

from omegaconf import DictConfig
from utils.training import configure_optimizers_alon
from models.deepwukong.FocalLoss import focal_loss
import torch.nn as nn
import torch.nn.functional as F
from utils.matrics import Statistic



class GCNPoolBlockLayer(torch.nn.Module):
    """graph conv-pool block

    graph convolutional + graph pooling + graph readout

    :attr GCL: graph conv layer
    :attr GPL: graph pooling layer
    """
    def __init__(self, config: DictConfig):
        super(GCNPoolBlockLayer, self).__init__()
        self._config = config
        input_size = self._config.hyper_parameters.vector_length
        self.layer_num = self._config.gnn.layer_num
        self.input_GCL = GCNConv(input_size, config.gnn.hidden_size)

        self.input_GPL = TopKPooling(config.gnn.hidden_size,
                                     ratio=config.gnn.pooling_ratio)

        for i in range(self.layer_num - 1):
            setattr(self, f"hidden_GCL{i}",
                    GCNConv(config.gnn.hidden_size, config.gnn.hidden_size))
            setattr(
                self, f"hidden_GPL{i}",
                TopKPooling(config.gnn.hidden_size,
                            ratio=config.gnn.pooling_ratio))

        ## GGNN
        # self.input_GCL = GatedGraphConv(input_size,  num_layers=1)

        # self.input_GPL = TopKPooling(config.gnn.hidden_size,
        #                              ratio=config.gnn.pooling_ratio)

        # for i in range(self.layer_num - 1):
        #     setattr(self, f"hidden_GCL{i}",
        #             GatedGraphConv(config.gnn.hidden_size, num_layers=1))
        #     setattr(
        #         self, f"hidden_GPL{i}",
        #         TopKPooling(config.gnn.hidden_size,
        #                     ratio=config.gnn.pooling_ratio))

    def forward(self, data):
        x, edge_index, batch = data.x, data.edge_index, data.batch
        x = F.relu(self.input_GCL(x, edge_index))
        x, edge_index, _, batch, _, _ = self.input_GPL(x, edge_index, None,
                                                       batch)
        # (batch size, hidden)
        out = torch.cat([gmp(x, batch), gap(x, batch)], dim=1)
        for i in range(self.layer_num - 1):
            x = F.relu(getattr(self, f"hidden_GCL{i}")(x, edge_index))
            x, edge_index, _, batch, _, _ = getattr(self, f"hidden_GPL{i}")(
                x, edge_index, None, batch)
            out += torch.cat([gmp(x, batch), gap(x, batch)], dim=1)

        return out


class VGD_GNN(LightningModule):
    _activations = {
        "relu": nn.ReLU(),
        "sigmoid": nn.Sigmoid(),
        "tanh": nn.Tanh(),
        "lkrelu": nn.LeakyReLU(0.3)
    }

    def __init__(
        self,
        config: DictConfig,
    ):
        super().__init__()
        self._config = config
        self.save_hyperparameters()
        self.init_layers()
        
        self.label_pcs = list()
        self.label_vr = list()
        self.label_pe = list()
        self.label_mi = list()


    def init_layers(self):
        self.gnn_layer = GCNPoolBlockLayer(self._config)
        self.lin1 = nn.Linear(self._config.gnn.hidden_size * 2,
                              self._config.gnn.hidden_size)
        self.dropout1 = nn.Dropout(self._config.classifier.drop_out)
        self.lin2 = nn.Linear(self._config.gnn.hidden_size,
                              self._config.gnn.hidden_size // 2)
        self.dropout2 = nn.Dropout(self._config.classifier.drop_out)
        self.lin3 = nn.Linear(self._config.gnn.hidden_size // 2, 2)

    def _get_activation(self, activation_name: str) -> torch.nn.Module:
        if activation_name in self._activations:
            return self._activations[activation_name]
        raise KeyError(f"Activation {activation_name} is not supported")

    def forward(self, batch):
        # (batch size, hidden)
        x = self.gnn_layer(batch)
        act = self._get_activation(self._config.classifier.activation)
        x = self.dropout1(act(self.lin1(x)))
        x = self.dropout2(act(self.lin2(x)))
        # (batch size, output size)
        # x = F.log_softmax(self.lin3(x), dim=-1)
        x = self.lin3(x)
        out_prob = F.log_softmax(x, dim=-1)

        return out_prob

    def training_step(self, batch, batch_idx: int) -> Dict:
        # (batch size, output size)
        logits = self(batch)
        loss = F.nll_loss(logits, batch.y)
        # loss_fn = focal_loss(alpha=0.25, gamma=2, num_classes=2)
        # loss = loss_fn(x, batch.y)
        log: Dict[str, Union[float, torch.Tensor]] = {"train/loss": loss}
        
        # for pred in preds:
        #     print(pred[1])

        with torch.no_grad():
            _, preds = logits.max(dim=1)
            # with open('srad_simple_analysis/train_false_xfg_ids.txt', 'a+') as f:
            #     for xfg_id in batch.xfg_id[batch.y != preds]:
            #         f.write(str(xfg_id.tolist()) + ',')
            #     f.close()
            statistic = Statistic().calculate_statistic(
                batch.y,
                preds,
                2, 
            )
            batch_matric = statistic.calculate_metrics(group="train")
            log.update(batch_matric)
            self.log_dict(log)
            self.log("f1",
                     batch_matric["train/f1"],
                     prog_bar=True,
                     logger=False)
        
        # preds_rate = F.sigmoid(logits)
        # preds_list = preds_rate.cpu().detach().numpy().tolist()
        # labels_list = preds.cpu().detach().numpy().tolist()
        # rb_path = join(self._config.res_folder, self._config.name, 'rb_result', self._config.dataset.name + '.json')
        # vr = 0
        # pe = 0
        # mi = 0

        # for i, pred in enumerate(preds_list):
        #     if pred[0] > pred[1]:
        #         vr = 1 - pred[1] / (pred[0] + pred[1])
        #         self.label_vr.append((labels_list[i], vr))
        #     else: 
        #         vr = 1 - pred[0] / (pred[0] + pred[1])
        #         self.label_vr.append((labels_list[i], vr))

        # with open(rb_path, 'a', encoding='utf8') as f:
        #     json.dump(self.label_vr,f,indent=2)
        #     f.close()

        return {"loss": loss, "statistic": statistic}

    def validation_step(self, batch, batch_idx: int) -> Dict:
        # (batch size, output size)
        # logits = self(batch)
        logits = self(batch)
        # loss_fn = focal_loss(alpha=0.25, gamma=2, num_classes=2)
        loss = F.nll_loss(logits, batch.y)
        # loss = loss_fn(x, batch.y)
        with torch.no_grad():
            _, preds = logits.max(dim=1)
            # with open('srad_simple_analysis/val_false_xfg_ids.txt', 'a+') as f:
            #     for xfg_id in batch.xfg_id[batch.y != preds]:
            #         f.write(str(xfg_id.tolist()) + ',')
            #     f.close()
            statistic = Statistic().calculate_statistic(
                batch.y,
                preds,
                2,
            )
            
        return {"loss": loss, "statistic": statistic}

    

    def test_step(self, batch, batch_idx: int) -> Dict:
                # (batch size, output size)
        # sample_num = 30
        # class_num = 2
        # # device = torch.device("cuda:{}".format(self._config.gpu) if torch.cuda.is_available() else "cpu")
        # # logits = numpy.empty(shape=[self._config.hyper_parameters.test_batch_size//2, class_num], dtype=numpy.float32)
        # for i in range(len(batch)):
        #     if batch[i] == None:
        #         break
        #     sample = batch[i]
        #     preds = numpy.zeros((sample_num, class_num), dtype=numpy.float32)
        #     n_cnt = 0
        #     p_cnt = 0
        #     sum_n = 0
        #     sum_p = 0
        #     mi = 0
        #     for j in range(sample_num):
        #         predictions = self(sample)
        #         preds_list = F.sigmoid(predictions).cpu().detach().numpy().tolist()
        #         pred_n = preds_list[0][0]
        #         pred_p = preds_list[0][1]
        #         sum_n += pred_n
        #         sum_p += pred_p
        #         _, label = predictions.max(dim=1)
        #         label = (label.cpu().detach().numpy().tolist())[0]
        #         # print(pred_n)
        #         # print(pred_p)
        #         print(label)
        #         if label == 0:
        #             n_cnt += 1
        #         else: p_cnt += 1
        #         if pred_n and pred_p:
        #             mi += pred_n * math.log10(pred_n) + pred_p * math.log10(pred_p)
        #         elif pred_n:
        #             mi += pred_n * math.log10(pred_n)
        #         elif pred_p:
        #             mi += pred_p * math.log10(pred_p)
        #         preds[j, :] = predictions.cpu().detach().numpy()
        #     print(sum_n)
        #     print(sum_p)
        #     preds = preds.mean(axis=0)
        #     preds = torch.tensor([preds])
        #     _, label = preds.max(dim=1)
        #     label = (label.cpu().detach().numpy().tolist())[0]
        #     preds_list = F.sigmoid(preds).cpu().detach().numpy().tolist()
        #     preds_n = preds_list[0][0]
        #     preds_p = preds_list[0][1]
        #     pcs = abs((preds_n - preds_p) / (preds_n + preds_p))
        #     label_pcs = (label, pcs)
        #     self.label_pcs.append(label_pcs)
        #     if n_cnt >= p_cnt:
        #         label_vr = (label, 1-(float)(n_cnt/sample_num))
        #     else: label_vr = (label, 1-(float)(p_cnt/sample_num))
        #     self.label_vr.append(label_vr)
        #     if sum_n and sum_p:
        #         pe = -(sum_n / sample_num * math.log(sum_n / sample_num, 10) 
        #             + sum_p / sample_num * math.log(sum_p / sample_num, 10))
        #     elif sum_n:
        #         pe = -(sum_n / sample_num * math.log(sum_n / sample_num, 10))
        #     elif sum_p:
        #         pe = (sum_p / sample_num * math.log(sum_p / sample_num, 10))
        #     label_pe = (label, pe)
        #     self.label_pe.append(label_pe)
        #     mi = pe + mi/sample_num
        #     label_mi = (label, mi)
        #     self.label_mi.append(label_mi)
        
        #     logits = numpy.append(logits, [preds], axis=0)
        # logits = torch.Tensor(logits)
        logits = self(batch)
        # y_probas = numpy.stack([self(batch)#???X_test_scaled???????????????
        #              for sample in range(100)])#??????????????????????????????100?????????
        # y_proba = y_probas.mean(axis=0)#?????????
        # loss_fn = focal_loss(alpha=0.25, gamma=2, num_classes=2)
        loss = F.nll_loss(logits, batch.y)
        # loss = loss_fn(x, batch.y)
        with torch.no_grad():
            _, preds = logits.max(dim=1)
            # with open('srad_simple_analysis/test_false_xfg_ids.txt', 'a+') as f:
            #     for xfg_id in batch.xfg_id[batch.y != preds]:
            #         f.write(str(xfg_id.tolist()) + ',')
            #     f.close()
            statistic = Statistic().calculate_statistic(
                batch.y,
                preds,
                2,
            )
        return {"loss": loss, "statistic": statistic}

    def _general_epoch_end(self, outputs: List[Dict], group: str) -> Dict:
        with torch.no_grad():
            mean_loss = torch.stack([out["loss"]
                                     for out in outputs]).mean().item()
            logs = {f"{group}/loss": mean_loss}
            logs.update(
                Statistic.union_statistics([
                    out["statistic"] for out in outputs
                ]).calculate_metrics(group))
            self.log_dict(logs)
            self.log(f"{group}_loss", mean_loss)

    # ===== OPTIMIZERS =====

    def configure_optimizers(
            self) -> Tuple[List[Optimizer], List[_LRScheduler]]:
        return configure_optimizers_alon(self._config.hyper_parameters,
                                         self.parameters())

    # ===== ON EPOCH END =====

    def training_epoch_end(self, outputs: List[Dict]) -> Dict:
        return self._general_epoch_end(outputs, "train")

    def validation_epoch_end(self, outputs: List[Dict]) -> Dict:
        return self._general_epoch_end(outputs, "val")

    def test_epoch_end(self, outputs: List[Dict]) -> Dict:
        # rb_path = join(self._config.res_folder, self._config.name, 'rb_result_30', self._config.dataset.name + '.json')
        # label_metrics = dict()
        # label_metrics['label_pcs'] = self.label_pcs
        # label_metrics['label_vr'] = self.label_vr
        # label_metrics['label_pe'] = self.label_pe
        # label_metrics['label_mi'] = self.label_mi
        # from utils.json_ops import write_json
        # write_json(label_metrics, rb_path)
        return self._general_epoch_end(outputs, "test")
