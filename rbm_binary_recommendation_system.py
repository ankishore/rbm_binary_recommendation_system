# Import libraries
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.parallel
import torch.optim as optim
import torch.utils.data
from torch.autograd import Variable

# Import dataset
movies = pd.read_csv('https://raw.githubusercontent.com/ankishore/rbm_binary_recommendation_system/main/movies.dat',
                     sep = '::', header = None, engine = 'python', encoding = 'latin-1')
users = pd.read_csv('https://raw.githubusercontent.com/ankishore/rbm_binary_recommendation_system/main/users.dat',
                     sep = '::', header = None, engine = 'python', encoding = 'latin-1')
ratings = pd.read_csv('https://raw.githubusercontent.com/ankishore/rbm_binary_recommendation_system/main/ratings.dat',
                     sep = '::', header = None, engine = 'python', encoding = 'latin-1')

# Preparing training and test dataset
training_set = pd.read_csv('https://raw.githubusercontent.com/ankishore/rbm_binary_recommendation_system/main/u1.base',
                           delimiter = '\t')
training_set = np.array(training_set, dtype = 'int')
test_set = pd.read_csv('https://raw.githubusercontent.com/ankishore/rbm_binary_recommendation_system/main/u1.test',
                       delimiter = '\t')
test_set = np.array(test_set, dtype = 'int')

# Getting number of users and movies
nb_users = int(max(max(training_set[:, 0]), max(test_set[:,0])))
nb_movies = int(max(max(training_set[:, 1]), max(test_set[:,1])))

# Converting data into an array with users in rows and movies in columns
def convert(data):
    new_data = []

    for id_users in range(1, nb_users + 1):
        id_movies = data[:, 1][data[:, 0] == id_users]
        id_ratings = data[:, 2][data[:, 0] == id_users]
        ratings = np.zeros(nb_movies)
        ratings[id_movies - 1] = id_ratings
        new_data.append(list(ratings))
    
    return new_data

training_set = convert(training_set)
test_set = convert(test_set)

# Converting data into torch tensors
training_set = torch.FloatTensor(training_set)
test_set = torch.FloatTensor(test_set)

# Converting the ratings into binary i.e 1 for like, 0 for dislike
training_set[training_set == 0] = -1 # No rating available
training_set[training_set == 1] = 0 # dislike
training_set[training_set == 2] = 0 # dislike
training_set[training_set >= 3] = 1 # like
test_set[test_set == 0] = -1 # No rating available
test_set[test_set == 1] = 0 # dislike
test_set[test_set == 2] = 0 # dislike
test_set[test_set >= 3] = 1 # like

# Creating the architecture of neural network
class RBM():
    def __init__(self, nv, nh):
        self.W = torch.randn(nh, nv) # Init weights
        self.a = torch.randn(1, nh) # Init bias for hidden nodes
        self.b = torch.randn(1, nv) # Init bias for visible nodes

    def sample_h(self, x):
        wx = torch.mm(x, self.W.t()) # Add all weights
        activation = wx + self.a.expand_as(wx) # Add bias
        p_h_given_v = torch.sigmoid(activation)
        return p_h_given_v, torch.bernoulli(p_h_given_v)

    def sample_v(self, y):
        wy = torch.mm(y, self.W) # Add all weights
        activation = wy + self.b.expand_as(wy) # Add bias
        p_v_given_h = torch.sigmoid(activation)
        return p_v_given_h, torch.bernoulli(p_v_given_h)

    # k-step contrastive divergence
    def train(self, v0, vk, ph0, phk):
        self.W += (torch.mm(v0.t(), ph0) - torch.mm(vk.t(), phk)).t()
        self.b += torch.sum((v0 - vk), 0)
        self.a += torch.sum((ph0 - phk), 0)
    
nv = len(training_set[0])
nh = 100 # User selected number of features we want to sample
batch_size = 100
rbm = RBM(nv, nh)

# Training the RBM
nb_epoch = 10
for epoch in range(1, nb_epoch + 1):
    train_loss = 0
    s = 0.
    for id_user in range(0, nb_users - batch_size, batch_size):
        # k step constrastive divengence
        vk = training_set[id_user : id_user + batch_size]
        v0 = training_set[id_user : id_user + batch_size]
        ph0,_ = rbm.sample_h(v0)
        
        # User defined 10 k steps
        for k in range(10):
            _,hk = rbm.sample_h(vk)
            _,vk = rbm.sample_v(hk)
            vk[v0 < 0] = v0[v0 < 0]

        phk,_ = rbm.sample_h(vk)

        rbm.train(v0, vk, ph0, phk)
        
        # Calculate training loss for every batch
        train_loss += torch.mean(torch.abs(v0[v0 >= 0] - vk[v0 >= 0]))
        s += 1
    
    print('epoch: ' + str(epoch) + ' loss: ' + str(train_loss / s))
    
# Testing RBM
test_loss = 0
s = 0.
for id_user in range(nb_users):
    v = training_set[id_user : id_user + 1]
    vt = test_set[id_user : id_user + 1]
    if len(vt[vt >= 0]) > 0:
        _,h = rbm.sample_h(v)
        _,v = rbm.sample_v(h)
        
        test_loss += torch.mean(torch.abs(vt[vt >= 0] - v[vt >= 0]))
        s += 1.
print('test loss: ' + str(test_loss / s))