import os,sys,inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)

import scipy.signal
import scipy.interpolate
import scipy.io as sio
from Preprocessing.tools_preprocessing import get_fileset_names, get_delta_features, split_sentences

from os.path import dirname
import numpy as np
import scipy.signal
import scipy.interpolate
import librosa
from Preprocessing.class_corpus import Speaker
import glob

root_path = dirname(dirname(os.path.realpath(__file__)))

order_arti_torgo = ["td_x","td_y", "tb_x","tb_y", "tt_x","tt_y", "forehead_x", "forehead_y",
                "bn_x", "bn_y", "ul_x", "ul_y","ll_x", "ll_y", "li_x", "li_y", 
                "left_lip_x","left_lip_y", "right_lip_x", "right_lip_y",
                "left_ear_x", "left_ear_y","right_ear_x", "right_ear_y"]

order_arti = ['tt_x', 'tt_y', 'td_x', 'td_y', 'tb_x', 'tb_y', 'li_x', 'li_y',
              'ul_x', 'ul_y', 'll_x', 'll_y']

# 需要把所有的session整合
class Speaker_TORGO(Speaker):
    def __init__(self, sp, path_to_raw, N_max = 0):
        super().__init__(sp)
        self.root_path = path_to_raw
        self.path_files_annotation = os.path.join(self.root_path, "Raw_data", self.speaker, "prompts")
        self.path_ema_files = os.path.join(self.root_path, "Raw_data", self.speaker, "pos")
        self.EMA_files = sorted([name[:-4] for name in os.listdir(self.path_ema_files) if name.endswith('.pos')])
        self.path_files_treated = os.path.join(root_path, "Preprocessed_data", self.speaker)
        self.path_files_brutes = os.path.join(self.root_path, "Raw_data", self.speaker)
        self.path_wav_files = os.path.join(self.root_path, "Raw_data", self.speaker, "wav_arrayMic")

        self.N_max = N_max

    def create_missing_dir(self):
        """
        delete all previous preprocessing, create needed directories
        """
        if not os.path.exists(os.path.join(os.path.join(self.path_files_treated, "ema"))):
            os.makedirs(os.path.join(self.path_files_treated, "ema"))
        if not os.path.exists(os.path.join(os.path.join(self.path_files_treated, "ema_final"))):
            os.makedirs(os.path.join(self.path_files_treated, "ema_final"))
        if not os.path.exists(os.path.join(os.path.join(self.path_files_treated, "mfcc"))):
            os.makedirs(os.path.join(self.path_files_treated, "mfcc"))

        files = glob.glob(os.path.join(self.path_files_treated, "ema", "*"))
        files += glob.glob(os.path.join(self.path_files_treated, "ema_final", "*"))
        files += glob.glob(os.path.join(self.path_files_treated, "mfcc", "*"))

        for f in files:
            os.remove(f)

    
    def read_ema_file(self, k):
        """
        read the ema file, first preprocessing,
        :param i: utterance index (wrt EMA files)
        :return: npy array (K,12) , K depends on the duration of the recording, 12 trajectories
        """

        path_ema_file = os.path.join(self.path_ema_files, self.EMA_files[k] + ".pos")
        ema_data = np.fromfile(filename, dtype='<f4', count=-1).reshape((-1, 7, 12))
        ema = np.zeros(len(ema_data), len(order_arti_torgo))

        for arti in range(7):
            for j in range(len(ema_data)):
                ema[j][(arti - 1) * 2] = ema_data[j][0][arti]
                ema[j][arti * 2 - 1] = ema_data[j][2][arti]
        new_order_arti = [order_arti_torgo.index(col) for col in order_arti]
        ema = ema[:, new_order_arti]

        return ema

    
    def remove_silences(self,k, ema, mfcc):
        """
       :param k:  utterance index (wrt the list EMA_files)
       :param ema: the ema list of traj
       :param mfcc: the mfcc features
       :return: the data (ema and mfcc) without the silence at the beginning and end of the recording

       """

        marge=0
        n_points_de_silences_ema = int(np.floor(marge * self.sampling_rate_ema))
        xtrm_temp_ema = [n_points_de_silences_ema, len(ema) - n_points_de_silences_ema]

        n_frames_de_silences_mfcc = int(np.floor(marge / self.hop_time))
        xtrm_temp_mfcc = [n_frames_de_silences_mfcc, len(mfcc) - n_frames_de_silences_mfcc]
        #   print("avant ",mfcc.shape)
        mfcc = mfcc[xtrm_temp_mfcc[0]:xtrm_temp_mfcc[1]]
        ema = ema[xtrm_temp_ema[0]:xtrm_temp_ema[1], :]
        # print("apres",mfcc.shape)
        return ema, mfcc

    def from_wav_to_mfcc(self, wav):
        mfcc = librosa.feature.mfcc(y=wav, sr=self.sampling_rate_wav, n_mfcc=self.n_coeff,
                                    n_fft=self.frame_length, hop_length=self.hop_length
                                    ).T

        dyna_features = get_delta_features(mfcc)
        dyna_features_2 = get_delta_features(dyna_features)
        mfcc = np.concatenate((mfcc, dyna_features, dyna_features_2), axis=1)
        padding = np.zeros((self.window, mfcc.shape[1]))
        frames = np.concatenate([padding, mfcc, padding])
        full_window = 1 + 2 * self.window
        mfcc = np.concatenate([frames[i:i + len(mfcc)] for i in range(full_window)], axis=1)
        return mfcc

    def Preprocessing_general_speaker(self):
        
        self.create_missing_dir()
        N = len(self.EMA_files)
        if self.N_max != 0:
            N = self.N_max
        for i in range(N):
            ema = self.read_ema_file(i)
            ema_VT = self.add_vocal_tract(ema)
            ema_VT_smooth = self.smooth_data(ema_VT)
            path_wav = os.path.join(self.path_wav_files, self.EMA_files[i] + '.wav')
            wav, sr = librosa.load(path_wav, sr=self.sampling_rate_wav)
            wav = 0.5 * wav / np.max(wav)
            mfcc = self.from_wav_to_mfcc(wav)
            ema_VT_smooth, mfcc = self.remove_silences(i, ema_VT_smooth, mfcc)
            ema_VT_smooth, mfcc = self.synchro_ema_mfcc(ema_VT_smooth, mfcc)
            np.save(os.path.join(root_path, "Preprocessed_data", self.speaker, "ema", self.EMA_files[i]), ema_VT)
            np.save(os.path.join(root_path, "Preprocessed_data", self.speaker, "mfcc", self.EMA_files[i]), mfcc)
            np.save(os.path.join(root_path, "Preprocessed_data", self.speaker, "ema_final", self.EMA_files[i]), ema_VT_smooth)
            self.list_EMA_traj.append(ema_VT_smooth)
            self.list_MFCC_frames.append(mfcc)
        self.calculate_norm_values()

        for i in range(N):
            ema_VT_smooth = np.load(
                os.path.join(root_path, "Preprocessed_data", self.speaker, "ema_final", self.EMA_files[i] + ".npy"))
            mfcc = np.load(os.path.join(root_path, "Preprocessed_data", self.speaker, "mfcc", self.EMA_files[i] + ".npy"))
            ema_VT_smooth_norma, mfcc = self.normalize_sentence(i, ema_VT_smooth, mfcc)
            np.save(os.path.join(root_path, "Preprocessed_data", self.speaker, "mfcc", self.EMA_files[i]), mfcc)
            np.save(os.path.join(root_path, "Preprocessed_data", self.speaker, "ema_final", self.EMA_files[i]),
                    ema_VT_smooth_norma)
        #  split_sentences(speaker)
        get_fileset_names(self.speaker)


def Preprocessing_general_torgo(N_max, path_to_raw):
    """
    :param N_max: #max of files to treat (0 to treat all files), useful for tests
    """
    corpus = 'torgo'
    speakers_Has = get_speakers_per_corpus(corpus)
    for sp in speakers_Has:
        print("In progress togo ",sp)
        speaker = Speaker_TORGO(sp, path_to_raw=path_to_raw, N_max=N_max)
        speaker.Preprocessing_general_speaker()
        print("Done torgo ",sp)