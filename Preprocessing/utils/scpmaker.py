import sys
import os

# sys.argv[1]: plp file paths
# sys.argv[2]: output plp scp file with time label

plp_train_paths = sys.argv[1]
train_scp = sys.argv[2]
with open(train_scp, 'w') as f2:
    with open(plp_train_paths) as f1:
        for line in f1:
            line = line.strip()

            a = os.popen("/scratch/bdda/ssliu/Projects/UASPEECH/Tools_V1.1/bin/HList -e 0 -h " + line + "| head | egrep 'Num Samples'|awk '{print $3}'").read()
            a = a.strip()
            a1 = int(a)-1
            a2 = str(a1)
            a1 = str(a1).zfill(7)

            logic = line.split('/')[9]
            logic1 = logic.split('.')[0]
            logic = logic1+'_0000000_'+ a1 + '.plp'

            output = logic + '=' + line + '[0,' + a2 + ']\n'
            #print(output)
            f2.write(output)

