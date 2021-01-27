import os,sys,shutil

ori_path = "/project_bdda3/bdda/sjhu/Data/torgo"
des_path = "/project_bdda3/bdda/sjhu/Data/Raw_data/torgo"
speakers = ["F01", "F03", "F04", "FC01", "FC02", "FC03","M01", "M02", "M03", "M04", "M05", "MC01", "MC02", "MC03", "MC04"]

# 对于每一个说话人，依次扫描SESSION,如果有pos和wav_array就就复制到Raw_data/torgo中
# torgo的文件目录为speaker/wav speaker/prompt speaker/pos
# 每个文件夹内容为session_0001.xxx

def process():
    for sp in speakers:
        if not os.path.exists(des_path+"/"+sp):
            print("create " + des_path+"/"+sp)
            os.mkdir(des_path+"/"+sp)
        temp_path = ori_path + "/" + sp
        dirs = os.listdir(temp_path)
        flag = False
        # 遍历Session
        for d in dirs:
            if d.find("Session") != -1:
                sess = temp_path + "/" + d
                content = os.listdir(sess)
                # 满足条件
                if "pos" in content and "wav_arrayMic" in content:
                    flag = True
                    pre = d + "_"
                    # 处理pos
                    pos_list = os.listdir(sess+"/pos")
                    if not os.path.exists(des_path+"/"+sp+"/pos"):
                        print("create " + des_path+"/"+sp+"/pos")
                        os.mkdir(des_path+"/"+sp+"/pos")
                    for p in pos_list:
                        if p[-4:] != ".pos":
                            continue
                        abs_dir = sess + "/pos/"+ p
                        new_filename = pre + p
                        shutil.copy(abs_dir, des_path+"/"+sp+"/pos/"+new_filename)
                        
                    # 处理wav
                    wav_list = os.listdir(sess+"/wav_arrayMic")
                    if not os.path.exists(des_path+"/"+sp+"/wav"):
                        print("create " + des_path+"/"+sp+"/wav")
                        os.mkdir(des_path+"/"+sp+"/wav")
                    for p in wav_list:
                        if p[-4:] != ".wav":
                            continue
                        abs_dir = sess + "/wav_arrayMic/"+ p
                        new_filename = pre + p
                        shutil.copy(abs_dir, des_path+"/"+sp+"/wav/"+new_filename)
                    
        if flag is True:
            wav_path = des_path + "/" + sp + "/wav"
            wav_files = os.listdir(wav_path)
            pos_path = des_path + "/" + sp + "/pos"
            pos_files = os.listdir(pos_path)
            # 1 pass wav->pos
            for wav_file in wav_files:
                wav_name = wav_file[:-4]
                pos_name = pos_path + "/" + wav_name + ".pos"
                if not os.path.exists(pos_name):
                    print("删除了" + wav_path+"/"+wav_file)
                    os.remove(wav_path+"/"+wav_file)
                    
            # 2 pass pos->wav
            for pos_file in pos_files:
                pos_name = pos_file[:-4]
                wav_name = wav_path + "/" + pos_name + ".wav"
                if not os.path.exists(wav_name):
                    print("删除了" + pos_path+"/"+pos_file)
                    os.remove(pos_path+"/"+pos_file)

if __name__ == "__main__":
    process()