ii=(10 100 500 1000 3000 5000 10000)

for i in ${ii[@]}
do 
  echo === Experiment with ${i} ===
  echo === Generator start ===
  python generator_fm.py ${i}
  echo === Verifier start ===
  python test_static.py -t dataset/fm/topo/fm_${i}.txt -a dataset/fm/bgp/announcement_${i}.json -p dataset/fm/bgp/pref_${i}.json
done