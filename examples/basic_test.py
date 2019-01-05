

import academictorrents as at
import pickle
import gzip
import sys
import os
import time
import numpy as np

print("Libraries imported, about to start a download")

filename = at.get("55a8925a8d546b9ca47d309ab438b91f7959e77f")

print("About to open the file")

mnist = gzip.open(filename, 'rb')
train_set, validation_set, test_set = pickle.load(mnist)
mnist.close()
