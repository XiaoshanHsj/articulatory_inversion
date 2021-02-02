import sys
import os
import re

# sys.argv[1]: plp scp file (with time label)
# sys.argv[2]: output mlf file path

train_scp = sys.argv[1]
out_mlf_path = sys.argv[2]

raw_path = "/project_bdda3/bdda/sjhu/Data/torgo/"

with open(out_mlf_path, 'w') as f_w:
    f_w.write("#!MLF!#\n")
    with open(train_scp) as f_r:        
        for line in f_r:
            mlf_path = line.strip().split('=')[0].split('.')[0]
            try:
                _, _, s, _, index = mlf_path.split('-')
            except:
                print(line.strip())
            s = s[s.rfind("X")+1:]
            sess = "Session" + s[0:2][-1]
            sp = s[2:]
            index = index.split('_')[1].lstrip('X')
            
            pro_path = raw_path + sp + "/" + sess + "/prompts/" + index + ".txt"
            with open(pro_path, "r") as f:
                utterance = f.readline()
                if not utterance[-1].isalpha():
                    utterance = utterance[:-1]
                
                mlf_full_path = "\"*/" + mlf_path + ".lab\""
                f_w.write(mlf_full_path + '\n')
                words = utterance.split()
                for word in words:
                    if not word[-1].isalpha():
                        word = word[:-1]
                    if not word[0].isalpha():
                        word = word[1:]
                    word = word.upper()
                    if word == "XRAY":
                        word = "X-RAY"
                    f_w.write(word + '\n')
                f_w.write('.\n')