import time
import numpy as np
from sklearn.model_selection import train_test_split
import pandas as pd
import os
import sys




def write_csv(write_path, write_data):
	if os.path.exists(write_path):
		fd = open(write_path, 'a')
		np.savetxt(write_path, write_data, fmt="%d", delimiter = ",")
		fd.close()
	else:
		fd = open(write_path, 'w')
		np.savetxt(write_path, write_data, fmt="%d", delimiter = ",")
		fd.close()
	
	return 0


def process(csv_source,ts,train_out,test_out):
	train_data, test_data = train_test_split(csv_source, test_size = ts, random_state = 0)
	
	write_csv(train_out, train_data)
	write_csv(test_out, test_data)

	return 0
		



def main(in_file,ts,train_out,test_out):
	for chunk in pd.read_csv(in_file, chunksize=1000000000):
		process(chunk,ts,train_out,test_out)
if __name__ == '__main__':
	start_time = time.time()
	# in_file="/data6/laowozhen10.8/sample/csv/laowozhen_all.csv"
	# train_out = "/data6/laowozhen10.8/sample/csv/train.csv"
	# test_out = "/data6/laowozhen10.8/sample/csv/test.csv"
	# main(in_file,train_out,test_out)
	main(sys.argv[1], float(sys.argv[2]), sys.argv[3],sys.argv[4])
	end_time=time.time()
	print("time: %.2f min." % ((end_time - start_time) / 60))
