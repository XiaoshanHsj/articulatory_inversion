import sys
import os

# 第一步是根据prompts中的内容来判断是否要删去对应的wav和pos
speakers = ["F03", "F04", "FC01", "FC02", "FC03","M01", "M02", "M03", "M04", "M05", "MC01", "MC02", "MC03", "MC04"]
ori_path = "/project_bdda3/bdda/sjhu/Data/Raw_data/torgo/"
raw_path = "/project_bdda3/bdda/sjhu/Data/torgo/"

for sp in speakers:
    wav_path = ori_path + sp + "/wav"
    wav_files = os.listdir(wav_path)
    for wav in wav_files:
        name = wav[:-4]
        sess = "Session" + name.split("_")[1][-1]
        num = name.split("_")[2]
        pro_path = raw_path + sp + "/" + sess + "/prompts/" + num + ".txt"
        with open(pro_path, 'r') as f:
            line = f.readline()
            if line.find(".jpg") != 0 or line.find("[") != 0 or line.find("]") != 0:
                # 此时我们需要将对应的.wav和.pos删去
                wav_abs_path = wav_path + "/" + wav
                pos_abs_path = ori_path + sp + "/pos/" + name + ".pos"
                try:
                    os.remove(wav_abs_path)
                    print("删去了" + wav_abs_path)
                    os.remove(pos_abs_path)
                    print("删去了" + pos_abs_path)
                except:
                    print(line)