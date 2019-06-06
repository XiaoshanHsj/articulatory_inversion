### Lecture des données EMA pour le corpus MOCHA. On ne conserve que les données concercnant les articulateurs indiqués
### dans articulators cest a dire 6 articulateurs en 2Dimensions.
### on normalise on soustrayant pour chaque articulateur sa position moyenne et en divisant par sa std
### il semble qu'un articulateur reste à la même position (li_x) voir si on le garde quand meme.
### il n'y au aucune valeur manquante donc pas besoin d'interpolation.
### revoir la longueur de col names


# A RENOMMER TRAITEMENT_MOCHA !! LE LARYNX ICI
import os
import time
from os.path import dirname
import numpy as np
import scipy.signal
from scipy import stats
import matplotlib.pyplot as plt
import scipy.interpolate
from Traitement.add_dynamic_features import get_delta_features
import librosa

def traitement_general_mocha(N=all):

    root_path = dirname(dirname(os.path.realpath(__file__)))
    path_files_treated = os.path.join(root_path, "Donnees_pretraitees")
    order = 5
    cutoff = 20
    sampling_rate_ema = 500
    articulators = [
        'tt_x', 'tt_y', 'td_x', 'td_y', 'tb_x', 'tb_y', 'li_x', 'li_y',
        'ul_x', 'ul_y', 'll_x', 'll_y','v_x ','v_y ']

    n_col_ema = len(articulators)+1 #plus lip aperture
    def first_step_ema_data(i,speaker):
        """

        :param i: index de l'uttérence (ie numero de phrase) dont les données EMA seront extraites
                speaker : fsew0 ou msak0
        :return: les données EMA en format npy pour l'utterance i avec les premiers traitements.
        :traitement : lecture du fichier .ema et recup des données, filtre sur les articulateurs qui nous intéressent ,
        ajout du lip aperture, interpolation pour données manquantes
        En sortie nparray de dimension (K,13), où K dépend de la longueur de la phrase
         (fréquence d'échantillonnage de 200Hz donc K = 200*durée_en_sec)
        """

        path_files = os.path.join(root_path, "Donnees_brutes\Donnees_breakfast\mocha\\" + speaker)
        EMA_files = sorted([name[:-4] for name in os.listdir(path_files) if name.endswith('.ema')])
        path_ema_file = os.path.join(path_files, EMA_files[i] + ".ema")
        N= len(wav_files)


        with open(path_ema_file,'rb') as ema_annotation:
            column_names=[0]*n_columns
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

            ema_data = ema_data[:, cols_index]/1000
            ind_1, ind_2 = [articulators.index("ul_y"), articulators.index("ll_y")]
            lip_aperture = (ema_data[:,ind_1] - ema_data[:,ind_2]).reshape(len(ema_data),1)
            ema_data = np.insert(ema_data,[1],lip_aperture, axis=1)

            #dabord enlever les nan avant de lisser etsous echantillonner
            # donnees en milimètres
            if np.isnan(ema_data).sum() != 0:
                # Build a cubic spline out of non-NaN values.
                spline = scipy.interpolate.splrep( np.argwhere(~np.isnan(ema_data).ravel()), ema_data[~np.isnan(ema_data)], k=3)
                # Interpolate missing values and replace them.
                for j in np.argwhere(np.isnan(ema_data)).ravel():
                    ema_data[j] = scipy.interpolate.splev(j, spline)
            return ema_data

    def first_step_wav_data(i,speaker):
        """
         :param i: index de l'uttérence (ie numero de phrase) dont les données WAV seront extraites
                speaker : msak0 ou fsew0
         :return: les MFCC en format npy pour l'utterance i avec les premiers traitements.
         :traitement : lecture du fichier .wav, extraction des mfcc avec librosa, ajout des Delta et DeltaDelta
         (features qui représentent les dérivées premières et secondes des mfcc)
         On conserve les 13 plus grands MFCC pour chaque frame de 25ms.
         En sortie nparray de dimension (K',13*3)=(K',39). Ou K' dépend de la longueur de la phrase
         ( Un frame toutes les 10ms, donc K' ~ duree_en_sec/0.01 )
         """
        path_files = os.path.join(root_path, "Donnees_brutes\Donnees_breakfast\mocha\\" + speaker)
        wav_files = sorted([name[:-4] for name in os.listdir(path_files) if name.endswith('.wav')])
        path_wav = os.path.join(path_files, wav_files[i] + '.wav')
        data, sr = librosa.load(path_wav, sr=sampling_rate_mfcc)  # chargement de données

        mfcc = librosa.feature.mfcc(y=data, sr=sampling_rate_mfcc, n_mfcc=n_coeff,
                                    n_fft=frame_length, hop_length=hop_length
                                    ).T

        dyna_features = get_delta_features(mfcc)
        dyna_features_2 = get_delta_features(dyna_features)

        mfcc = np.concatenate((mfcc, dyna_features, dyna_features_2), axis=1)
        return mfcc

    def second_step_data(i,ema,mfcc,speaker):
        """
              :param i:  index de l'uttérence (ie numero de phrase) pour laquelle on va traiter le fichier EMA et MFCC
                     speaker : msak0 ou fsew0
              :param ema: Données EMA en format .npy en sortie de la fonction first_step_ema_data(i)
              :param mfcc: Données MFCC en format .npy en sortie de la fonction first_step_wav_data(i)
              :return: les npy EMA et MFCC de taille (K,13) et (K,429) avec le même nombre de lignes
              :traitement lecture du fichier d'annotation .lab , on enlève les frames MFCC et EMA qui correspondent à du silence
              On sous échantillone le nparray EMA pour avoir 1 donnée par frame MFCC.
              On ajoute le 'contexte' aux données MFCC ie les 5 frames précédent et les 5 frames suivant chaque frame,
              d'où la taille de mfcc 429 = 5*39 + 5*39 + 39
              """


        path_files = os.path.join(root_path, "Donnees_brutes\Donnees_breakfast\mocha\\" + speaker)
        wav_files = sorted([name[:-4] for name in os.listdir(path_files) if name.endswith('.wav')])
        path_annotation = os.path.join(path_files, wav_files[i] + '.lab')
        with open(path_annotation) as file:
            labels = [
                row.strip('\n').strip('\t').replace(' 26 ', '').split(' ')
                for row in file
            ]
        start_time = float(labels[0][1])  # if labels[0][1] == '#' else 0
        end_time = float(labels[-1][0])  # if labels[-1][1] == '#' else labels[-1][0]
        start_frame_mfcc = int(np.floor(start_time * 1000 / hop_time))  # nombre de frame mfcc avant lesquelles il ny a que du silence
        end_frame_mfcc = int(np.ceil(end_time * 1000 / hop_time))  # nombre de frame mfcc apres lesquelles il ny a que du silence
        mfcc = np.array(mfcc[start_frame_mfcc:end_frame_mfcc])
        start_frame_ema = int(np.floor(start_time * sampling_rate_ema))
        end_frame_ema = int(np.ceil(end_time * sampling_rate_ema))
        ema = ema[start_frame_ema:end_frame_ema]

        #sous echantillonnage de EMA pour synchro avec WAV
        n_frames_wanted = mfcc.shape[0]
        ema = scipy.signal.resample(ema, num=n_frames_wanted)

        ## zero padding de sorte que l'on intègre les dépendences temporelles : on apprend la trame du milieu
        # mais on ajoute des trames précédent et suivant pour ajouter de l'informatio temporelle

        padding = np.zeros((window, mfcc.shape[1]))
        frames = np.concatenate([padding, mfcc, padding])
        length = len(mfcc)
        full_window = 1 + 2 * window
        mfcc=  np.concatenate(  [frames[i:i + len(mfcc)] for i in range(full_window)], axis=1)

        return ema,mfcc

    window = 5
    n_coeff = 13
    n_col_mfcc = n_coeff*(2*window+1)*3
    speakers=["fsew0","msak0"]
    sampling_rate_mfcc = 16000
    frame_time = 25
    hop_time = 10  # en ms
    hop_length = int((hop_time * sampling_rate_mfcc) / 1000)
    frame_length = int((frame_time * sampling_rate_mfcc) / 1000)
    cutoff=20
    #2*cutoff/sampling_rate_ema = 2*20/500 = 40/500 = 4/50 = 4*2/100 = 0.08
    filt_b, filt_a = scipy.signal.butter(order, 0.2, btype='lowpass', analog=False) #fs=sampling_rate_ema)
    filt_b_ema, filt_a_ema = scipy.signal.butter(order, 0.08, btype='lowpass', analog=False) #fs=sampling_rate_ema)

    for k in range(2) :

        speaker = speakers[k]
        path_files = os.path.join(root_path, "Donnees_brutes\Donnees_breakfast\mocha\\" + speaker)

        EMA_files = sorted([name[:-4] for name in os.listdir(path_files) if name.endswith('.ema')])
        cols_index = None
        n_columns = 20
        wav_files = sorted([name[:-4] for name in os.listdir(path_files) if name.endswith('.wav')])
        if N == all:
            N = len(wav_files)

        ALL_EMA= np.zeros((1, n_col_ema))
        ALL_MFCC = np.zeros((1, n_col_mfcc))
        for i in range(N):
            if i%100 ==0:
                print(i," out of ",N)
            ema = first_step_ema_data(i,speaker)   # recup ema de occurence i, conserve colonnes utiles, interpole données manquantes, filtre passe bas pour lisser

            mfcc = first_step_wav_data(i,speaker) #recup MFCC de occurence i,  calcule 13 plus grands mfcc sur chaque trame, calcule les delta et deltadelta
            ema, mfcc = second_step_data(i, ema, mfcc,speaker) # enleve les silences en début et fin, ajoute trames alentours pour mfcc, normalise (ema par arti, mfcc en tout)
            if ema.shape[0] != mfcc.shape[0]:
                print("probleme de shape")

            # filtre passe bas : a cause du bruit il est utile de lisser un peu les donnée ema a 20Hz pas tres utile pour ce corpus

            filtered_data_ema = np.concatenate([np.expand_dims(scipy.signal.filtfilt(filt_b_ema, filt_a_ema, channel), 1)
                                            for channel in ema.T], axis=1)

            filtered_data_mfcc = np.concatenate([np.expand_dims(scipy.signal.filtfilt(filt_b, filt_a, channel), 1)
                                                for channel in mfcc.T], axis=1)

            ema = np.reshape(filtered_data_ema, ema.shape)
            mfcc = np.reshape(filtered_data_mfcc, mfcc.shape)

            np.save(os.path.join(root_path, "Donnees_pretraitees","mocha_"+speaker,"ema", EMA_files[i]),ema)
            np.save(os.path.join(root_path, "Donnees_pretraitees","mocha_"+speaker,"mfcc", wav_files[i]),mfcc)

            ALL_EMA = np.concatenate((ALL_EMA,ema),axis=0)
            ALL_MFCC= np.concatenate((ALL_MFCC,mfcc),axis=0)

        ALL_EMA = ALL_EMA[1:]
        ALL_MFCC = ALL_MFCC[1:]

        std_ema = np.std(ALL_EMA, axis=0)
        mean_ema = np.mean(ALL_EMA,axis=0)

        std_mfcc  = np.std(ALL_MFCC,axis=0)
        mean_mfcc = np.mean(ALL_MFCC,axis=0)

        np.save("std_ema_arti_mocha",std_ema)

        path_files = os.path.join(root_path, "Donnees_brutes\Donnees_breakfast\mocha\\" + speakers[k])
        EMA_files = sorted([name[:-4] for name in os.listdir(path_files) if name.endswith('.ema')])

        for i in range(N):
            ema = np.load(os.path.join(root_path, "Donnees_pretraitees","mocha_"+speaker,"ema", EMA_files[i]+".npy"))
            ema = (ema - mean_ema)
            ema = ema/std_ema
            ema_without_lar = ema[:,:-2]

            mfcc = np.load(os.path.join(root_path, "Donnees_pretraitees","mocha_"+speaker,"mfcc", EMA_files[i]+".npy"))
            mfcc = (mfcc - mean_mfcc) / std_mfcc

            np.save(os.path.join(root_path, "Donnees_pretraitees", "mocha_" + speaker, "ema", EMA_files[i]), ema)
            np.save(os.path.join(root_path, "Donnees_pretraitees", "mocha_" + speaker, "mfcc", wav_files[i]), mfcc)

            ALL_EMA = np.concatenate((ALL_EMA, ema), axis=0)





traitement_general_mocha(N=10)