# Inversion-articulatoire

Inversion-articulatoire is a Python library for training/test neural network models of articulatory reconstruction.\
the task : based on the acoustic signal guess 18 articulatory trajectories. \
It was created for learning the acoustic to articulatory mapping in a subject independant framework.\
For that we use data from 4 public datasets, that contains in all 19 speakers and more than 10 hours of acoustic and articulatory recordings.

It contains 2 main parts :
	- preprocessing that reads/cleans/preprocess/reorganize data
	- Feed a neural network with our data. Training  on some speakers and testing on a speaker

The library enables evaluating the generalization capacity of a set of (or one) corpus.
 To do so we train the model in three different configurations. 
 For each configuration we evaluate the model through cross validation, considering successively the speakers as the test speaker, and averaging the results.
 1) "speaker specific", we train and test on the same speaker. This configuration gives a topline of the results, and learn some characteristics of the speaker
 2) "speaker dependent", we train on all speakers (including the test speaker). 
 3) "speaker independant", we train on all speakers EXCEPT the test-speaker. We discover the test-speaker at the evaluation of the model. 
 By analyzing how the scores decrease from configuration 1 to 3 we conclude on the generalization capacity.

# Dependencies
numpy\
tensorflow (not used but tensorboard can be used)\
pytorch\
scipy\
librosa

# Requirements
The data from the 4 corpuses have to be in the correct folders.\
mocha : http://data.cstr.ed.ac.uk/mocha/\
MNGU0 : http://www.mngu0.org/\
usc : https://sail.usc.edu/span/usc-timit/\
Haskins : https://yale.app.box.com/s/cfn8hj2puveo65fq54rp1ml2mk7moj3h/folder/30415804819



# Contents

## Preprocessing :
1) main_preprocessing.py : launches the preprocessing for each of the corpuses (scripts preprocessing_namecorpus.py)
2) class_corpus.py : a speaker class useful that contains common attributes to all/some speakers and preprocessing functions that are shared as well.
3)preprocessing_namecorpus.py : contains function to preprocess all the speaker's data of the corpus.
4)tools_preprocessing.py : functions that are used in the preprocessing. 

## Training 
1) modele.py : the pytorch model, neural network bi-LSTM. Define the layers of the network, implementation of the smoothing convolutional layer, can evaluate on test set the model

2) train.py : the training process of our project. We can modulate some parameters of the learning. Especially we can chose on which corpus(es) we train our model, and the dependancy level to the test speaker.
3 main configurations : speaker specific, speaker dependent, speaker independent.  
Several parameters are optional and have default values. The required parameters are test_on, corpus_to_train_on, and config.

3) test.py : test the model (without any training) and saving some graph with the predicted & target articulatory trajectories.
experiments : ...

# Usage
1) Download the data 
Change some name folders to respect the following schema : in Inversion_articulatoire/Raw_data\
mocha :  for each speaker in ["fsew0", "msak0", "faet0", "ffes0", "maps0", "mjjn0", "falh0"] all the files are in Raw_data/mocha/speaker 
(same filename for same sentence, the extension indicates if its EMA, WAV, TRANS)\
MNGU0 : 3 folders in Raw_data/MNGU0 : ema, phone_labels and wav. In each folder all the sentences\
usc : for each speaker in ["F1","F5","M1","M3"] a folder  Raw_data/usc/speaker, then 3 folders : wav, mat, trans\
Haskins : for each speaker in ["F01", "F02", "F03", "F04", "M01", "M02", "M03", "M04"] a folder Raw_data/usc/speaker, then 3 folders : data, TextGrids, wav 

2) Preprocessing 
The argument is for the max number of files you want to preprocess, to preprocess ALL files put 0. This argument is useful for test.
To preprocess 50 files for each speaker : be in the folder "Preprocessing" and type the following in the command line 
```bash
python main_preprocessing.py 50 
```
The preprocessing of all the data takes about 6 hours.

3) Training 
The required parameters of the train function are those concerning the training/test set :\
- the test-speaker : the speaker on which the model will be evaluated),\
-  the corpus we want to train on  : the list the corpus that will be in training set
- the configuration : see above the description of the 3 configuration "indep","dep" or "spec".
The optional parameters are the parameters of the models itself.
To train on all the speakers except F01 of the Haskins corpus with the default parameters : be in the folder "Training" and type the following in the commandline
```bash
python train.py "F01" ["Haskins"] "indep"  
```

The model name contains information about the training/testing set , and some parameters for which we did experiments 
The model weights are saved in "Training/saved_models". The name of the above model would be "F01_spec_loss_90_filter_fix_bn_False_0"
If we train twice with the same parameters, a new model will be created with an increment in the suffix of the namefile.
An exception is when the last model didn't end training, in that case the training continue for the model [no increment in the suffix of the namefile].
The results of the model (ie RMSE and PEARSON for the test set for each articulator) are saved adding a new row to a csv file "results_models". 


or 3) Experiments
Training only train excluding ONE speaker. For more significant results, one wants to average results obtained by cross validation excluding all the speakers one by one.
The script Experiments enables to perform this cross_validation and save the result of the cross validation.
Several experiments to evaluate influence of parameters (filter type, alpha, batch normalization) , and results are saved in a csv file "experiment_results_parameter".
An experiment enables to evaluate the capacity of generalization of a set of corpuses, and results are saved in a csv file "experiment_results_config".
To perform this last experiment : be in the folder "Training" and type in the command line :
 
```bash
python experiment.py ["Haskins"] "config"  
```
Haskins means that we learn on haskins , config means that we do this cross validation on each configuration of spec/dep/indep.
In the results csv file there is one row per configuration.

4) Perform inversion
Supposed you have acoustic data (.wav) and you want to get the articulatory trajectories. 
Chose on model that was already trained.

# Perform articulatory predictions
If you have wav files and want to predict the associated articulatory predictions : 
Put the wav files in "Predictions_arti/my_wav_files_for_inversion".
be in the folder "Predictions_arti" and type in the command line : 
```bash
python predictions_arti.py  F01_spec_loss_0_filter_fix_bn_False_0
```
```bash
python predictions_arti.py  F01_spec_loss_0_filter_fix_bn_False_0 --already_prepro True
```
If you  already did the preprocessing and want to test with another model :
 
The first argument is the  name of the model you want to use for the prediction
The second argument --already_prepro is a boolean that is by default False, set it to true if you dont want to do the preprocess again.
The preprocessing will calculate the mfcc features corresponding to the wav files and save it in "Predictions_arti/my_mfcc_files_for_inversion"
The predictions of the articulatory trajectories are as nparray in "Predictions_arti/my_articulatory_prediction" with the same name as the wav (and mfcc) files.
Warning : if you perform several predictions wuth different models the previous predictions will be overwritten, so save it elsewhere.
Warning : usually the mfcc features are normalized at a speaker level when enough data for this speaker is available. The preprocessing doesn't normalize the mfcc coeff.


# Results 
Some models already trained are in saved_models_examples.

For example the following one  "fsew0_spec_loss_0_filter_fix_bn_False_0.txt", is a speaker specific model (train and test on fsew0), with loss rmse, 
with a filter inside the NN with fixed weights, without batch normalization.

To test this models be in the folder "Training" and type this in the command line :
```bash
python test.py "fsew0" "fsew0_spec_loss_0_filter_fix_bn_False_0"
```
"fsew0" indicates the test speaker.  fsew0_spec_loss_0_filter_fix_bn_False_0 is the name of the model that should be in "Training/saved_models" (be careful to change the name of saved_models_examples).
The script will save in Training/images_prediction some graph. For one random test sentence it will plot and save the target and predicted trajectories for every articulators. 
The script will print the rmse and pearson result  per articulator averaged over the test set. It also adds rows in the csv "results_models_test" with the rmse and pearson per articulator.


To compare to the state of the art, speaker specific results on fsew0 and msak0 :

model , 
the weights 


| articulator |     tt_x    |     tt_y    |     td_x    |     td_y    |     tb_x    |     li_y    |     ll_x    |     ll_y    |     ttcl    |     v_x     |     v_y     |
|:-----------:|:-----------:|:-----------:|:-----------:|:-----------:|:-----------:|:-----------:|:-----------:|:-----------:|:-----------:|:-----------:|:-----------:|
|     rmse    |       0,74  |       0,86  |       1,75  |       0,43  |       1,74  |       1,67  |       0,74  |       1,03  |       0,05  |       1,71  |       1,53  |
|   pearson   |       0,75  |       0,84  |       0,87  |       0,69  |       0,86  |       0,85  |       0,69  |       0,80  |       0,86  |       0,89  |       0,92  |



Some plot of trajectories 

First use of the corpus Haskins that provides better results, and very good on generalization 




