ss=(1221 1239 1755 3257 3967 6461)  

for s in ${ss[@]}                       
do
    for ((i=0; i<5; i++))
    do
    python test_ospf.py -t dataset/ospf/isp_${s}.txt
    done
done