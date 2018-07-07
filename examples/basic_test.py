
print "About to import the library"

import academictorrents as at




print "About to start a download"

filename = at.get("323a0048d87ca79b68f12a6350a57776b6a3b7fb")



print "About to open the file"

import cPickle, gzip
import sys, os, time
import numpy as np

mnist = gzip.open(filename, 'rb')
train_set, validation_set, test_set = cPickle.load(mnist)
mnist.close()
