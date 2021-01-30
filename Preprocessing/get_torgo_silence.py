import os,sys,inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)

import json

speakers = ["F03", "F04", "FC01", "FC02", "FC03","M01", "M02", "M03", "M04", "M05", "MC01", "MC02", "MC03", "MC04"]
dest_dir = "/project_bdda3/bdda/sjhu/Projects/my_git/articulatory_inversion/Preprocessing/"
path = "/project_bdda3/bdda/sjhu/Data/Raw_data/torgo"
m = "torgo_speaker_silence"
if not os.path.exists(dest_dir + m):
    os.mkdir(dest_dir + m)
for sp in speakers:
    wav_path = os.path.join(path, sp, "wav")
    wav_files = os.listdir(wav_path)
    j = {}
    for wav in wav_files:
        abs_path = os.path.join(wav_path, wav)
        name = wav[:-4]
        os.system('ffmpeg -i "%s" -af silencedetect=n=-38dB:d=0.5 -f null - 2>&1 | grep -E "silence_(start|end)|Duration" > %s.txt' % (abs_path, name))
        if os.path.exists(name+".txt"):
            with open(name + ".txt") as f:
                x = f.readlines()
                length = len(x)
                flag = False
                times = [0, 0]
                if(length > 1):
                    flag = True
                duration = x[0].split(",")[0].split("n")[1].split(" ")[1]
                d_list = duration.split(":")
                hour = int(d_list[0])
                minute = int(d_list[1])
                second = float(d_list[2])
                if flag:
                    # 如果只有一个silence_start，就说明从这里开始全是silence
                    if length == 2:
                        t = float(x[1].split(":")[1])
                        times[1] = t
                    else:
                        t_e = float(x[2].split("|")[0].split(":")[1])
                        times[0] = t_e
                        # 如果不是1，就看最后一个是start还是end
                        if x[-1].find("silence_start") != -1:
                            # 如果最后一个是start，说明之后都是silence
                            t_s = float(x[-1].split(":")[1])
                            times[1] = t_s
                        else:
                            # 如果最后一个是end，则需要和总时长进行比较
                            t_e = float(x[-1].split("|")[0].split(":")[1])
                            if t_e < second:
                                times[1] = second
                            else:
                                t_s = float(x[-2].split(":")[1])
                                times[1] = t_s
                    if times[0] < 0:
                        times[0] = 0
                    if times[0] > times[1]:
                        times = [0, 0]

                temp = {}
                temp["have_silence"] = flag
                temp["time"] = times
                j[name] = temp

            os.remove(name+".txt")

        
    time_data = json.dumps(j)
    filename = sp+".json"
    with open(dest_dir + m + "/" + filename, 'w') as f:
        f.write(time_data)