import academictorrents as at
import sys
import argparse

parser = argparse.ArgumentParser(description='AT Simple command line tool')
parser.add_argument('-hash', type=str, nargs='?', required=True, help='Hash of torrent to download')
parser.add_argument('-name', type=str, nargs='?', default=None, help='Name of subfolder for file')
parser.add_argument('-datastore', type=str, nargs='?', default=".", help='Location which to place the files')
args = parser.parse_args()

filename = at.get(args.hash, datastore=args.datastore, name=args.name)

print("Done")
