import torch
import os
import sys
from sklearn.model_selection import train_test_split
from scipy.signal import butter, lfilter, freqz
import time
import math
from scipy.stats import pearsonr
from os.path import dirname
import numpy as np
from scipy import signal
import matplotlib.pyplot as plt
import scipy
from torch.autograd import Variable

try :
    from Apprentissage import utils
except :  import utils


class my_bilstm(torch.nn.Module):
    def __init__(self, hidden_dim, input_dim, output_dim, batch_size,name_file, sampling_rate=200,
                 window=5, cutoff=20):
        root_folder = os.path.dirname(os.getcwd())
        super(my_bilstm, self).__init__()
        self.input_dim = input_dim
        self.output_dim = output_dim
        self.hidden_dim = hidden_dim
        self.first_layer = torch.nn.Linear(input_dim, hidden_dim)
        self.second_layer = torch.nn.Linear(hidden_dim, hidden_dim)
        self.last_layer = torch.nn.Linear(output_dim,output_dim)
        self.lstm_layer = torch.nn.LSTM(input_size=hidden_dim,
                                        hidden_size=hidden_dim, num_layers=1,
                                        bidirectional=True)
        self.readout_layer = torch.nn.Linear(hidden_dim *2, output_dim)
        self.batch_size = batch_size
        self.sigmoid = torch.nn.Sigmoid()
        self.softmax = torch.nn.Softmax(dim=output_dim)
        self.tanh = torch.nn.Tanh()
        self.sampling_rate = sampling_rate
        self.window = window
        self.cutoff = cutoff
        self.min_valid_error = 100000
        self.all_training_loss = []
        self.all_validation_loss = []
        #self.std = np.load(os.path.join(root_folder,"Traitement","std_ema_"+speaker+".npy"))
        self.name_file = name_file
        self.lowpass = None
        self.init_filter_layer()

    def prepare_batch(self, x, y):
        max_lenght = np.max([len(phrase) for phrase in x])
        new_x = torch.zeros((self.batch_size, max_lenght, self.input_dim), dtype=torch.double)
        new_y = torch.zeros((self.batch_size, max_lenght, self.output_dim), dtype=torch.double)

        for j in range(self.batch_size):
            zeropad = torch.nn.ZeroPad2d((0, 0, 0, max_lenght - len(x[j])))
            new_x[j] = zeropad(torch.from_numpy(x[j])).double()
            new_y[j] = zeropad(torch.from_numpy(y[j])).double()
        x = new_x.view((self.batch_size, max_lenght, self.input_dim))
        y = new_y.view((self.batch_size, max_lenght, self.output_dim))
        return x, y

    def forward(self, x):
        dense_out = torch.nn.functional.relu(self.first_layer(x))
        dense_out_2 = torch.nn.functional.relu(self.second_layer(dense_out))
        lstm_out, hidden_dim = self.lstm_layer(dense_out_2)
        lstm_out = torch.nn.functional.relu(lstm_out)
        y_pred = self.readout_layer(lstm_out)
        y_pred_smoothed = self.filter_layer(y_pred)
        return y_pred_smoothed

    def get_filter_weights(self):
        # print(cutoff)
        cutoff = torch.tensor(self.cutoff, dtype=torch.float64).view(1, 1)
        fc = torch.div(cutoff,self.sampling_rate)  # Cutoff frequency as a fraction of the sampling rate (in (0, 0.5)).
        if fc > 0.5:
            raise Exception("La frequence de coupure doit etre au moins deux fois la frequence dechantillonnage")
        b = 0.3  # Transition band, as a fraction of the sampling rate (in (0, 0.5)).
        N = int(np.ceil((4 / b)))  # le window
        if not N % 2:
            N += 1  # Make sure that N is odd.
        n = torch.from_numpy(np.arange(N))  # int of [0,N]
        alpha = torch.mul(fc,torch.tensor(2*(n-(N-1)/2)).double())
        h= torch.div(torch.sin(alpha),alpha)
        h[torch.isnan(h)] = 1
#        h = np.sinc(2 * fc * (n - (N - 1) / 2))  # Compute sinc filter.
        beta = torch.tensor(2*math.pi*n/(N-1)).double()
        w = 0.5 * (1 - torch.cos(beta) ) # Compute hanning window.
        h = torch.mul(h, w ) # Multiply sinc filter with window.
        h = torch.div(h , torch.sum(h))
        h.require_grads=True
        self.cutoff = Variable(cutoff, requires_grad=True)
        self.cutoff.require_grads = True
        self.cutoff.retain_grad()
        #  h = torch.cat([h]*self.output_dim,0)
        return h



    def init_filter_layer(self):
        # print("1",self.cutoff)

        # self.cutoff = torch.nn.parameter.Parameter(torch.Tensor(self.cutoff))

        # self.cutoff.requires_grad = True
        window_size = 5
        C_in = 1
        # stride=1
        padding = 5 # int(0.5*((C_in-1)*stride-C_in+window_size))+23
        lowpass = torch.nn.Conv1d(C_in, self.output_dim, window_size, stride=1, padding=padding,
                                  bias=False)
        weight_init = self.get_filter_weights()
        lowpass.weight.data =weight_init
        #lowpass_init = lowpass_init.view((1, 1, -1))
        #lowpass.weight = torch.nn.Parameter(lowpass_init)
        lowpass = lowpass.double()
        self.lowpass = lowpass


    def filter_layer(self, y):
        B = len(y) # batch size
        L = len(y[0])
        #     y= y.view(self.batch_size,self.output_dim,L)
        y = y.double()
        y_smoothed = torch.zeros(B, L, self.output_dim)
        for i in range(self.output_dim):
            traj_arti = y[:, :, i].view(B, 1, L)
            traj_arti_smoothed = self.lowpass(traj_arti)  # prend que une seule dimension
            difference = int((L-traj_arti_smoothed.shape[2])/ 2)

            if difference>0: #si la traj smoothed est plus petite que L on rajoute le meme dernier élément
                traj_arti_smoothed = torch.nn.ReplicationPad1d(difference)(traj_arti_smoothed)

            traj_arti_smoothed = traj_arti_smoothed.view(B, L)
            y_smoothed[:, :, i] = traj_arti_smoothed


           # x = traj_arti.detach().numpy()
           # x_s = traj_arti_smoothed.detach().numpy()
           # plt.plot(x[0,0,:])
           # plt.plot(x_s[0,:])
           # plt.legend(['traj','traj smootehd'])
           # plt.show()
        return y_smoothed


    def plot_results(self, y, y_pred):
        plt.figure()
        for j in range(12):
            plt.figure()
            #print("10 first :",y_pred[0:10,j])
            plt.plot(y_pred[:, j])
            plt.plot(y[:, j])
            plt.title("prediction_test_{0}_arti{1}.png".format(self.name_file, str(j)))
            plt.legend(["prediction", "vraie"])
            save_pics_path = os.path.join(
                "images_predictions\\{0}_arti{1}.png".format(self.name_file,str(j)))
            plt.savefig(save_pics_path)
            plt.close('all')

    def evaluate(self, x_valid, y_valid,epoch,criterion):
        x_temp, y_temp = self.prepare_batch(x_valid, y_valid) #add zero to have correct size
        y_pred = self(x_temp).double()
        y_temp = y_temp.double()
        loss = criterion(y_pred, y_temp).item()
        y_toplot = y_temp.detach().numpy()
        y_toplot_2 = y_pred.detach().numpy()
        i = np.random.choice(len(y_toplot_2))
    #    self.plot_results(y_toplot[i],y_toplot_2[i])
        return loss

    def evaluate_on_test(self,X_test=None,Y_test=None,to_plot=False):
        fileset_path = os.path.join(os.path.dirname(os.getcwd()), "Donnees_pretraitees","fileset")
         #Racine de l’erreur quadratique moyenne de prédiction des modèles
        all_diff = np.zeros((1, self.output_dim))
        print('MODEL OK, NOW LETS SEE RESULTS ON TEST SET')
        indices_to_plot=[]
        if to_plot == True :
            print("you chose to plot")
            indices_to_plot = np.random.choice(len(X_test), 2, replace=False)
        all_corr=[]
        for i in range(len(X_test)):
                x = torch.from_numpy(X_test[i])
                x = x.view(1, len(x), self.input_dim) #one sample of X (mfcc) : normalized
                y = Y_test[i].reshape((len(x[0]), self.output_dim))  #one sample of y (ema) : normalized
                y_pred = self(x)
                y_pred = y_pred.reshape((len(x[0]), self.output_dim)).detach().numpy()
                if i in indices_to_plot:
                    self.plot_results(y, y_pred)

                rmse = np.sqrt(np.mean(np.square(y - y_pred), axis=0))
                rmse = np.reshape(rmse, (1, self.output_dim))
                all_diff = np.concatenate((all_diff, rmse))
        all_diff = all_diff[1:] #remove first row of zeros #all the errors per arti and per sample
        print("rmse final : ", np.mean(all_diff))
        corr_final = np

        rmse_per_arti_mean = np.mean(all_diff,axis=0)
        rmse_per_arti_std = np.std(all_diff,axis=0)

        print("rmse mean per arti : \n", rmse_per_arti_mean)
      #  print("rmse std per arti : \n", rmse_per_arti_std)