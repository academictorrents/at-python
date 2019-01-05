

import academictorrents as at
import pickle
import gzip
import sys
import os
import time

print("Libraries imported, about to start a download")

filename = at.get("b79869ca12787166de88311ca1f28e3ebec12dec")

print("About to open the file")

mnist = gzip.open(filename, 'rb')
train_set, validation_set, test_set = pickle.load(mnist)
mnist.close()
