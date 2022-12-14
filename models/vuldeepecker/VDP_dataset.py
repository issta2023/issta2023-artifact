from math import ceil
from os.path import exists, join
from typing import Dict, Tuple, List

import numpy
import torch
from torch.utils.data import IterableDataset, DataLoader

from models.vuldeepecker.buffered_path_context import BufferedPathContext
from models.vuldeepecker.data_classes import VDPSample


class VDPDataset(IterableDataset):
    def __init__(self, data: BufferedPathContext, seq_len: int, shuffle: bool):
        super().__init__()
        self._total_n_samples = 0
        self.seq_len = seq_len
        self.shuffle = shuffle
        self._prepare_buffer(data)

    def __iter__(self):
        worker_info = torch.utils.data.get_worker_info()
        if worker_info is None:  # single-process data loading, return the full iterator
            self._cur_sample_idx = 0
            self._end_sample_idx = self._total_n_samples
        else:
            worker_id = worker_info.id
            per_worker = int(
                ceil(self._total_n_samples / float(worker_info.num_workers)))
            self._cur_sample_idx = per_worker * worker_id
            self._end_sample_idx = min(self._cur_sample_idx + per_worker,
                                       self._total_n_samples)
        return self

    def _prepare_buffer(self,  data: BufferedPathContext) -> None:
        self._cur_buffered_path_context = data
        self._total_n_samples = len(self._cur_buffered_path_context)
        self._order = numpy.arange(self._total_n_samples)
        if self.shuffle:
            self._order = numpy.random.permutation(self._order)
        self._cur_sample_idx = 0

    def __next__(self) -> Tuple[numpy.ndarray, int, int]:
        if self._cur_sample_idx >= self._end_sample_idx:
            raise StopIteration()
        gadget, label, is_back, words_for_label, idx, flip = self._cur_buffered_path_context[
            int(self._order[self._cur_sample_idx])]

        # select max_context paths from sample
        words_for_label = min(self.seq_len, words_for_label)
        if is_back:
            gadget = gadget[len(gadget) - words_for_label:len(gadget)]
        else:
            gadget = gadget[:words_for_label]
        self._cur_sample_idx += 1
        return VDPSample(tokens=gadget, label=label, is_back=is_back, n_tokens=words_for_label, idx=idx, flip=flip)
    def __len__(self) -> int:
        return self.get_n_samples()
    def get_n_samples(self):
        return self._total_n_samples


