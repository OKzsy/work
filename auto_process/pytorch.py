from __future__ import print_function
import argparse
import os
import pickle
import requests
import numpy as np
from tensorboardX import SummaryWriter
import torch
import torch.distributed as dist
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.utils.data import DataLoader
import time

WORLD_SIZE = int(os.environ.get('WORLD_SIZE', 1))

def get_data():
    file = r"/mnt/nydsjsmb/kubelfow/train_pre/data.pickle"
    fileObject = open(file, 'rb')
    modelInput = pickle.load(fileObject)
    fileObject.close()
    return modelInput

#####mydataloader
class Mydataset1(torch.utils.data.Dataset):
    def __init__(self,in_file):
        # print(in_file1)
        self.xy = in_file
        # self1.len = xy.shape[0]
        self.train_x = torch.from_numpy(self.xy[:, :-1]/10000)
        self.train_y = torch.from_numpy(self.xy[:, -1])

    def __getitem__(self, index):
        return self.train_x[index], self.train_y[index]
    def __len__(self): # 返回文件数据的数目
        return len(self.xy)

class Mydataset2(torch.utils.data.Dataset):
    def __init__(self2,in_file):
    # 读取csv文件中的数据
    #     print(in_file2)
        self2.xy = in_file
        # self2.len = xy.shape[0]
        self2.val_x = torch.from_numpy(self2.xy[:, :-1]/10000)
        self2.val_y = torch.from_numpy(self2.xy[:, -1])

    def __getitem__(self2, index):
        return self2.val_x[index], self2.val_y[index]

    def __len__(self2):
        return len(self2.xy)    
 
    

class Net(nn.Module):
    def __init__(self,args):
        super(Net,self).__init__()
        self.conv1 = nn.Sequential(nn.Conv2d(channels,100,2,stride=1,padding=1),
                                   nn.ReLU(),
                                   nn.MaxPool2d(2,2))
        self.conv2 = nn.Sequential(nn.Conv2d(100,100,2,stride=1,padding=1),
                                   nn.ReLU(),
                                   nn.MaxPool2d(2,2))
        self.conv3 = nn.Sequential(nn.Conv2d(100,100,2,stride=1),
                                   nn.ReLU())
        self.fc = nn.Sequential(nn.Linear(100,out_features=args.H_dense),
                                 nn.ReLU(),
                                 nn.Linear(in_features=args.H_dense,out_features=2))
    def forward(self,x):
        x = self.conv1(x)
        x = self.conv2(x)
        x = self.conv3(x)
        (_, C, H, W) = x.data.size()
        x = x.view(-1, C * H * W)
        x = self.fc(x)
        return x
    
def train(args, model, device, train_loader, optimizer, epoch, writer,criterion):
    model.train()
    for batch_idx, (data, target) in enumerate(train_loader):
        data = data.view(data.shape[0], channels, patch_size, patch_size)
        data, target = data.to(device), target.to(device)
        from torch.autograd import Variable
        data = Variable(data.float())
        target = Variable(target.long())

        output = model(data)
        loss = criterion(output, target)
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        if batch_idx % args.log_interval == 0:
            print('Train Epoch: {} [{}/{} ({:.0f}%)]\tloss={:.4f}'.format(
                epoch, batch_idx * len(data), len(train_loader.dataset),
                       100. * batch_idx / len(train_loader), loss.item()))
            niter = epoch * len(train_loader) + batch_idx
            writer.add_scalar('loss', loss.item(), niter)

def test(args, model, device, test_loader, writer, epoch,criterion):
    model.eval()
    test_loss = 0
    correct = 0
    with torch.no_grad():
        for data, target in test_loader:
            data = data.view(data.shape[0], channels, patch_size, patch_size)
            data, target = data.to(device), target.to(device)
            from torch.autograd import Variable
            data = Variable(data.float())
            target = Variable(target.long())
            output = model(data)
            test_loss += criterion(output, target).sum().item()  # sum up batch loss
            pred = output.max(1, keepdim=True)[1]  # get the index of the max log-probability
            correct += pred.eq(target.view_as(pred)).sum().item()

        test_loss /= len(test_loader.dataset)
        print('\naccuracy={:.4f}\n'.format(float(correct) / len(test_loader.dataset)))
        writer.add_scalar('accuracy', float(correct) / len(test_loader.dataset), epoch)


def should_distribute():
    return dist.is_available() and WORLD_SIZE > 1


def is_distributed():
    return dist.is_available() and dist.is_initialized()



def main():
    # Training settings
    parser = argparse.ArgumentParser(description='PyTorch Cnn model')
    parser.add_argument('--batch-size', type=int, default=128, metavar='N',
                        help='input batch size for training (default: 64)')
    parser.add_argument('--test-batch-size', type=int, default=1000, metavar='N',
                        help='input batch size for testing (default: 1000)')
    parser.add_argument('--epochs', type=int, default=5, metavar='N',
                        help='number of epochs to train (default: 10)')
    parser.add_argument('--lr', type=float, default=0.0003, metavar='LR',
                        help='learning rate (default: 0.003)')
    # parser.add_argument('--momentum', type=float, default=0.5, metavar='M',
    #                     help='SGD momentum (default: 0.5)')
    parser.add_argument('--no-cuda', action='store_true', default=False,
                        help='disables CUDA training')
    parser.add_argument('--seed', type=int, default=1, metavar='S',
                        help='random seed (default: 1)')
    parser.add_argument('--log-interval', type=int, default=10, metavar='N',
                        help='how many batches to wait before logging training status')
    parser.add_argument('--save-model', action='store_true', default=True,
                        help='For Saving the current Model')
    # parser.add_argument('--dir', default='logs', metavar='L',
    #                     help='directory where summary logs are stored')
    parser.add_argument('--H_dense',default=200,help='hidden size in the cnn model')
    if dist.is_available():
        parser.add_argument('--backend', type=str, help='Distributed backend',
                            choices=[dist.Backend.GLOO, dist.Backend.NCCL, dist.Backend.MPI],
                            default=dist.Backend.GLOO)
    args = parser.parse_args()
    use_cuda = not args.no_cuda and torch.cuda.is_available()
    if use_cuda:
        print('Using CUDA')

    writer = SummaryWriter(os.path.join(out_path,'logs'))

    torch.manual_seed(args.seed)

    device = torch.device("cuda" if use_cuda else "cpu")

    if should_distribute():
        print('Using distributed PyTorch with {} backend'.format(args.backend))
        dist.init_process_group(backend=args.backend)

    kwargs = {'num_workers': 2, 'pin_memory': True} if use_cuda else {}

    from sklearn.model_selection import train_test_split
    data = get_data()
    train_data, test_data = train_test_split(data, test_size=test_size, random_state=0)
    train_dataset = Mydataset1(train_data)
    test_dataset = Mydataset2(test_data)
    train_loader = DataLoader(train_dataset,
                              batch_size=args.batch_size,
                              shuffle=True,
                              **kwargs)
    test_loader = DataLoader(test_dataset,
                             batch_size=args.test_batch_size,
                             shuffle=False,
                             **kwargs)

    model = Net(args).to(device)

    if is_distributed():
        Distributor = nn.parallel.DistributedDataParallel if use_cuda \
            else nn.parallel.DistributedDataParallelCPU
        model = Distributor(model)

    optimizer = optim.Adam(model.parameters(), lr=args.lr)
    criterion = nn.CrossEntropyLoss()
    for epoch in range(1, args.epochs + 1):
        train(args, model, device, train_loader, optimizer, epoch, writer,criterion)
        test(args, model, device, test_loader, writer, epoch,criterion)

    if (args.save_model):
        torch.save(model,out_path + '/'+ 'best_model.pkl')
        
if __name__ == '__main__':
    channels = 4
    flag_dict = {"yancao": 0, "qita": 1}
    sample_dir = r"/mnt/nydsjsmb/kubelfow/sample"
    sample_tiffs = [os.path.join(sample_dir, f) for f in os.listdir(sample_dir) if f.endswith(".tif")]
    patch_size = 7
    test_size = 0.2
    out_path = r"/mnt/nydsjsmb/kubelfow/model"

    main()