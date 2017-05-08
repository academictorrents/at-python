# Academic Torrents Python and R APIs (Under Development)

[![Build Status](https://travis-ci.org/AcademicTorrents/python-r-api.svg?branch=master)](https://travis-ci.org/AcademicTorrents/python-r-api)
[![Build status](https://ci.appveyor.com/api/projects/status/0jgof5la8u4nvfv0/branch/master?svg=true)](https://ci.appveyor.com/project/JonathanNogueira/python-r-api/branch/master)
[![codecov](https://codecov.io/gh/AcademicTorrents/python-r-api/branch/master/graph/badge.svg)](https://codecov.io/gh/AcademicTorrents/python-r-api)

The idea of this API is to allow scripts to download datasets easily. The library should be available on every system and allow a simple interface to download small and large files.



```
import academictorrents as at

# Download the data (or verify existing data)
filename = at.get("323a0048d87ca79b68f12a6350a57776b6a3b7fb")

# Then work with the data
import cPickle, gzip
import sys, os, time
import numpy as np

mnist = gzip.open(filename, 'rb')
train_set, validation_set, test_set = cPickle.load(mnist)
mnist.close()
```
