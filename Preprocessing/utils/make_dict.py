import os,sys

dict_path = "/project_bdda3/bdda/sjhu/Data/Raw_data/torgo/data/dict/lexicon.txt"
save_path = "/project_bdda3/bdda/sjhu/Data/Raw_data/torgo/convert/lib/dicts/"
filename = "train.pi_ti.dct"

with open(save_path + filename, "w") as f_w:
    with open(dict_path , "r") as f_r:
        for line in f_r:
            word = line.split()[0]
            phones = line.split()[1:]
            if word.find("SIL") != -1:
                continue
            else:
                new_line = word + "\t\t"
                for phone in phones:
                    new_line = new_line + phone.lower() + "\t"
                new_line = new_line[:-1]
                f_w.write(new_line + "\n")