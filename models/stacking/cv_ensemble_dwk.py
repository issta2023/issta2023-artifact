from numpy.lib import utils
from scipy.sparse import data
from torch_geometric.nn import GCNConv, TopKPooling, GATConv, GraphSAGE, GatedGraphConv, GraphConv
from torch_geometric.nn import global_mean_pool as gap, global_max_pool as gmp
from typing import Tuple, Dict, List, Union
from sklearn.base import BaseEstimator
from tqdm import tqdm
import torch
from omegaconf import DictConfig
from utils.training import configure_optimizers_alon
import numpy as np
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.data import DataLoader
from sklearn.model_selection import StratifiedKFold
from typing import Tuple, Dict, List, Union
from omegaconf import DictConfig
from utils.training import configure_optimizers_alon
from torch.optim import Adam, Optimizer, SGD, Adamax, RMSprop
from utils.training import cut_gadgets_encoded_contexts
import torch.nn as nn
import numpy
import torch.nn.functional as F
from utils.training import cut_sys_encoded_contexts
from utils.matrics import Statistic
import pprint as pp
from pytorch_lightning.core.lightning import LightningModule
      
class GCNPoolBlockLayer(nn.Module):
    """graph conv-pool block

    graph convolutional + graph pooling + graph readout

    :attr GCL: graph conv layer
    :attr GPL: graph pooling layer
    """
    def __init__(self, config: DictConfig, gnn_module_name='GCNConv'):
        super(GCNPoolBlockLayer, self).__init__()
        self._config = config
        self.layer_num = self._config.gnn.layer_num
        self.init_GCL_GPL(gnn_module_name=gnn_module_name)
        
    def init_GCL_GPL(self, gnn_module_name):
        input_size = self._config.hyper_parameters.vector_length
        print(f"-------------------------init GNN module as {gnn_module_name}------------------------------")
        if gnn_module_name in ['GCNConv', 'GATConv', 'GraphConv']:
            if gnn_module_name == 'GCNConv':
                GNN_Module = GCNConv
            elif gnn_module_name == 'GATConv':
                GNN_Module = GATConv
            else:
                GNN_Module = GraphConv
            self.input_GCL = GNN_Module(input_size, self._config.gnn.hidden_size)

            self.input_GPL = TopKPooling(self._config.gnn.hidden_size,
                                     ratio=self._config.gnn.pooling_ratio)

            for i in range(self.layer_num - 1):
                setattr(self, f"hidden_GCL{i}",
                        GNN_Module(self._config.gnn.hidden_size, self._config.gnn.hidden_size))
                setattr(
                    self, f"hidden_GPL{i}",
                    TopKPooling(self._config.gnn.hidden_size,
                                ratio=self._config.gnn.pooling_ratio))
        elif gnn_module_name == 'GraphSAGE':
            self.input_GCL = GraphSAGE(input_size, self._config.gnn.hidden_size, num_layers=1)

            self.input_GPL = TopKPooling(self._config.gnn.hidden_size,
                                     ratio=self._config.gnn.pooling_ratio)

            for i in range(self.layer_num - 1):
                setattr(self, f"hidden_GCL{i}",
                        GraphSAGE(self._config.gnn.hidden_size, self._config.gnn.hidden_size, num_layers=1))
                setattr(
                    self, f"hidden_GPL{i}",
                    TopKPooling(self._config.gnn.hidden_size,
                                ratio=self._config.gnn.pooling_ratio))
        elif gnn_module_name == 'GatedGraphConv':
            self._config.gnn.hidden_size = input_size
            self.input_GCL = GatedGraphConv(input_size, num_layers=1)

            self.input_GPL = TopKPooling(self._config.gnn.hidden_size,
                                     ratio=self._config.gnn.pooling_ratio)

            for i in range(self.layer_num - 1):
                setattr(self, f"hidden_GCL{i}",
                        GatedGraphConv(self._config.gnn.hidden_size, num_layers=1))
                setattr(
                    self, f"hidden_GPL{i}",
                    TopKPooling(self._config.gnn.hidden_size,
                                ratio=self._config.gnn.pooling_ratio))


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


class VGD_GNN(nn.Module):
    _activations = {
        "relu": nn.ReLU(),
        "sigmoid": nn.Sigmoid(),
        "tanh": nn.Tanh(),
        "lkrelu": nn.LeakyReLU(0.3)
    }

    def __init__(
        self,
        config: DictConfig,
        gnn_module_name='GCNConv'
    ):
        super().__init__()
        self._config = config
        self.init_layers(gnn_module_name)

    def init_layers(self, gnn_module_name):
        self.gnn_layer = GCNPoolBlockLayer(self._config, gnn_module_name)
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
            
class CV_ENSEMBLE_DWK(torch.nn.Module):
    def __init__(
        self,
        model_config,
        stacking_config: DictConfig
    ):
        super().__init__()
        self._config = stacking_config
        self.model_config = model_config
        self.trained_models = []
        self._GPU = self._config.gpu     
        self.loss = F.nll_loss
        self.device = torch.device("cuda:{}".format(self._GPU) if torch.cuda.is_available() else "cpu")
        self.gnn_module_name = ['GCNConv', 'GATConv', 'GraphConv', 'GatedGraphConv', 'GraphSAGE']
    def forward(self, batch): 
        predictions = []  
        for model in self.trained_models:
            model.eval()
            batch.to(self.device)
            model.to(self.device)
            out = model(batch)
            predictions.append(torch.exp(out))
        pred = torch.stack(predictions).mean(dim=0)
        return pred
    
    def get_dataloader(self, dataset, batch_size, idx=None, shuffle_data=False):
        if idx:
            sub_dataset = dataset[idx.tolist()]
        else:
            sub_dataset = dataset
        loader = DataLoader(
            sub_dataset,
            batch_size = batch_size,
            shuffle = shuffle_data,
            num_workers = 8,
            pin_memory = True,
        )
        return loader
    
    def k_fold_train(self, dataset, cv_n_folds=5):

        X, s, xfg_id = [i.x for i in dataset], [i.y for i in dataset], [i.xfg_id.item() for i in dataset]
        s = np.asarray(s)
        # kf = StratifiedKFold(n_splits=cv_n_folds, shuffle=True, random_state=self._config.seed)           
        # for fold, (cv_train_idx, cv_holdout_idx) in enumerate(kf.split(X, s)):
        config = self.model_config
        train_dataloader = self.get_dataloader(dataset, config.hyper_parameters.batch_size, shuffle_data = True)
        
        for fold in range(cv_n_folds):
            print(f'===============================Start fold {fold}=================================')
            model = VGD_GNN(self.model_config, gnn_module_name=self.gnn_module_name[fold])
            
            if torch.cuda.is_available():
                model.cuda(self._GPU)
            optimizers, schedulers = configure_optimizers_alon(config.hyper_parameters,
                                         model.parameters())
            optimizer, scheduler = optimizers[0], schedulers[0]
            # test_dataloader = self.get_dataloader(dataset, config.hyper_parameters.test_batch_size, cv_holdout_idx, False)
            #????????????
            model.train()
            for epoch in tqdm(range(self._config.cl.n_epochs)):
                for batch in train_dataloader:
                    
                    batch.to(self.device)
                    optimizer.zero_grad()
                    output = model(batch)
                    loss = F.nll_loss(output, batch.y, weight=None)
                    loss.backward()
                    optimizer.step()
                scheduler.step() 
            #????????????
            # model.eval()
            # outs = []
            # for batch in test_dataloader:
            #     batch.to(self.device)
            #     output = model(batch)
            #     loss = F.nll_loss(output, batch.y)
            #     with torch.no_grad():
            #         _, preds = output.max(dim=1)
            #         statistic = Statistic().calculate_statistic(
            #             batch.y,
            #             preds,
            #             2,
            #         )
            #     outs.append({"loss": loss, "statistic": statistic})
            # with torch.no_grad():
            #     mean_loss = torch.stack([out["loss"]
            #                      for out in outs]).mean().item()
            #     logs = {"test/loss": mean_loss}
            #     logs.update(
            #         Statistic.union_statistics([
            #         out["statistic"] for out in outs
            #     ]).calculate_metrics("test"))
            #     pp.pprint(logs)
            self.trained_models.append(model)
            print(f'===============================End fold {fold}=================================')
                # Outputs are log_softmax (log probabilities)

        
    def predict_proba(self, batch):
        self.eval()
        preds = self(batch)
        return preds
    
    
    def _general_epoch_end(self, outputs: List[Dict], group: str) -> Dict:
        with torch.no_grad():
            mean_loss = torch.stack([out["loss"]
                                     for out in outputs]).mean().item()
            logs = {f"{group}/loss": mean_loss}
            logs.update(
                Statistic.union_statistics([
                    out["statistic"] for out in outputs
                ]).calculate_metrics(group))
            pp.pprint(logs)
            
            
    def test(self, test_dataset):
        
        loader = DataLoader(
            test_dataset,
            batch_size = len(test_dataset),
            shuffle = False,
            num_workers = 1,
            pin_memory = True,
        )
       
        outputs = []
        self.eval()
        for batch in tqdm(loader):
            logits = self.predict_proba(batch)
            loss = self.loss(logits, batch.y)
            with torch.no_grad():
                _, preds = logits.max(dim=1)
                statistic = Statistic().calculate_statistic(
                    batch.y,
                    preds,
                    2,
                )
                outputs.append({"loss": loss, "statistic": statistic})
        self._general_epoch_end(outputs, "test")
        
        # from utils.json_ops import write_json
        # pp.pprint(self.result)
        # write_json(self.result, 'liner_input.json')
                
       
        
        
class CL_CV_ENSEMBLE_DWK(BaseEstimator):  # Inherits sklearn classifier
    """Wraps a PyTorch CNN for the MNIST dataset within an sklearn template

    Defines ``.fit()``, ``.predict()``, and ``.predict_proba()`` functions. This
    template enables the PyTorch CNN to flexibly be used within the sklearn
    architecture -- meaning it can be passed into functions like
    cross_val_predict as if it were an sklearn model. The cleanlab library
    requires that all models adhere to this basic sklearn template and thus,
    this class allows a PyTorch CNN to be used in for learning with noisy
    labels among other things.

    Parameters
    ----------
    batch_size: int
    epochs: int
    log_interval: int
    lr: float
    momentum: float
    no_cuda: bool
    seed: int
    test_batch_size: int, default=None
    dataset: {'mnist', 'sklearn-digits'}
    loader: {'train', 'test'}
      Set to 'test' to force fit() and predict_proba() on test_set

    Note
    ----
    Be careful setting the ``loader`` param, it will override every other loader
    If you set this to 'test', but call .predict(loader = 'train')
    then .predict() will still predict on test!

    Attributes
    ----------
    batch_size: int
    epochs: int
    log_interval: int
    lr: float
    momentum: float
    no_cuda: bool
    seed: int
    test_batch_size: int, default=None
    dataset: {'mnist', 'sklearn-digits'}
    loader: {'train', 'test'}
      Set to 'test' to force fit() and predict_proba() on test_set

    Methods
    -------
    fit
      fits the model to data.
    predict
      get the fitted model's prediction on test data
    predict_proba
      get the fitted model's probability distribution over clases for test data
    """
    def __init__(
            self,
            model_config,
            dataset,
            config: DictConfig,
            no_cuda,
            loader = None
            
    ):
        self.config = config
        self.dataset = dataset
        self.batch_size = config.cl.batch_size
        self.lr = config.hyper_parameters.learning_rate
        self.no_cuda = no_cuda
        self.seed = config.seed
        self._GPU = config.gpu
        self.cuda = not self.no_cuda and torch.cuda.is_available()
        self.log_interval = config.hyper_parameters.log_interval
        torch.manual_seed(self.seed)
        if self.cuda:  # pragma: no cover
            torch.cuda.manual_seed(self.seed)

        # Instantiate PyTorch model
        self.model = CV_ENSEMBLE_DWK(model_config=model_config, stacking_config=config)
        #??????GPU??????
        if self.cuda:  # pragma: no cover
            self.model.cuda(self._GPU)

        self.loader_kwargs = {'num_workers': self.config.num_workers,
                              'pin_memory': True} if self.cuda else {}
        self.loader = loader
        
        self.cnt_dict = dict()
        self.test_batch_size = config.hyper_parameters.test_batch_size

    def get_dataloader(self, idx, shuffle_data=False):
    
        
        sub_dataset = self.dataset[idx.tolist()]
        loader = DataLoader(
            sub_dataset,
            batch_size = self.batch_size,
            shuffle = shuffle_data,
            num_workers = self.config.num_workers,
            pin_memory = True,
        )
        return loader
    
    def get_sub_dataset(self, idx):
        return self.dataset[idx.tolist()]

    def fit(self, train_idx, train_labels=None, sample_weight=None,
            loader='train'):
        """This function adheres to sklearn's "fit(X, y)" format for
        compatibility with scikit-learn. ** All inputs should be numpy
        arrays, not pyTorch Tensors train_idx is not X, but instead a list of
        indices for X (and y if train_labels is None). This function is a
        member of the cnn class which will handle creation of X, y from the
        train_idx via the train_loader. """
        if self.loader is not None:
            loader = self.loader
        if train_labels is not None and len(train_idx) != len(train_labels):
            raise ValueError(
                "Check that train_idx and train_labels are the same length.")

        if sample_weight is not None:  # pragma: no cover
            if len(sample_weight) != len(train_labels):
                raise ValueError("Check that train_labels and sample_weight "
                                 "are the same length.")
            class_weight = sample_weight[
                np.unique(train_labels, return_index=True)[1]]
            class_weight = torch.from_numpy(class_weight).float()
            if self.cuda:
                class_weight = class_weight.cuda(self._GPU)
        else:
            class_weight = None

        
        train_dataset = self.get_sub_dataset(train_idx)
        self.model.k_fold_train(train_dataset, cv_n_folds=5)
        
        
    def predict(self, idx=None, loader=None):
        """Get predicted labels from trained model."""
        # get the index of the max probability
        probs = self.predict_proba(idx)
        return probs.argmax(axis=1)

    
    def predict_proba(self, idx=None, loader=None):
        if self.loader is not None:
            loader = self.loader
        # if loader is None:
        #     is_test_idx = idx is not None and len(
        #         idx) == self.test_size and np.all(
        #         np.array(idx) == np.arange(self.test_size))
        #     loader = 'test' if is_test_idx else 'train'
        test_loader = self.get_dataloader(idx)

        # sets model.train(False) inactivating dropout and batch-norm layers

        # Run forward pass on model to compute outputs
        outputs = []
        for batch in tqdm(test_loader):
            device = torch.device("cuda:{}".format(self._GPU) if torch.cuda.is_available() else "cpu")
            batch.to(device)
            output = self.model.predict_proba(batch)
            outputs.append(output)

        # Outputs are log_softmax (log probabilities)
        outputs = torch.cat(outputs, dim=0)
        # Convert to probabilities and return the numpy array of shape N x K
        pred = outputs.cpu().detach().numpy() if self.cuda else outputs.detach().numpy()
        # pred = np.exp(out)
        return pred