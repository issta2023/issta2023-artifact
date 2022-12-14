from argparse import ArgumentParser
from logging import error
import os
from os.path import join
from statistic import statistic_cl_and_dt
from confident_learning import select_noise_from_cl_result
import numpy as np
from typing import Tuple
import json
import torch
import jsonlines
from omegaconf import DictConfig
from pytorch_lightning import seed_everything, Trainer, LightningModule, LightningDataModule
from pytorch_lightning.callbacks import ModelCheckpoint, EarlyStopping, LearningRateMonitor
from pytorch_lightning.loggers import WandbLogger, TensorBoardLogger
from models.reveal.REVEAL_ggnn import ClassifyModel
from models.reveal.REVEAL_data_module import RevealDataModule
from utils.callback import UploadCheckpointCallback, PrintEpochResultCallback, CollectResCallback
from utils.common import print_config, filter_warnings, get_config
from utils.plot_result import plot_approach_f1, plot_cwe_f1
from utils.json_ops import get_data_json
from pre_train import doc2vec
from statistic import get_dt_found_noise_ids
from utils.json_ops import read_json, write_json

def train(config: DictConfig, method:str = None, noise_rate:int = 0, rm_xfg_list:list=[], rm_count:int=0, resume_from_checkpoint: str = None):
    """
    @description  : deepwukong train 
    ---------
    @param  : 
                json_data :  samples for train
                method: reduce noisy sample method : df or cl
                noise_rate: 0.1, 0.3, 0.5
    -------
    @Returns  :
    -------
    """
    filter_warnings()
    print_config(config)
    # seed_everything(config.seed)
    data_module = RevealDataModule(config, noise_rate=noise_rate, rm_xfg_list=rm_xfg_list, rm_count = rm_count)
    
    model = ClassifyModel(config, data_module.data_class_rate)
    # if method == 'dt':
    #     data_module = VGDDataModule(config, json_data, 0)
    # else:
    # define logger
    # wandb logger
    # wandb_logger = WandbLogger(project=f"{config.name}-{config.dataset.name}",
    #                            log_model=True,
    #                            offline=config.log_offline)
    # wandb_logger.watch(model)
    # checkpoint_callback = ModelCheckpoint(
    #     dirpath=wandb_logger.experiment.dir,
    #     filename="{epoch:02d}-{val_loss:.4f}",
    #     period=config.save_every_epoch,
    #     save_top_k=-1,
    # )
    # upload_checkpoint_callback = UploadCheckpointCallback(
    #     wandb_logger.experiment.dir)

    # tensorboard logger
    tensorlogger = TensorBoardLogger(join("ts_logger", config.name),
                                     config.dataset.name)
    # define model checkpoint callback
    checkpoint_callback = ModelCheckpoint(
        dirpath=join(tensorlogger.log_dir, "checkpoints"),
        monitor="val_loss",
        filename="{epoch:02d}-{val_loss:.4f}",
        period=config.save_every_epoch,
        save_top_k=3,
    )
    upload_checkpoint_callback = UploadCheckpointCallback(
        join(tensorlogger.log_dir, "checkpoints"))

    # define early stopping callback
    early_stopping_callback = EarlyStopping(
        patience=config.hyper_parameters.patience,
        monitor="val_loss",
        verbose=True,
        mode="min")
    # define callback for printing intermediate result
    print_epoch_result_callback = PrintEpochResultCallback("train", "val")
    collect_test_res_callback = CollectResCallback(config, data_module , method, noise_rate)
    # use gpu if it exists
    gpu = [0] if torch.cuda.is_available() else None
    print(gpu)
    # define learning rate logger
    lr_logger = LearningRateMonitor("step")
    trainer = Trainer(
        max_epochs=config.hyper_parameters.n_epochs,
        gradient_clip_val=config.hyper_parameters.clip_norm,
        deterministic=True,
        check_val_every_n_epoch=config.val_every_epoch,
        log_every_n_steps=config.log_every_epoch,
        logger=[tensorlogger],
        reload_dataloaders_every_epoch=config.hyper_parameters.
        reload_dataloader,
        gpus=gpu,
        progress_bar_refresh_rate=config.progress_bar_refresh_rate,
        callbacks=[
            lr_logger,  early_stopping_callback, checkpoint_callback,
            print_epoch_result_callback, upload_checkpoint_callback,
            collect_test_res_callback
        ],
        resume_from_checkpoint=resume_from_checkpoint,
    )
    print(get_parameter_number(net=model))
    trainer.fit(model=model, datamodule=data_module)
    trainer.test(model=model, datamodule=data_module)
    
    # trainer.test()
def test(config: DictConfig, method:str = None, noise_rate:int = 0, rm_xfg_list:list=[], rm_count:int=0, resume_from_checkpoint: str = None):
    """
    @description  : deepwukong train 
    ---------
    @param  : 
                json_data :  samples for train
                method: reduce noisy sample method : df or cl
                noise_rate: 0.1, 0.3, 0.5
    -------
    @Returns  :
    -------
    """
    
    filter_warnings()
    print_config(config)
    # seed_everything(config.seed)
    data_module = RevealDataModule(config, noise_rate=noise_rate, rm_xfg_list=rm_xfg_list, rm_count = rm_count)
    
    model = ClassifyModel(config, data_module.data_class_rate)
    # if method == 'dt':
    #     data_module = VGDDataModule(config, json_data, 0)
    # else:
    # define logger
    # wandb logger
    # wandb_logger = WandbLogger(project=f"{config.name}-{config.dataset.name}",
    #                            log_model=True,
    #                            offline=config.log_offline)
    # wandb_logger.watch(model)
    # checkpoint_callback = ModelCheckpoint(
    #     dirpath=wandb_logger.experiment.dir,
    #     filename="{epoch:02d}-{val_loss:.4f}",
    #     period=config.save_every_epoch,
    #     save_top_k=-1,
    # )
    # upload_checkpoint_callback = UploadCheckpointCallback(
    #     wandb_logger.experiment.dir)

    # tensorboard logger
    # define model checkpoint callback

    # define early stopping callback
    early_stopping_callback = EarlyStopping(
        patience=config.hyper_parameters.patience,
        monitor="val_loss",
        verbose=True,
        mode="min")
    # define callback for printing intermediate result
    print_epoch_result_callback = PrintEpochResultCallback("train", "val")
    collect_test_res_callback = CollectResCallback(config, data_module , method, noise_rate)
    # use gpu if it exists
    gpu = [0] if torch.cuda.is_available() else None
    print(gpu)
    # define learning rate logger
    lr_logger = LearningRateMonitor("step")
    trainer = Trainer(
        max_epochs=config.hyper_parameters.n_epochs,
        gradient_clip_val=config.hyper_parameters.clip_norm,
        deterministic=True,
        check_val_every_n_epoch=config.val_every_epoch,
        log_every_n_steps=config.log_every_epoch,
        reload_dataloaders_every_epoch=config.hyper_parameters.
        reload_dataloader,
        gpus=gpu,
        progress_bar_refresh_rate=config.progress_bar_refresh_rate,
        callbacks=[
            lr_logger,  early_stopping_callback,
            print_epoch_result_callback,
            collect_test_res_callback
        ],
        resume_from_checkpoint=resume_from_checkpoint,
    )
    print(get_parameter_number(net=model))
    trainer.test(model=model, datamodule=data_module)
def get_parameter_number(net):
    total_num = sum(p.numel() for p in net.parameters())
    trainable_num = sum(p.numel() for p in net.parameters() if p.requires_grad)
    return {'Total': total_num, 'Trainable': trainable_num}



def reveal_cl_train(config, noise_rate):
    """
    @description  : train deepwukong after removing noisy samples found by cl 
    ---------
    @param  :
    -------
    @Returns  :
    -------
    """
    
    
    print_config(config)
    # ws_fliped_path = '/home/niexu/project/python/deepwukong/data/diff_train/CWE119/flipped/bigjson_flip.json'
    
    cl_result_path = join(config.res_folder, config.name ,'cl_result', config.dataset.name, str(int(noise_rate * 100)) + '_percent_res.json')
    result = read_json(cl_result_path)
    xfg_ids = np.array(result['xfg_id'])
    flipped = np.array(result['flip'])
    error_labels = result['error_label']
    flipped = flipped[error_labels]
    print(np.sum(flipped))
    rm_xfg_list = xfg_ids[error_labels].tolist()
    # rm_xfg_list = rm_xfg_list[flipped == True].tolist()
    print(len(rm_xfg_list))
    rm_xfg_list.sort()
    # rm_xfg_list = statistic_cl_and_dt('deepwukong', 'CWE119_v1', 0.1)
    # rm_xfg_list = select_noise_from_cl_result(config.name, config.dataset.name, noise_rate)
    train(config, 'cl', noise_rate, rm_xfg_list=rm_xfg_list)

def reveal_ds_train(config, noise_rate):
    """
    @description  : keep sample count in training set same as training set after removing noisy samples found by cl 
    ---------
    @param  :
    -------
    @Returns  :
    -------
    """
    
    
    print_config(config)
    # ws_fliped_path = '/home/niexu/project/python/deepwukong/data/diff_train/CWE119/flipped/bigjson_flip.json'
    cl_result_path = join(config.res_folder, config.name ,'cl_result', config.dataset.name, str(int(noise_rate * 100)) + '_percent_res.json')
    result = read_json(cl_result_path)
    xfg_ids = np.array(result['xfg_id'])
    flipped = np.array(result['flip'])
    error_labels = result['error_label']
    flipped = flipped[error_labels]
    print(np.sum(flipped))
    rm_xfg_list = xfg_ids[error_labels].tolist()
    # rm_xfg_list = rm_xfg_list[flipped == True].tolist()
    print(len(rm_xfg_list))
    rm_xfg_list.sort()
    # rm_xfg_list = statistic_cl_and_dt('deepwukong', 'CWE119_v1', 0.1)
    # rm_xfg_list = select_noise_from_cl_result(config.name, config.dataset.name, noise_rate)
    train(config, 'ds', noise_rate, rm_count=len(rm_xfg_list))


def reveal_train(config, noise_rate:int=0, ckpt:str=None, mode:str='train'):
    print_config(config)
    if mode == 'train':
        
        train(config, noise_rate=noise_rate)
    elif mode == 'test':
        test(config, noise_rate, resume_from_checkpoint=ckpt)


if __name__ == "__main__":
   
    arg_parser = ArgumentParser()
    # arg_parser.add_argument("model", type=str)
    # arg_parser.add_argument("--dataset", type=str, default=None)
    arg_parser.add_argument("--offline", action="store_true")
    arg_parser.add_argument("--resume", type=str, default=None)
    args = arg_parser.parse_args()
    # config = get_config('Devign', 'reveal' ,log_offline=args.offline)
    # config.res_folder = 'res'
    # config.noise_set = 'all'
    # reveal_train(config, 0)
    # cwe_ids = ['CWE119','CWE020',  'CWE125', 'CWE190', 'CWE400', 'CWE787']
    cwe_ids = ['Devign']
    for cwe_id in cwe_ids:
        for method in ['reveal']:
            try:
                config = get_config(cwe_id, method, log_offline=args.offline)
                config.res_folder = 'res'
                config.noise_set = 'all'
                config.gpu = 0
                # reveal_train(config)
                # reveal_train(config, 0.1)
                # reveal_cl_train(config, 0.1)
                # reveal_ds_train(config, 0.1)
                # reveal_train(config, 0.2)
                # reveal_cl_train(config, 0.2)
                # reveal_ds_train(config, 0.2)
                reveal_train(config, 0.3)
                # reveal_cl_train(config, 0.3)
                # reveal_ds_train(config, 0.3)
                # reveal_ds_train(config, 0)
                # reveal_ds_train(config, 0.2)
                # reveal_ds_train(config, 0.3)
            except Exception as e:
                with open('log/train_error.log', 'a', encoding='utf8') as f:
                    f.write('{} {} {} \n'.format(cwe_id, method, e))
    # ckpt_before_cl = '/home/niexu/project/python/noise_reduce/ts_logger/reveal'Devign/version_19/checkpoints/epoch=06-val_loss=0.5148.ckpt'
    # ckpt_after_cl ='/home/niexu/project/python/noise_reduce/ts_logger/reveal/ReVeal/version_20/checkpoints/epoch=06-val_loss=1.5768.ckpt'
    # reveal_train(config)
    # reveal_cl_train(config=config, noise_rate=0)
    

  