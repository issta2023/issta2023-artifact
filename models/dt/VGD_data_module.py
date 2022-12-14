from os.path import exists, join
from typing import List, Optional, Tuple

import torch
from omegaconf import DictConfig
from pytorch_lightning import LightningDataModule
import os
import shutil
from models.dt.dataset_build import PGDataset
from math import ceil
from torch_geometric.data import DataLoader


class VGDDataModule(LightningDataModule):
    def __init__(self, config: DictConfig, data_json, noisy_rate, type):
        super().__init__()
        self._config = config
        self.data_json = data_json
        self.d2v_path = os.path.join(config.data_folder, 'CWES', config.dataset.name, 'd2v_model/{}.model'.format(config.dataset.name))
        if noisy_rate is not None:
            self._geo_dir = join(config.data_folder, config.name, config.dataset.name, 
            '{}_{}_percent'.format(config.dataset.name, str(int(noisy_rate * 100))), type)
        else :
            self._geo_dir = join(config.data_folder, config.name, config.dataset.name, 
            config.dataset.name, type)
        if os.path.exists(self._geo_dir):
                if True:
                    shutil.rmtree(self._geo_dir)
                    print(self._geo_dir + " is exist ,delete it")
        

    def prepare_data(self):
        
        self.dataset = PGDataset(self.data_json, self._geo_dir, self.d2v_path)
        sz = len(self.dataset)
        self.train_dataset_slice = slice(0, sz)
        # self.val_dataset_slice = slice(0, sz//10)
        # self.test_dataset_slice = slice(sz // 10, sz // 5)
        # TODO: download data from s3 if not exists

    def setup(self, stage: Optional[str] = None):
        # TODO: collect or convert vocabulary if needed
        pass

    def create_dataloader(
        self,
        dataset_slice: slice,
        shuffle: bool,
        batch_size: int,
        n_workers: int,
    ) -> Tuple[DataLoader, int]:
        dataset = self.dataset[dataset_slice]
        dataloader = DataLoader(
            dataset,
            batch_size=batch_size,
            shuffle=shuffle,
            num_workers=n_workers,
            pin_memory=True,
        )
        return dataloader, len(dataset)

    def train_dataloader(self, *args, **kwargs) -> DataLoader:
        dataloader, n_samples = self.create_dataloader(
            self.train_dataset_slice,
            self._config.hyper_parameters.shuffle_data,
            self._config.hyper_parameters.batch_size,
            0,
        )
        print(
            f"\napproximate number of steps for train is {ceil(n_samples / self._config.hyper_parameters.batch_size)}"
        )
        return dataloader, n_samples

    # def val_dataloader(self, *args, **kwargs) -> DataLoader:
    #     dataloader, n_samples = self.create_dataloader(
    #         self.val_dataset_slice,
    #         False,
    #         self._config.hyper_parameters.test_batch_size,
    #         self._config.num_workers,
    #     )
    #     print(
    #         f"\napproximate number of steps for val is {ceil(n_samples / self._config.hyper_parameters.test_batch_size)}"
    #     )
    #     return dataloader

    # def test_dataloader(self, *args, **kwargs) -> DataLoader:
    #     dataloader, n_samples = self.create_dataloader(
    #         self.test_dataset_slice,
    #         False,
    #         self._config.hyper_parameters.test_batch_size,
    #         self._config.num_workers,
    #     )
    #     print(
    #         f"\napproximate number of steps for test is {ceil(n_samples / self._config.hyper_parameters.test_batch_size)}"
    #     )
    #     self.test_n_samples = n_samples
    #     return dataloader

    def transfer_batch_to_device(self, batch, device: torch.device):
        batch.to(device)
        return batch
