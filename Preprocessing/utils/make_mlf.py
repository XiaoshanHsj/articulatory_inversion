import sys
import os
import re

# sys.argv[1]: word index file
# sys.argv[2]: plp scp file (with time label)
# sys.argv[3]: output mlf file path

word_index = sys.argv[1]
train_scp = sys.argv[2]
out_mlf_path = sys.argv[3]

word_index_dict = {}
with open(word_index) as f_r:
    for line in f_r:
        word, index = line.strip().split()
        word = word.upper()
        word_index_dict[index] = word

with open(out_mlf_path, 'w') as f_w:
    f_w.write("#!MLF!#\n")
    with open(train_scp) as f_r:        
        for line in f_r:
            mlf_path = line.strip().split('=')[0].split('.')[0]
            try:
                _, _, BLK, _, index = mlf_path.split('-')
            except:
                print(line.strip())
            BLK = re.search(r'B\d', BLK).group()
            index = index.split('_')[1].lstrip('X').rstrip('1234567890')[:-1]
            if index.startswith('UW'):
                index = BLK + '_' + index
            if index in word_index_dict:
                word = word_index_dict[index]
            mlf_full_path = "\"*/" + mlf_path + ".lab\""
            f_w.write(mlf_full_path + '\n')
            f_w.write(word + '\n')
            f_w.write('.\n')
