ii=(10 100 500 1000 3000 5000 10000)

for i in ${ii[@]}
do 
  echo === Experiment with ${i} ===
  echo === Generator start ===
  python generator_fm.py ${i}
  echo === Verifier start ===
  python test.py -t fm/topo/fm_${i}.txt -a fm/bgp/announcement_${i}.json -p fm/bgp/pref_${i}.json
done