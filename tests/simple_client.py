import academictorrents as at
import sys
import argparse

parser = argparse.ArgumentParser(description='AT Simple command line tool')
parser.add_argument('-hash', type=str, nargs='?',default="sq", help='Hash of torrent to download')
args = parser.parse_args()

filename = at.get(args.hash)

print("Done")
