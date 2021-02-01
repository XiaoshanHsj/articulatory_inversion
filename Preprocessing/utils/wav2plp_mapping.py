import sys
import os

# sys.argv[1]: input .wav files folder
# sys.argv[2]: output .plp files folder
# sys.argv[3]: output mapping file path

wav_folder = sys.argv[1]
plp_folder = sys.argv[2]
mapping_file_path = sys.argv[3]

wav_files = os.popen("find %s -name \"*.wav\"" % wav_folder).read().split()
with open(mapping_file_path, 'w') as f_w:
    for wav_file in wav_files:
        wav_file_suffix = wav_file.split('/')[-1]
        plp_file_suffix = wav_file_suffix.rstrip(".wav") + ".plp"
        plp_out_path = plp_folder.rstrip('/') + "/%s" % plp_file_suffix
        write_line = wav_file + '\t' + plp_out_path
        f_w.write(write_line)
        f_w.write('\n')
