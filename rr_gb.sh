rr=(10 50 100 200)
cc=(3 10 30 50)

for r in ${rr[@]}
do 
    for c in ${cc[@]}
    do 
        python generator_rr.py -r ${r} -p 2 -c ${c}
        for ((i=0; i<3; i++))
        do
            python rr_gb.py -t dataset/bgp/topo/rr_`python -c "print(${r}*(${c}+2))"`.txt \
                -a dataset/bgp/announcements/announcements_`python -c "print(${r}*(${c}+2))"`.json \
                -c dataset/bgp/conf/conf_`python -c "print(${r}*(${c}+2))"`.json \
                -n good -p 5000
            python rr_gb.py -t dataset/bgp/topo/rr_`python -c "print(${r}*(${c}+2))"`.txt \
                -a dataset/bgp/announcements/announcements_`python -c "print(${r}*(${c}+2))"`.json \
                -c dataset/bgp/conf/conf_`python -c "print(${r}*(${c}+2))"`.json \
                -n bad -p 1
        done
    done 
done