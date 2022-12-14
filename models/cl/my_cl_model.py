# Copyright (C) 2017-2050  Curtis G. Northcutt
# This file is part of cleanlab.
# 
# cleanlab is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# cleanlab is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with cleanlab.  If not, see <https://www.gnu.org/licenses/>.
#
# This agreement applies to this version and all previous versions of cleanlab.


# ## A cleanlab compatible PyTorch CNN classifier.
# 
# ## Note to use this model you'll need to have pytorch installed
# See: https://pytorch.org/get-started/locally/


# Python 2 and 3 compatibility
from __future__ import (
    print_function, absolute_import, division, unicode_literals, with_statement)
from torch.nn.utils.clip_grad import clip_grad_norm_

from torch.utils import data



# Make sure python version is compatible with pyTorch
from cleanlab.util import VersionWarning, clip_values

python_version = VersionWarning(
    warning_str="pyTorch supports Python version 2.7, 3.5, 3.6, 3.7.",
    list_of_compatible_versions=[2.7, 3.5, 3.6, 3.7, 3.8],
)

if python_version.is_compatible():  # pragma: no cover
    from torch_geometric.nn import GCNConv, TopKPooling
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

if python_version.is_compatible():
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


    class VGD_GNN(torch.nn.Module):
        def __init__(
            self,
            config: DictConfig,
        ):
            super().__init__()
            self._config = config
            self.gnn_layer = GCNPoolBlockLayer(self._config)
            self.lin1 = nn.Linear(self._config.gnn.hidden_size * 2,
                                  self._config.gnn.hidden_size)
            self.dropout1 = nn.Dropout(self._config.classifier.drop_out)
            self.lin2 = nn.Linear(self._config.gnn.hidden_size,
                                  self._config.gnn.hidden_size // 2)
            self.dropout2 = nn.Dropout(self._config.classifier.drop_out)
            self.lin3 = nn.Linear(self._config.gnn.hidden_size // 2, 2)
            self.activation = nn.ReLU()
        def forward(self, batch):
            # (batch size, hidden)
            x = self.gnn_layer(batch)
            act = self.activation
            x = self.dropout1(act(self.lin1(x)))
            x = self.dropout2(act(self.lin2(x)))
            # (batch size, output size)
            x = F.log_softmax(self.lin3(x), dim=-1)
            return x


class MY_VGD_GNN(BaseEstimator):  # Inherits sklearn classifier
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
            config: DictConfig,
            dataset,
            no_cuda,
            loader = None
            
    ):
        self.config = config
        self.dataset = dataset
        self.batch_size = config.cl.batch_size
        self.epochs = config.cl.n_epochs
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
        self.model = VGD_GNN(self.config)
        #??????GPU??????
        if self.cuda:  # pragma: no cover
            self.model.cuda(self._GPU)

        self.loader_kwargs = {'num_workers': self.config.num_workers,
                              'pin_memory': True} if self.cuda else {}
        self.loader = loader
        
        
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

        

        

        train_loader = self.get_dataloader(train_idx, True)
        optimizers, schedulers = configure_optimizers_alon(self.config.hyper_parameters,
                                         self.model.parameters())
        optimizer, scheduler = optimizers[0], schedulers[0]
        
        # Train for self.epochs epochs
        self.model.train()
        for epoch in range(self.epochs):

            for batch_idx,data in enumerate(train_loader) :
                device = torch.device("cuda:{}".format(self._GPU) if torch.cuda.is_available() else "cpu")
                data.to(device)
                optimizer.zero_grad()
                output = self.model(data)
                loss = F.nll_loss(output, data.y, weight=None)
                loss.backward()
                optimizer.step()
                if self.log_interval is not None and \
                            batch_idx % self.log_interval == 0:
                    print(
                            'TrainEpoch: {} [{}/{} ({:.0f}%)]\tLoss: {:.6f}'.format(
                                epoch, batch_idx * self.batch_size, len(train_idx),
                                100. * batch_idx / len(train_loader),
                                loss.item()), end='\r'
                    )
            scheduler.step() 

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
        self.model.eval()

        # Run forward pass on model to compute outputs
        outputs = []
        for data in tqdm(test_loader):
            device = torch.device("cuda:{}".format(self._GPU) if torch.cuda.is_available() else "cpu")
            data.to(device)
            output = self.model(data)
            outputs.append(output)

        # Outputs are log_softmax (log probabilities)
        outputs = torch.cat(outputs, dim=0)
        # Convert to probabilities and return the numpy array of shape N x K
        out = outputs.cpu().detach().numpy() if self.cuda else outputs.detach().numpy()
        pred = np.exp(out)
        return pred


#########################################vdp model ##############################################
from models.vuldeepecker.VDP_blstm import VDP_BLSTM
from models.vuldeepecker.buffered_path_context import BufferedPathContext as BPC_vdp
from models.vuldeepecker.VDP_dataset import VDPDataset
from models.vuldeepecker.data_classes import VDPSample, VDPBatch
from torch.utils.data import DataLoader as CL_Dataloader
from utils.matrics import Statistic
class MY_VDP_BLSTM(BaseEstimator):  # Inherits sklearn classifier
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
            config: DictConfig,
            data,
            no_cuda,
            loader = None
            
    ):
        self.config = config
        self.buffer_data = data
        self.epochs = config.cl.n_epochs
        self.no_cuda = no_cuda
        self.seed = config.seed
        self.cuda = not self.no_cuda and torch.cuda.is_available()
        self.log_interval = config.hyper_parameters.log_interval
        self._GPU = config.gpu
        torch.manual_seed(self.seed)
        if self.cuda:  # pragma: no cover
            torch.cuda.manual_seed(self.seed)

        # Instantiate PyTorch model
        self.model = VDP_BLSTM(self.config)
        if self.cuda:  # pragma: no cover
            self.model.cuda(self._GPU)

        self.loader_kwargs = {'num_workers': self.config.num_workers,
                              'pin_memory': True} if self.cuda else {}
        self.loader = loader
        
        
        self.test_batch_size = config.hyper_parameters.test_batch_size
    @staticmethod
    def collate_wrapper(batch: List[VDPSample]) -> VDPBatch:
        return VDPBatch(batch)

    def get_dataloader(self, idx, shuffle_data=False):
    
        sub_buffer_data = self.buffer_data[idx.tolist()]

        
        dataset = VDPDataset(sub_buffer_data, self.config.hyper_parameters.seq_len, False)
        dataloader = CL_Dataloader(
            dataset,
            batch_size=self.config.cl.batch_size,
            collate_fn=self.collate_wrapper,
            num_workers=0,
            pin_memory=True,
        )
        return dataloader

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
                class_weight = class_weight.cuda()
        else:
            class_weight = None

        

        
        optimizers, schedulers = configure_optimizers_alon(self.config.hyper_parameters,
                                         self.model.parameters())
        optimizer, scheduler = optimizers[0], schedulers[0]
        train_loader = self.get_dataloader(train_idx, True)

        
        # Train for self.epochs epochs
        self.model.train()
        for epoch in range(self.epochs):

            for batch_idx,data in enumerate(train_loader) :
                device = torch.device("cuda:{}".format(self._GPU) if torch.cuda.is_available() else "cpu")
                data.move_to_device(device)
                optimizer.zero_grad()
                
                output = self.model(data)
                
                loss = F.nll_loss(output, data.labels, weight=None)
                loss.backward()
                optimizer.step()
                if self.log_interval is not None and \
                            batch_idx % self.log_interval == 0:
                    print(
                            'TrainEpoch: {} [{}/{} ({:.0f}%)]\tLoss: {:.6f}'.format(
                                epoch, batch_idx * self.config.cl.batch_size, len(train_idx),
                                100. * (batch_idx / len(train_loader)),
                                loss.item()), end='\r'
                    )
            scheduler.step() 

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
        
        test_loader = self.get_dataloader(idx, False)

        # sets model.train(False) inactivating dropout and batch-norm layers
        self.model.eval()

        # Run forward pass on model to compute outputs
        outputs = []
        labels = []
        for data in tqdm(test_loader) :
            device = torch.device("cuda:{}".format(self._GPU) if torch.cuda.is_available() else "cpu")
            data.move_to_device(device)
            output = self.model(data)
            outputs.append(output)
            labels.append(data.labels)
        # Outputs are log_softmax (log probabilities)
        outputs = torch.cat(outputs, dim=0)
        labels = torch.cat(labels, dim=0)
        # Convert to probabilities and return the numpy array of shape N x K
        out = outputs.cpu().detach().numpy() if self.cuda else outputs.detach().numpy()
        pred = np.exp(out)


        _, preds = outputs.max(dim=1)
        
        statistic = Statistic().calculate_statistic(
                labels,
                preds,
                2,
            )
        print(statistic.calculate_metrics())
        return pred

#########################################sys model ##############################################
from models.sysevr.SYS_bgru import SYS_BGRU
from models.sysevr.buffered_path_context import BufferedPathContext as BPC_sys
from models.sysevr.SYS_dataset import SYSDataset
from models.sysevr.data_classes import SYSSample, SYSBatch
from torch.utils.data import DataLoader as CL_Dataloader
class MY_SYS_BGRU(BaseEstimator):  # Inherits sklearn classifier
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
            config: DictConfig,
            data,
            no_cuda,
            loader = None
            
    ):
        self.config = config
        self.buffer_data = data
        self.epochs = config.cl.n_epochs
        self.no_cuda = no_cuda
        self.seed = config.seed
        self.cuda = not self.no_cuda and torch.cuda.is_available()
        self.log_interval = config.hyper_parameters.log_interval
        self._GPU = config.gpu
        torch.manual_seed(self.seed)
        if self.cuda:  # pragma: no cover
            torch.cuda.manual_seed(self.seed)

        # Instantiate PyTorch model
        self.model = SYS_BGRU(self.config)
        if self.cuda:  # pragma: no cover
            self.model.cuda(self._GPU)

        self.loader_kwargs = {'num_workers': self.config.num_workers,
                              'pin_memory': True} if self.cuda else {}
        self.loader = loader

        
        self.test_batch_size = config.hyper_parameters.test_batch_size
    @staticmethod
    def collate_wrapper(batch: List[SYSSample]) -> SYSBatch:
        return SYSBatch(batch)

    def get_dataloader(self, idx, shuffle_data = False):
    
        sub_buffer_data = self.buffer_data[idx.tolist()]

        # idxs = []
        # for idx in sub_buffer_data:
        #     idxs.append(idx[3])
        # print(idxs)
        dataset = SYSDataset(sub_buffer_data, self.config.hyper_parameters.seq_len, False)
        dataloader = CL_Dataloader(
            dataset,
            batch_size=self.config.cl.batch_size,
            collate_fn=self.collate_wrapper,
            num_workers=0,
            pin_memory=True,
        )
        return dataloader

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
                class_weight = class_weight.cuda()
        else:
            class_weight = None


        train_loader = self.get_dataloader(train_idx, False)

        optimizers, schedulers = configure_optimizers_alon(self.config.hyper_parameters,
                                         self.model.parameters())
        optimizer, scheduler = optimizers[0], schedulers[0]
        # Train for self.epochs epochs
        self.model.train()
        for epoch in range(self.epochs):

            for batch_idx,data in enumerate(train_loader) :
                device = torch.device("cuda:{}".format(self._GPU) if torch.cuda.is_available() else "cpu")
                data.move_to_device(device)

                optimizer.zero_grad()
                output = self.model(data)
                loss = F.nll_loss(output, data.labels, weight=None)
                loss.backward()
                optimizer.step()

                if self.log_interval is not None and \
                            batch_idx % self.log_interval == 0:
                    # print(
                    #         'TrainEpoch: {} [{}/{} ({:.0f}%)]\tLoss: {:.6f}'.format(
                    #             epoch, batch_idx * self.config.cl.batch_size, len(train_idx),
                    #             100. * (batch_idx / len(train_loader)),
                    #             loss.item()), end='\r'
                    # )
                    pass
            scheduler.step() 

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
        
        
        # print(idx)
     
        test_loader = self.get_dataloader(idx, False)

        # sets model.train(False) inactivating dropout and batch-norm layers
        self.model.eval()

        # Run forward pass on model to compute outputs
        outputs = []
        labels = []
        
        for data in tqdm(test_loader) :
            device = torch.device("cuda:{}".format(self._GPU) if torch.cuda.is_available() else "cpu")
            data.move_to_device(device)

            output = self.model(data)
            outputs.append(output)
            labels.append(data.labels)
            

        # Outputs are log_softmax (log probabilities)
        outputs = torch.cat(outputs, dim=0)
        labels = torch.cat(labels, dim=0)
        # Convert to probabilities and return the numpy array of shape N x K
        out = outputs.cpu().detach().numpy() if self.cuda else outputs.detach().numpy()
        pred = np.exp(out)

    
        # print(pred_c)
        # print(labels)
        

        _, preds = outputs.max(dim=1)
        
        statistic = Statistic().calculate_statistic(
                labels,
                preds,
                2,
            )
        print(statistic.calculate_metrics())

        return pred
    
    
    

#########################################reveal model ##############################################
from models.reveal.REVEAL_ggnn import ClassifyModel
from models.reveal.reveal_dataset_build import RevealDataset
import os
from torch.optim.lr_scheduler import _LRScheduler, LambdaLR
from torch.optim import Adam
from torch.nn.utils.clip_grad import clip_grad_norm_
class MY_REVEAL_GGNN(BaseEstimator):  # Inherits sklearn classifier
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
            config: DictConfig,
            dataset,
            no_cuda,
            class_rate,
            loader = None
            
    ):
        self.config = config
        self.dataset = dataset
        self.epochs = config.cl.n_epochs
        self.no_cuda = no_cuda
        self.seed = config.seed
        self.cuda = not self.no_cuda and torch.cuda.is_available()
        self.log_interval = config.hyper_parameters.log_interval
        self._GPU = config.gpu
        self._geo_dir = os.path.join(self.config.geo_folder, self.config.name, self.config.dataset.name, 'geo')
        
        torch.manual_seed(self.seed)
        if self.cuda:  # pragma: no cover
            torch.cuda.manual_seed(self.seed)

        # Instantiate PyTorch model
        self.model = ClassifyModel(config=self.config, data_class_rate=2/1)
        if self.cuda:  # pragma: no cover
            self.model.cuda(self._GPU)

        self.loader_kwargs = {'num_workers': self.config.num_workers,
                              'pin_memory': True} if self.cuda else {}
        self.loader = loader
        self.class_rate = class_rate
        
        self.test_batch_size = config.hyper_parameters.test_batch_size
    

    def get_dataloader(self, idx, shuffle_data = False):
    
        

        # idxs = []
        # for idx in sub_buffer_data:
        #     idxs.append(idx[3])
        # print(idxs)
        
        sub_dataset = self.dataset[idx.tolist()]
        
        dataloader = DataLoader(
            sub_dataset,
            batch_size=self.config.hyper_parameters.batch_size,
            shuffle=shuffle_data,
            num_workers=0,
            pin_memory=True,
        )
        
        return dataloader

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
                class_weight = class_weight.cuda()
        else:
            class_weight = None

        
        
        

        train_loader = self.get_dataloader(train_idx, False)

        optimizer = Adam(self.model.parameters(), lr=self.config.hyper_parameters.learning_rate,
                         weight_decay=self.config.hyper_parameters.weight_decay,
                         betas=(self.config.hyper_parameters.beta1, self.config.hyper_parameters.beta2))
        scheduler = LambdaLR(
        optimizer, lr_lambda=lambda epoch: self.config.hyper_parameters.decay_gamma**epoch)
        weight_ce = torch.FloatTensor([1, self.class_rate]).to("cuda:{}".format(self.config.gpu) if torch.cuda.is_available() else "cpu")
        loss_function = nn.CrossEntropyLoss(weight=weight_ce)
        # Train for self.epochs epochs
        self.model.train()
        for epoch in range(self.epochs):

            for batch_idx,data in enumerate(train_loader) :
                device = torch.device("cuda:{}".format(self._GPU) if torch.cuda.is_available() else "cpu")
                data.to(device)

                optimizer.zero_grad()
                output = self.model(data)
                loss = loss_function(output, data.y)
                clip_grad_norm_(self.model.parameters(), max_norm=2.0)
                
                loss.backward()
                optimizer.step()

                if self.log_interval is not None and \
                            batch_idx % self.log_interval == 0:
                    # print(
                    #         'TrainEpoch: {} [{}/{} ({:.0f}%)]\tLoss: {:.6f}'.format(
                    #             epoch, batch_idx * self.config.cl.batch_size, len(train_idx),
                    #             100. * (batch_idx / len(train_loader)),
                    #             loss.item()), end='\r'
                    # )
                    pass
            scheduler.step() 

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
        
        
        # print(idx)
     
        test_loader = self.get_dataloader(idx, False)

        # sets model.train(False) inactivating dropout and batch-norm layers
        self.model.eval()

        # Run forward pass on model to compute outputs
        outputs = []
        labels = []
        
        for data in tqdm(test_loader) :
            device = torch.device("cuda:{}".format(self._GPU) if torch.cuda.is_available() else "cpu")
            data.to(device)
            output = self.model(data)
            outputs.append(output)
            labels.append(data.y)
            

        # Outputs are log_softmax (log probabilities)
        outputs = torch.cat(outputs, dim=0)
        labels = torch.cat(labels, dim=0)
        # Convert to probabilities and return the numpy array of shape N x K
        out = outputs.cpu().detach().numpy() if self.cuda else outputs.detach().numpy()
        pred = np.exp(out)

    
        # print(pred_c)
        # print(labels)
        

        _, preds = outputs.max(dim=1)
        
        statistic = Statistic().calculate_statistic(
                labels,
                preds,
                2,
            )
        print(statistic.calculate_metrics())

        return pred