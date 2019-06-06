""" Lecture des données EMA pour le corpus MNGU0. On ne conserve que les données concernant les articulateurs indiqués
 dans articulators cest a dire 6 articulateurs en 2Dimensions.
 on ajoute une colonne correspondant à l'ouverture des lèvres, cest donc la 13ème colonne
 on normalise on soustrayant pour chaque articulateur sa position moyenne et en divisant par sa std
"""
import os
import time
from os.path import dirname
import numpy as np
import scipy.signal
import matplotlib.pyplot as plt
import scipy.interpolate
from Traitement.add_dynamic_features import get_delta_features
import librosa

def traitement_general_mngu0(N=all):

    root_path = dirname(dirname(os.path.realpath(__file__)))
    path_files_annotation = os.path.join(root_path, "Donnees_brutes\Donnees_breakfast\MNGU0\phone_labels")

    sampling_rate_ema = 200

    #articulators in the same order that those of MOCHA
    articulators = [
        'T1_py','T1_pz','T3_py','T3_pz','T2_py','T2_pz',
        'jaw_py','jaw_pz','upperlip_py','upperlip_pz',
        'lowerlip_py','lowerlip_pz']

    n_col_ema = len(articulators)+1 #lip aperture
    path_ema_files = os.path.join(root_path, "Donnees_brutes\Donnees_breakfast\MNGU0\ema")
    EMA_files = sorted([name[:-4] for name in os.listdir(path_ema_files) if name.endswith('.ema')])
    cols_index = None
    n_columns = 87
    window=5
    path_wav_files = os.path.join(root_path, "Donnees_brutes\Donnees_breakfast\MNGU0\wav")
    wav_files = sorted([name[:-4] for name in os.listdir(path_wav_files) if name.endswith('.wav')])
    sampling_rate_mfcc = 16000
    frame_time = 25
    hop_time = 10  # en ms
    hop_length = int((hop_time * sampling_rate_mfcc) / 1000)
    frame_length = int((frame_time * sampling_rate_mfcc) / 1000)
    n_coeff = 13
    n_col_mfcc = n_coeff*(2*window+1)*3

    EMA_files = sorted([name[:-4] for name in os.listdir(path_ema_files) if name.endswith('.ema')])
    if N == all:
        N = len(wav_files)
    def first_step_ema_data(i):
        """
        :param i: index de l'uttérence (ie numero de phrase) dont les données EMA seront extraites
        :return: les données EMA en format npy pour l'utterance i avec les premiers traitements.
        :traitement : lecture du fichier .ema et recup des données, filtre sur les articulateurs qui nous intéressent ,
        ajout du lip aperture, interpolation pour données manquantes
        En sortie nparray de dimension (K,13), où K dépend de la longueur de la phrase
         (fréquence d'échantillonnage de 200Hz donc K = 200*durée_en_sec)
        """
        path_ema_file = os.path.join(path_ema_files, EMA_files[i] + ".ema")
        with open(path_ema_file, 'rb') as ema_annotation:
            column_names = [0] * n_columns
            for line in ema_annotation:
                line = line.decode('latin-1').strip("\n")
                if line == 'EST_Header_End':
                    break
                elif line.startswith('NumFrames'):
                    n_frames = int(line.rsplit(' ', 1)[-1])
                elif line.startswith('Channel_'):
                    col_id, col_name = line.split(' ', 1)
                    column_names[int(col_id.split('_', 1)[-1])] = col_name

            ema_data = np.fromfile(ema_annotation, "float32").reshape(n_frames, n_columns + 2)
            cols_index = [column_names.index(col) for col in articulators]
            ema_data = ema_data[:, cols_index]
            ind_1, ind_2 = [articulators.index("upperlip_pz"), articulators.index("lowerlip_pz")]
            lip_aperture = (ema_data[:, ind_1] - ema_data[:, ind_2]).reshape(len(ema_data), 1)
            ema_data = np.concatenate((ema_data, lip_aperture), axis=1)
            #dabord enlever les nan avant de lisser et sous echantillonner
            if np.isnan(ema_data).sum() != 0:
                # Build a cubic spline out of non-NaN values.
                spline = scipy.interpolate.splrep( np.argwhere(~np.isnan(ema_data).ravel()), ema_data[~np.isnan(ema_data)], k=3)
                # Interpolate missing values and replace them.
                for j in np.argwhere(np.isnan(ema_data)).ravel():
                    ema_data[j] = scipy.interpolate.splev(j, spline)
            return ema_data

    def first_step_wav_data(i): #reste à enlever les blancs et normaliser et ajouter trames passées et futures
        """
           :param i: index de l'uttérence (ie numero de phrase) dont les données WAV seront extraites
           :return: les MFCC en format npy pour l'utterance i avec les premiers traitements.
           :traitement : lecture du fichier .wav, extraction des mfcc avec librosa, ajout des Delta et DeltaDelta
           (features qui représentent les dérivées premières et secondes des mfcc)
           On conserve les 13 plus grands MFCC pour chaque frame de 25ms.
           En sortie nparray de dimension (K',13*3)=(K',39). Ou K' dépend de la longueur de la phrase
           ( Un frame toutes les 10ms, donc K' ~ duree_en_sec/0.01 )
           """
        path_wav = os.path.join(path_wav_files, wav_files[i] + '.wav')
        data, sr = librosa.load(path_wav, sr=sampling_rate_mfcc)  # chargement de données

        mfcc = librosa.feature.mfcc(y=data, sr=sampling_rate_mfcc, n_mfcc=n_coeff,
                                    n_fft=frame_length, hop_length=hop_length
                                    ).T
        dyna_features = get_delta_features(mfcc)
        dyna_features_2 = get_delta_features(dyna_features)

        mfcc = np.concatenate((mfcc, dyna_features, dyna_features_2), axis=1)
        return mfcc

    def second_step_data(i,ema,mfcc):
        """
        :param i:  index de l'uttérence (ie numero de phrase) pour laquelle on va traiter le fichier EMA et MFCC
        :param ema: Données EMA en format .npy en sortie de la fonction first_step_ema_data(i)
        :param mfcc: Données MFCC en format .npy en sortie de la fonction first_step_wav_data(i)
        :return: les npy EMA et MFCC de taille (K,13) et (K,429) avec le même nombre de lignes
        :traitement lecture du fichier d'annotation .lab , on enlève les frames MFCC et EMA qui correspondent à du silence
        On sous échantillone le nparray EMA pour avoir 1 donnée par frame MFCC.
        On ajoute le 'contexte' aux données MFCC ie les 5 frames précédent et les 5 frames suivant chaque frame,
        d'où la taille de mfcc 429 = 5*39 + 5*39 + 39
        """

        #remove blanks at the beginning and the end, en sortie autant de lignes pour les deux
        path_annotation = os.path.join(path_files_annotation, wav_files[i] + '.lab')
        with open(path_annotation) as file:
            while next(file) != '#\n':
                pass
            labels = [  row.strip('\n').strip('\t').replace(' 26 ', '').split('\t') for row in file     ]
        labels =  [(round(float(label[0]), 2), label[1]) for label in labels]
        start_time = labels[0][0] if labels[0][1] == '#' else 0
        end_time = labels[-2][0] if labels[-1][1] == '#' else labels[-1][0]
        start_frame_mfcc = int(
            np.floor(start_time * 1000 / hop_time))  # nombre de frame mfcc avant lesquelles il ny a que du silence
        end_frame_mfcc = int(np.ceil(end_time * 1000 / hop_time))  # nombre de frame mfcc apres lesquelles il ny a que du silence
        mfcc = np.array(mfcc[start_frame_mfcc:end_frame_mfcc])
        start_frame_ema = int(np.floor(start_time * sampling_rate_ema))
        end_frame_ema = int(np.ceil(end_time * sampling_rate_ema))
        ema = ema[start_frame_ema:end_frame_ema]

        #sous echantillonnage de EMA pour synchro avec WAV
        n_frames_wanted = mfcc.shape[0]
        ema = scipy.signal.resample(ema, num=n_frames_wanted)

        #  padding de sorte que l'on intègre les dépendences temporelles : on apprend la trame du milieu
        # mais on ajoute des trames précédent et suivant pour ajouter de l'informatio temporelle
        padding = np.zeros((window, mfcc.shape[1]))
        frames = np.concatenate([padding, mfcc, padding])
        full_window = 1 + 2 * window
        mfcc=  np.concatenate(  [frames[i:i + len(mfcc)] for i in range(full_window)], axis=1)

        return ema,mfcc

    ALL_EMA = np.zeros((1,n_col_ema))
    ALL_MFCC = np.zeros((1,n_col_mfcc))

    #traitement uttérance par uttérance des phrases
    for i in range(N):
        if i%100 ==0:
            print(i," out of ",N)
        ema = first_step_ema_data(i)
        mfcc = first_step_wav_data(i)
        ema, mfcc = second_step_data(i, ema, mfcc)
        if ema.shape[0] != mfcc.shape[0]:
            print("probleme de shape")
        np.save(os.path.join(root_path, "Donnees_pretraitees\MNGU0\ema", EMA_files[i]),ema) #sauvegarde temporaire pour la récup après
        np.save(os.path.join(root_path, "Donnees_pretraitees\MNGU0\mfcc", wav_files[i]),mfcc) #sauvegarde temporaire pour la récup après
        ALL_EMA = np.concatenate((ALL_EMA,ema),axis=0)
        ALL_MFCC = np.concatenate((ALL_MFCC,mfcc),axis=0)

    ALL_EMA  =ALL_EMA[1:]  #concaténation de toutes les données EMA
    ALL_MFCC = ALL_MFCC[1:] #concaténation de toutes les frames mfcc

    # de taille 429 : moyenne et std de chaque coefficient
    mean_mfcc = np.mean(ALL_MFCC,axis=0)
    std_mfcc = np.std(ALL_MFCC,axis=0)

    # de taille 13 : moyenne et std de chaque articulateur
    mean_ema = np.mean(ALL_EMA, axis=0)
    std_ema = np.std(ALL_EMA, axis=0)
    np.save("std_ema_MNGU0",std_ema)

    # construction du filtre passe bas que lon va appliquer à chaque frame mfcc et trajectoire d'articulateur
    # la fréquence de coupure réduite de 0.1 a été choisi manuellement pour le moment, et il se trouve qu'on
    # n'a pas besoin d'un filtre différent pour mfcc et ema
    order = 5
    cutoff = 20
    filt_b, filt_a = scipy.signal.butter(order, 0.1, btype='lowpass', analog=False) #fs=sampling_rate_ema)

    for i in range(N):
        if i%100 ==0:
            print(i," out of ",N)
        ema = np.load(os.path.join(root_path, "Donnees_pretraitees\MNGU0\ema", EMA_files[i]+".npy"))
        ema = (ema - mean_ema) /std_ema

        filtered_data_ema = np.concatenate([np.expand_dims(scipy.signal.filtfilt(filt_b, filt_a, channel), 1)
                                        for channel in ema.T], axis=1)
        ema = np.reshape(filtered_data_ema, ema.shape)

        mfcc = np.load(os.path.join(root_path, "Donnees_pretraitees\MNGU0\mfcc", wav_files[i]+".npy"))
        mfcc = (mfcc - mean_mfcc)/std_mfcc

        filtered_data_mfcc = np.concatenate([np.expand_dims(scipy.signal.filtfilt(filt_b, filt_a, channel), 1)
                                        for channel in mfcc.T], axis=1)
        mfcc = np.reshape(filtered_data_mfcc, mfcc.shape)

        np.save(os.path.join(root_path, "Donnees_pretraitees\MNGU0\ema", EMA_files[i]),ema)
        np.save(os.path.join(root_path, "Donnees_pretraitees\MNGU0\mfcc", wav_files[i]),mfcc)

    #path_mfcc_mngu0 = os.path.join(path_files_treated,"MNGU0_mfcc.npy")
    #np.save(path_mfcc_mngu0, ALL_MFCC)

    #path_ema_mngu0 = os.path.join(path_files_treated,"MNGU0_ema.npy")
    #np.save(path_ema_mngu0, ALL_EMA)


traitement_general_mngu0(5)


