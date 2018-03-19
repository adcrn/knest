"""
Module to hold all global variables used in `main.py`
"""

# completion indicators of process checkpoints
blur_step = 0
bird_step = 0

# classification model variables
load = 0
model = None

# path information variables
dir_path = ""
des_path = ""
num_files = 0

# reusuable variables for use in real-time display
first_pass = 0
index = 0
files = []

# holds image data of entire process
images = {}

# image comparison variable
comp = 0
std = ''
std_hash = None
count = 0
