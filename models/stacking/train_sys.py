from scipy.sparse import data
import torch
from utils.training import configure_optimizers_alon
from torch_geometric.data import DataLoader
from torch.utils.data import DataLoader as CL_Dataloader

from tqdm import tqdm
import torch.nn.functional as F
from utils.matrics import Statistic
from typing import Tuple, Dict, List, Union
import pprint as pp
# from models.sysevr.SYS_dataset import SYSDataset
# from models.sysevr.data_classes import SYSSample, SYSBatch

# def collate_wrapper(batch: List[SYSSample]) -> SYSBatch:
#     return SYSBatch(batch)
def get_dataloader(dataset, batch_size, s, shuffle_data=False):
        
        sub_dataset= dataset[s]
        # dataset = SYSDataset(sub_buffer_data, 50, False)
        
        dataloader = DataLoader(
            sub_dataset,
            batch_size=batch_size,
            shuffle=shuffle_data,
            num_workers=1,
            pin_memory=True
        )
        return dataloader
    
def general_epoch_end(outputs: List[Dict], group: str) -> Dict:
        with torch.no_grad():
            mean_loss = torch.stack([out["loss"]
                                     for out in outputs]).mean().item()
            logs = {f"{group}/loss": mean_loss}
            logs.update(
                Statistic.union_statistics([
                    out["statistic"] for out in outputs
                ]).calculate_metrics(group))
            pp.pprint(logs)
            
                
def train_sys(model, config, dataset):
    
    sz = len(dataset)
    train_slice = slice(sz//5, sz)
    test_slice = slice(0, sz //5)
    if torch.cuda.is_available():
            model.cuda(1)
    optimizers, schedulers = configure_optimizers_alon(config.hyper_parameters,
                                         model.parameters())
    optimizer, scheduler = optimizers[0], schedulers[0]
    
    train_dataloader = get_dataloader(dataset, config.hyper_parameters.batch_size, train_slice, True)
    test_dataloader = get_dataloader(dataset, config.hyper_parameters.test_batch_size, test_slice, False)
    #????????????
    model.train()
    for epoch in tqdm(range(config.hyper_parameters.n_epochs)):
        for batch in train_dataloader:
            device = torch.device("cuda:{}".format(1) if torch.cuda.is_available() else "cpu")
            batch.to(device)
            optimizer.zero_grad()
            output = model(batch)
            loss = F.nll_loss(output, batch.y, weight=None)
            loss.backward()
            optimizer.step()
        scheduler.step() 
    #????????????
    model.eval()
    outputs = []
    for batch in test_dataloader:
        device = torch.device("cuda:{}".format(1) if torch.cuda.is_available() else "cpu")
        batch.to(device)
        logits = model(batch)
        loss = F.nll_loss(logits, batch.y)
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
            outputs.append({"loss": loss, "statistic": statistic})
    general_epoch_end(outputs, "test")