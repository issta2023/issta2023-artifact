from os.path import exists, join
from models.sysevr.buffered_path_context import BufferedPathContext
from typing import List, Optional, Tuple

import torch
from omegaconf import DictConfig
from pytorch_lightning import LightningDataModule
from torch.utils.data import DataLoader, Dataset
from utils.vectorize_gadget import GadgetVectorizer
from utils.json_ops import read_json
from models.sysevr.data_classes import SYSSample, SYSBatch
from models.sysevr.SYS_dataset import SYSDataset
from math import ceil


class SYSDataModule(LightningDataModule):
    def __init__(self, config: DictConfig, data_json, noise_rate, type):
        super().__init__()
        self._config = config
        self._dataset_dir = join(config.data_folder, config.name,
                                 config.dataset.name)
        self.noise_rate = noise_rate
        self.config = config
        self.data_json = data_json
        self.w2v_path = join(self._dataset_dir, 'w2v.model')

       
    def prepare_data(self):
        # TODO: download data from s3 if not exists
        if not exists(self._dataset_dir):
            raise ValueError(
                f"There is no file in passed path ({self._dataset_dir})")
        vectorizer = GadgetVectorizer(self.config)

        vectorizer.load_model(w2v_path=self.w2v_path)

        X = []
        labels = []
        count = 0
        for gadget in self.data_json:
            count += 1
            # print("Processing gadgets...", count, end="\r")
            vector, backwards_slice = vectorizer.vectorize2(
                gadget["gadget"])  # [word len, embedding size]
            # vectors.append(vector)
            X.append((vector, gadget['xfg_id'], gadget['flip']))

            labels.append(gadget["val"])

        self.train_data = BufferedPathContext.create_from_lists(X, labels)



    def setup(self, stage: Optional[str] = None):
        # TODO: collect or convert vocabulary if needed
        pass

    @staticmethod
    def collate_wrapper(batch: List[SYSSample]) -> SYSBatch:
        return SYSBatch(batch)

    def create_dataloader(
        self,
        data: BufferedPathContext,
        seq_len: int,
        shuffle: bool,
        batch_size: int,
        n_workers: int,
    ) -> Tuple[DataLoader, int]:
        dataset = SYSDataset(data, seq_len, False)
        dataloader = DataLoader(
            dataset,
            batch_size=batch_size,
            collate_fn=self.collate_wrapper,
            num_workers=n_workers,
            pin_memory=True,
        )
        return dataloader, dataset.get_n_samples()

    def train_dataloader(self, *args, **kwargs) -> DataLoader:
        train_data = self.train_data
        dataloader, n_samples = self.create_dataloader(
            train_data,
            self._config.hyper_parameters.seq_len,
            self._config.hyper_parameters.shuffle_data,
            self._config.hyper_parameters.batch_size,
            0,
        )
        print(
            f"\napproximate number of steps for train is {ceil(n_samples / self._config.hyper_parameters.batch_size)}"
        )
        return dataloader, n_samples

    # def val_dataloader(self, *args, **kwargs) -> DataLoader:
    #     val_data = BufferedPathContext.load(self._val_data_file)
    #     dataloader, n_samples = self.create_dataloader(
    #         val_data,
    #         self._config.hyper_parameters.seq_len,
    #         False,
    #         self._config.hyper_parameters.test_batch_size,
    #         self._config.num_workers,
    #     )
    #     print(
    #         f"\napproximate number of steps for val is {ceil(n_samples / self._config.hyper_parameters.test_batch_size)}"
    #     )
    #     return dataloader

    # def test_dataloader(self, *args, **kwargs) -> DataLoader:
    #     test_data = BufferedPathContext.load(self._test_data_file)
    #     dataloader, n_samples = self.create_dataloader(
    #         test_data,
    #         self._config.hyper_parameters.seq_len,
    #         False,
    #         self._config.hyper_parameters.test_batch_size,
    #         self._config.num_workers,
    #     )
    #     print(
    #         f"\napproximate number of steps for test is {ceil(n_samples / self._config.hyper_parameters.test_batch_size)}"
    #     )
    #     self.test_n_samples = n_samples
    #     return dataloader

    def transfer_batch_to_device(self, batch: SYSBatch,
                                 device: torch.device) -> SYSBatch:
        batch.move_to_device(device)
        return batch
