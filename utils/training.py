from typing import List, Tuple, Iterable

import numpy
import torch
from torch import Tensor
from omegaconf import DictConfig
from torch.optim import Adam, Optimizer, SGD, Adamax
from torch.optim.lr_scheduler import _LRScheduler, LambdaLR


def configure_optimizers_alon(
    hyper_parameters: DictConfig, parameters: Iterable[torch.Tensor]
) -> Tuple[List[Optimizer], List[_LRScheduler]]:
    """ Create optimizers like in original Alon work
    https://github.com/tech-srl/code2seq/blob/a01076ef649d298e5f90ac2ce1f6a42f4ff49cc2/model.py#L386-L397
    :param hyper_parameters: hyper parameters
    :param parameters: model parameters for optimization
    :return: list of optimizers and schedulers
    """
    optimizer: Optimizer
    if hyper_parameters.optimizer == "Momentum":
        # using the same momentum value as in original realization by Alon
        optimizer = SGD(
            parameters,
            hyper_parameters.learning_rate,
            momentum=0.95,
            nesterov=hyper_parameters.nesterov,
            weight_decay=hyper_parameters.weight_decay,
        )
    elif hyper_parameters.optimizer == "Adam":
        optimizer = Adam(parameters,
                         hyper_parameters.learning_rate,
                         weight_decay=hyper_parameters.weight_decay)
    elif hyper_parameters.optimizer == "Adamax":
        optimizer = Adam(parameters,
                         hyper_parameters.learning_rate)
    else:
        raise ValueError(
            f"Unknown optimizer name: {hyper_parameters.optimizer}, try one of: Adam, Momentum, Adamax"
        )
    scheduler = LambdaLR(
        optimizer, lr_lambda=lambda epoch: hyper_parameters.decay_gamma**epoch)
    return [optimizer], [scheduler]


def segment_sizes_to_slices(sizes: Tensor) -> List:
    cum_sums = numpy.cumsum(sizes.cpu())
    start_of_segments = numpy.append([0], cum_sums[:-1])
    return [
        slice(start, end) for start, end in zip(start_of_segments, cum_sums)
    ]


def cut_encoded_contexts(
        encoded_contexts: torch.Tensor,
        contexts_per_label: List[int],
        mask_value: float = -1e9) -> Tuple[torch.Tensor, torch.Tensor]:
    """Cut encoded contexts into batches

    :param encoded_contexts: [n contexts; units]
    :param contexts_per_label: [batch size]
    :param mask_value:
    :return: [batch size; max context len; units], [batch size; max context len]
    """
    batch_size = len(contexts_per_label)
    max_context_len = max(contexts_per_label)

    batched_contexts = encoded_contexts.new_zeros(
        (batch_size, max_context_len, encoded_contexts.shape[-1]))
    attention_mask = encoded_contexts.new_zeros((batch_size, max_context_len))

    context_slices = segment_sizes_to_slices(contexts_per_label)
    for i, (cur_slice,
            cur_size) in enumerate(zip(context_slices, contexts_per_label)):
        batched_contexts[i, :cur_size] = encoded_contexts[cur_slice]
        attention_mask[i, cur_size:] = mask_value

    return batched_contexts, attention_mask


def cut_gadgets_encoded_contexts(
        gadgets: torch.Tensor,
        is_back: List[bool],
        words_per_label: List[int],
        sen_len,
        mask_value: float = -1e9) -> Tuple[torch.Tensor, torch.Tensor]:
    """Cut encoded gadgets into batches

    :param gadgets: [total word length, input size]
    :param is_back:
    :param words_per_label: word length for each label
    :param sen_len: length of sequence
    :return: [batch size, sen_len; input size], [batch size; sen_len]
    """
    batch_size = len(words_per_label)

    batched_gadgets = gadgets.new_zeros(
        (batch_size, sen_len, gadgets.shape[-1]))
    attention_mask = gadgets.new_zeros((batch_size, sen_len))

    gadget_slices = segment_sizes_to_slices(words_per_label)
    for i, (cur_slice,
            cur_size) in enumerate(zip(gadget_slices, words_per_label)):
        # batched_gadgets[i, :cur_size] = gadgets[cur_slice]
        # attention_mask[i, cur_size:] = mask_value
        if is_back[i]:
            batched_gadgets[i, sen_len - cur_size:sen_len] = gadgets[
                cur_slice]  # [sen_len, input size]
            attention_mask[i, :sen_len - cur_size] = mask_value
        else:
            batched_gadgets[i, :cur_size] = gadgets[cur_slice]
            attention_mask[i, cur_size:] = mask_value

    return batched_gadgets, attention_mask


def cut_sys_encoded_contexts(
        sys: torch.Tensor,
        words_per_label: List[int],
        sen_len,
        mask_value: float = -1e9) -> Tuple[torch.Tensor, torch.Tensor]:
    """Cut encoded gadgets into batches

    :param sys: [total word length, input size]
    :param words_per_label: word length for each label
    :param sen_len: length of sequence
    :return: [batch size, sen_len; input size], [batch size; sen_len]
    """
    batch_size = len(words_per_label)

    batched_gadgets = sys.new_zeros((batch_size, sen_len, sys.shape[-1]))
    attention_mask = sys.new_zeros((batch_size, sen_len))

    gadget_slices = segment_sizes_to_slices(words_per_label)
    for i, (cur_slice,
            cur_size) in enumerate(zip(gadget_slices, words_per_label)):
        # batched_gadgets[i, :cur_size] = gadgets[cur_slice]
        # attention_mask[i, cur_size:] = mask_value

        batched_gadgets[i, :cur_size] = sys[cur_slice]
        attention_mask[i, cur_size:] = mask_value

    return batched_gadgets, attention_mask