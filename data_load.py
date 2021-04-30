# IMPORT LIBRARIES
import json
import hashlib
import pickle
import numpy as np
import random
import string
import os
import shutil
import subprocess
import sys
import glob
import pandas as pd
from zipfile import ZipFile
from collections import Counter
from pathlib import Path

from pandas.core.frame import DataFrame

# DEFINE FUNCTIONS

def unzip_msg_files(zip_path, target_dir):
    with ZipFile(zip_path, 'r') as zipObj:
        # Get a list of all archived file names from the zip
        all_files = zipObj.namelist()
        for file in all_files:
            if file.endswith(".json"):
                zipObj.extract(file, target_dir)
                
def read_json(file):
    with open(file, "r") as f:
        return json.load(f)
    
def read_convo(file):
    """reads conversation json file to dict """
    return json.loads(read_json(file))

def hash_name(name):
    """ simplified version (no salt) """
    return hashlib.sha1(name.encode()).hexdigest()

def create_group_id(groupchat):
    """creates a group id based on participant names"""
    participant_string = "".join(sorted(groupchat["participants"]))
    return hash_name(participant_string)

def find_most_common(participant_list):
    """finds most common element in list """
    try:
        return Counter(participant_list).most_common(1)[0][0]
    except:
        return "No items in input array"


def fix_dropout_dict(data_path):    
    """adds name to dropout dict as well as fixes keyv"""
    file_generator = Path(data_path).glob("*.json")
    data_files = [file for file in file_generator if file.name != "dropout.json"]


    participant_list = []
    for file in data_files:
        temp_dict = json.loads(read_json(file))
        participant_list.extend(temp_dict["participants"])

    if (Path(data_path) / "dropout.json").exists():
        dropout_dict = read_json(Path(data_path) / "dropout.json")
        dropout_dict["still_cogsci"] = dropout_dict.pop("is_dropout")
        dropout_dict["name"] = find_most_common(participant_list)
    else:
        dropout_dict = {"still_cogsci": 1, "name":"No dropout file available"}
    return dropout_dict

def add_reactions(msg, rel_list):
    """ Appends reaction to a reaction list (preprocessing step) """
    if "reactions" in msg.keys():
        for reaction in msg["reactions"]:
            reaction_dict = {"from": reaction, 
                             "to": msg["sender_name"], 
                             "timestamp": msg["timestamp_ms"], 
                             "rel_type": "reaction"}
            rel_list = rel_list.append(reaction_dict, ignore_index=True)
    return rel_list

            
            
def create_member_edges(group_convo, group_id):
    """ Create participant --> group relations for a conversation """
    return pd.DataFrame({"from": group_convo["participants"], 
                          "to": group_id, 
                          "timestamp": np.nan, 
                          "rel_type": "group"})

def process_group_messages(group_convo, group_id):
    """ Create a nice dataframe with all the messages from group chat"""
    group_msgs = pd.DataFrame(index=range(len(test_group["messages"])), 
                              columns=["from", "to", "timestamp", "rel_type"])
    group_msgs = group_msgs.assign(to = group_id, rel_type = "msg")
    rel_list = []
    for i, msg in enumerate(test_group["messages"]):
        group_msgs.loc[i, "from"] = msg["sender_name"]
        group_msgs.loc[i, "timestamp"] = msg["timestamp_ms"]
        add_reactions(msg, rel_list)
    return pd.concat([group_msgs, pd.DataFrame(rel_list)])

def process_group_edges(group_convo):
    """ Full pipeline for processing group chats """
    group_id = create_group_id(group_convo)
    group_msgs = process_group_messages(group_convo, group_id)
    group_members = create_member_edges(group_convo, group_id)
    return pd.concat([group_msgs, group_members]).reset_index(drop=True)


def process_msgs(convo):
    """ Processes messages and returns a nice dataframe :)) """
    msgs = pd.DataFrame(index=range(len(test_chat["messages"])), 
                        columns=["from", "to", "timestamp", "rel_type"])
    msgs = msgs.assign(rel_type = "msg")
    rel_list
    for i, msg in enumerate(test_chat["messages"]):
        if "call_duration" in msg.keys():
            continue
        msgs.loc[i, "from"] = msg["sender_name"]
        msgs.loc[i, "to"] = msg["receiver_name"]
        msgs.loc[i, "timestamp"] = msg["timestamp_ms"]
        add_reactions(msg, rel_list)
    return pd.concat([msgs.dropna(subset=["from"])
                            , pd.DataFrame(rel_list)])

# RUN DATA PIPELINE
data_dir = Path("./data")

# Unzip data files
data_files = data_dir.glob("*.zip")
for file in data_files:
    data_target = data_dir / f"{file.name[:-4]}_unzipped"
    unzip_msg_files(file, data_target)


# Fix dropout dicts for each unzipped directory (some are missing)
unzipped_dirs = data_dir.glob("./*unzipped/")
dropout_dicts = [fix_dropout_dict(dat_dir) for dat_dir in unzipped_dirs]

# Save a single data_path
data_path = list(data_dir.glob("./*unzipped/"))[6]
dropout_dict = fix_dropout_dict(data_path)

# Running pipeline for single path
all_convos = list(glob.glob("./data/*_unzipped/*[0-9A-Z][0-9A-Z][0-9A-Z][0-9A-Z][0-9A-Z][0-9A-Z][0-9A-Z][0-9A-Z].json"))
# all_convos_in_user = list(glob.glob('./data/all_the_data_6EQ02QNL_unzipped/*{8,}.json', recursive=True))
all_msgs = pd.DataFrame(columns=["from", "to", "timestamp", "rel_type"])

# Go through all conversations in test user
for file in all_convos:
    current_chat = read_convo(file)
    if current_chat["thread_type"] == "Regular":
        msgs = pd.DataFrame(index=range(len(current_chat["messages"])), 
                            columns=["from", "to", "timestamp", "rel_type"])
        msgs = msgs.assign(rel_type = "msg")
        rel_list = pd.DataFrame(columns=["from", "to", "timestamp", "rel_type"])
        for i, msg in enumerate(current_chat["messages"]):
            # Ignore calls
            if "call_duration" in msg.keys():
                continue
            msgs.loc[i, "from"] = msg["sender_name"]
            try:
                msgs.loc[i, "to"] = msg["receiver_name"]
            except:
                msgs.loc[i, "to"] = None
            msgs.loc[i, "timestamp"] = msg["timestamp_ms"]
            add_reactions(msg, rel_list)
        all_msgs = all_msgs.append(pd.concat([msgs.dropna(subset=["from"]),
                                                    pd.DataFrame(rel_list)]))

all_msgs.to_csv("all_messages.csv")
