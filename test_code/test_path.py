import sys
import os

path = r'F:\mod'

for root, dirs, files in os.walk(path):
    for name in files:
        print(os.path.join(root, name))
    break
