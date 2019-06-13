### ETUDIER ARTI 6

from class_network import my_bilstm

import sys
import torch
import os
import sys
from sklearn.model_selection import train_test_split

from pytorchtools import EarlyStopping
import time

from os.path import dirname
import numpy as np
from scipy import signal
import matplotlib.pyplot as plt
import scipy
from os import listdir


print(sys.argv)

def train_model(train_on=["fsew0"],test_on=["msak0"],n_epochs=1,delta_test=50,patience=5,lr=0.09,output_dim=12):
  # cuda_avail = torch.cuda.is_available()
   # print("cuda ?",cuda_avail)

    root_folder = os.path.dirname(os.getcwd())
    fileset_path = os.path.join(root_folder, "Donnees_pretraitees","fileset")

    train_on=str(train_on[1:-1])
    test_on  =str(test_on[1:-1])
    train_on = train_on.split(",")
    test_on=test_on.split(",")

    name_file="train_" + "_".join(train_on) + "_test_" + "_".join(test_on)
    folder_weights= os.path.join("saved_models", name_file)

    X_train, Y_train =[],[]
    for speaker in train_on :
        X_train.extend( np.load(os.path.join(fileset_path,"X_train_"+speaker+".npy")))
        Y_train.extend(np.load(os.path.join(fileset_path, "Y_train_"+speaker + ".npy")))
        if speaker not in test_on :#then we can train on the test part of this speaker
            X_train.extend( np.load(os.path.join(fileset_path,"X_test_"+speaker+".npy")))
            Y_train.extend(np.load(os.path.join(fileset_path, "Y_test_" + speaker + ".npy")))

    X_test,Y_test = [],[]
    for speaker in test_on :
        X_test.extend(np.load(os.path.join(fileset_path, "X_test_" + speaker + ".npy")))
        Y_test.extend(np.load(os.path.join(fileset_path, "Y_test_" + speaker + ".npy")))
        if speaker not in train_on:  # then we can test on the train part of this speaker
            X_test.extend(np.load(os.path.join(fileset_path, "X_train_" + speaker + ".npy")))
            Y_test.extend(np.load(os.path.join(fileset_path, "Y_train_" + speaker + ".npy")))

    if output_dim != len(Y_train[0][0]): #besoin denlever quelques features , les premieres
        print('we remove some features and Y goes from size {} to {}'.format(len(Y_train[0][0]), output_dim))
        Y_train = np.array([Y_train[i][:, :output_dim] for i in range(len(Y_train))])
        Y_test = np.array([Y_test[i][:, :output_dim] for i in range(len(Y_test))])

    pourcent_valid=0.05
    hidden_dim = 300
    input_dim = 429
    batch_size = 10
    X_train, X_valid, Y_train, Y_valid = train_test_split(X_train, Y_train, test_size=pourcent_valid, random_state=1)
    X_train, X_valid, Y_train, Y_valid = np.array(X_train),np.array(X_valid),np.array(Y_train),np.array(Y_valid),
   # X_train = X_train[0:100]
   # Y_train = Y_train[0:100]
    early_stopping = EarlyStopping(name_file,patience=patience, verbose=True)


    model = my_bilstm(hidden_dim=hidden_dim,input_dim=input_dim,name_file =name_file, output_dim=output_dim,batch_size=batch_size)
    model = model.double()

    try :
        model.load_state_dict(torch.load(os.path.join(folder_weights,name_file+".txt")))
        model.all_training_loss=[]


        #try :

        #except:
         #   print("pbm pour charger les anciennes loss")
    except :
       print('first time, intialisation...')



    previous_epoch = 0

    try :
        previous_losses = np.load(os.path.join(folder_weights, "all_losses.npy"))
        a,b,c = previous_losses[0, :],previous_losses[1, :],previous_losses[2, :]



        if len(a)==len(b)==len(c):
            model.all_training_loss = list(a)
            model.all_validation_loss_loss = list(b)
            model.all_test_loss = list(c)
            previous_epoch  = len(a)
    except :
        print("seems first time no previous loss")


    print("previous epoch  :", previous_epoch)
    #if cuda_avail:
     #   model = model.cuda()

    criterion  = torch.nn.MSELoss(reduction='sum')
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)

    plt.ioff()
    print("number of epochs : ", n_epochs)

    for epoch in range(n_epochs):
        indices = np.random.choice(len(X_train), batch_size, replace=False)
        x, y = X_train[indices], Y_train[indices]
        x,y = model.prepare_batch(x,y)

      #  if cuda_avail:
      #      x = x.cuda()
       #     y = y.cuda()
        before = model.lowpass.weight.data
        y_pred= model(x).double()
        y = y.double()
        optimizer.zero_grad()
        loss = criterion(y_pred,y)
       # print("cutoff",model.cutoff)
       # print(model.cutoff.grad)
        loss.backward()
        optimizer.step()
        after = model.lowpass.weight.data
        print("same?",after==before)
        model.all_training_loss.append(loss.item())
        if epoch%10 ==0:
            print("---------epoch---",epoch)
        if epoch%delta_test ==0:  #toutes les 20 epochs on évalue le modèle sur validation et on sauvegarde le modele si le score est meilleur
            mean_loss = model.evaluate(X_valid, Y_valid,criterion)
            model.all_validation_loss += [mean_loss] * (epoch+previous_epoch - len(model.all_validation_loss))

            loss_test = model.evaluate_on_test(criterion,X_test = X_test,Y_test = Y_test,to_plot=False)
            model.all_test_loss += [mean_loss] * (epoch+previous_epoch - len(model.all_test_loss))

            print("\n ---------- epoch" + str(epoch) + " ---------")
            early_stopping.epoch = previous_epoch+epoch
            early_stopping(mean_loss, model)
            print("train loss ", loss.item())
            print("valid loss ", mean_loss)
            print("test loss ",loss_test)

        if early_stopping.early_stop:
            print("Early stopping")
            break

    model.load_state_dict(torch.load(os.path.join(folder_weights,name_file+'.pt')))
    torch.save(model.state_dict(), os.path.join( folder_weights,name_file+".txt"))
    model.evaluate_on_test(criterion,X_test = X_test,Y_test = Y_test,to_plot=False,verbose=True)


    length_expected = len(model.all_training_loss)
    print("lenght exp",length_expected)
    model.all_validation_loss += [model.all_validation_loss[-1]] * (length_expected - len(model.all_validation_loss))
    model.all_test_loss += [model.all_test_loss[-1]] * (length_expected - len(model.all_test_loss))
    model.all_training_loss = np.array(model.all_training_loss).reshape(1,length_expected)
    model.all_validation_loss = np.array(model.all_validation_loss).reshape(1,length_expected)
    model.all_test_loss = np.array(model.all_test_loss).reshape((1,length_expected))
    all_losses = np.concatenate(
        ( np.array(model.all_training_loss),
        np.array(model.all_validation_loss),
      np.array(model.all_test_loss) )
          ,axis=0)

    np.save(os.path.join(folder_weights,"all_losses.npy"),all_losses)
if __name__=='__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Train and save a model.')
    parser.add_argument('train_on', metavar='train_on', type=list,
                        help='')
    parser.add_argument('test_on', metavar='test_on', type=list,
                        help='')

    #
    parser.add_argument('n_epochs', metavar='n_epochs', type=int,
                        help='max number of epochs to train the model')
#    parser.add_argument('speaker', metavar='speaker', type=str,
 #                       help='corpus on which train model : fsew or msak or MNGU0 or both')
    parser.add_argument('delta_test', metavar='delta_test', type=int,
                        help='interval between two validation evaluation')
    parser.add_argument('patience', metavar='patience', type=int,
                        help='number of iterations in a row with decreasing validation score before stopping the train ')
    parser.add_argument('lr', metavar='lr', type=str,
                        help='learning rate of Adam optimizer ')

    parser.add_argument('output_dim', metavar='output_dim', type=int,
                        help='simple  : 12, +lipaperture : 13, +velu : 15 -attention il faut avoir appris sur mngu0')

    args = parser.parse_args()

    train_on =  sys.argv[1]
    test_on = sys.argv[2]
    n_epochs = int( sys.argv[3] )
    delta_test = int(sys.argv[4])
    patience = int(sys.argv[5])
    lr = float(sys.argv[6])
    output_dim = int(sys.argv[7])
    train_model(train_on = train_on,test_on = test_on ,n_epochs=n_epochs,delta_test=delta_test,patience=patience,lr = lr,output_dim=output_dim)