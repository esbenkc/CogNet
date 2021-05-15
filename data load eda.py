#!/usr/bin/env python
# coding: utf-8

# In[24]:


import json
import hashlib, uuid
import pickle
import numpy as np
import random
import string
import os
import shutil
import subprocess
import sys
import pandas as pd
from zipfile import ZipFile
from collections import Counter
from pathlib import Path
# In[18]:


def hash_name(name):
    """ simplified version (no salt) """
    return hashlib.sha1(name.encode()).hexdigest()

def hash_with_salt(s):
    """ Hashes a string with a randomly generated salt """
    salt = uuid.uuid4().hex
    return hashlib.sha512(s + salt).hexdigest()


def check_name(hashed_name, new_name):
    return hashed_name == hash_name(new_name)


def is_a_cogsci(cogsci_hashes, new_name):
    return any(check_name(hsh, new_name) for hsh in cogsci_hashes)


def unzip_msg_files(zip_path, target_dir):
    with ZipFile(zip_path, 'r') as zipObj:
        # Get a list of all archived file names from the zip
        all_files = zipObj.namelist()
        for file in all_files:
            if file.endswith(".json"):
                zipObj.extract(file, target_dir)

                
def yield_msg_files(zip_path):
    """ Creates generator for files in zipdir """
    with ZipFile(zip_path, 'r') as zipObj:
        # Get a list of all archived file names from the zip
        all_files = zipObj.namelist()
        for file in all_files:
            with zipObj.open(file, "r") as myfile:
                try:
                    yield json.loads(json.load(myfile))
                except TypeError:
                    yield file


def count_msg_files(zip_path):
    """Counts the number of conversations in zip-file"""
    with ZipFile(zip_path, "r") as zipObj:
        return len(zipObj.namelist())
    

def read_zip_file(zip_path, file_name):
    with ZipFile(zip_path, "r") as zipObj:
        with zipObj.open(file_name, "r") as f:
            return json.load(f)
                    
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
    return Counter(participant_list).most_common(1)[0][0]


def add_reactions(msg, rel_list):
    """ Appends reaction to a reaction list (preprocessing step) """
    if "reactions" in msg.keys():
        for reaction in msg["reactions"]:
            reaction_dict = {"from": reaction, 
                             "to": msg["sender_name"], 
                             "timestamp": msg["timestamp_ms"], 
                             "rel_type": "reaction"}
            rel_list.append(reaction_dict)

            
            
def create_member_edges(group_convo, group_id):
    """ 
    Create participant --> group relations for a conversation 
    NB: These will have timestamp as nan!
    """
    return pd.DataFrame({"from": group_convo["participants"], 
                          "to": group_id, 
                          "timestamp": np.nan, 
                          "rel_type": "group"})

def process_group_messages(group_convo, group_id):
    """ Create a nice dataframe with all the messages from group chat"""
    assert group_convo["thread_type"] == "RegularGroup"
    group_msgs = pd.DataFrame(index=range(len(group_convo["messages"])), 
                              columns=["from", "to", "timestamp", "rel_type"])
    group_msgs = group_msgs.assign(to = group_id, rel_type = "msg")
    rel_list = []
    for i, msg in enumerate(group_convo["messages"]):
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
    if len(convo["participants"]) == 1:
        return None
    assert convo["thread_type"] == "Regular"
    msgs = pd.DataFrame(index=range(len(convo["messages"])), 
                        columns=["from", "to", "timestamp", "rel_type"])
    msgs = msgs.assign(rel_type = "msg")
    rel_list = []
    for i, msg in enumerate(convo["messages"]):
        if "call_duration" in msg.keys():
            continue
        msgs.loc[i, "from"] = msg["sender_name"]
        msgs.loc[i, "to"] = msg["receiver_name"]
        msgs.loc[i, "timestamp"] = msg["timestamp_ms"]
        add_reactions(msg, rel_list)
    return pd.concat([msgs.dropna(subset=["from"])
                            , pd.DataFrame(rel_list)])


def fix_dropout_dict(data_path):    
    """adds name to dropout dict as well as fixes key"""
    participant_list = []
    num_two_person = 0
    stop = False
    while not stop:
        for convo in yield_msg_files(data_path):
            is_two_person = convo["thread_type"] == "Regular"
            if is_two_person:
                num_two_person += 1
                participant_list.extend(convo["participants"])      
            if num_two_person == 2:
                stop = True
                break
        
    dropout_dict = read_zip_file(data_path, "dropout.json")
    dropout_dict["still_cogsci"] = dropout_dict.pop("is_dropout")
    dropout_dict["name"] = find_most_common(participant_list)
    return dropout_dict


def process_person(data_path):
    """
    processes all conversations from one person 
    (inputs path to zip-file)
    """
    df_list = []
    for convo in yield_msg_files(data_path):
        if type(convo) == str:
            continue
        elif convo["thread_type"] == "Regular":
            df_list.append(process_msgs(convo))
        elif convo["thread_type"] == "RegularGroup":
            df_list.append(process_group_edges(convo))
        else:
            print(convo["thread_type"])
    try:
        return pd.concat(df_list)
    except ValueError:
        return None


def create_dropout_df(data_paths):
    """Full pipeline for creating df with from the dropout.json """
    dropout_list = [None for _ in range(len(data_paths))]
    for i, data_path in enumerate(data_paths):
        dropout_list[i] = fix_dropout_dict(data_path)
    return pd.DataFrame(dropout_list)

def anonymize_filename(data_path):
    """ Removes the actual name from the filename (weird google thing)"""
    problem_part = data_path.name.find(" -")
    new_name = data_path.parent / Path(data_path.name[:problem_part] + ".zip")
    data_path.rename(new_name)
    
def anonymize_folder(data_folder):
    """Anonymizes all filenames in folder (from google thing)"""
    problem_paths = data_folder.glob("*-*.zip")
    for file in problem_paths:
        anonymize_filename(file)
        
def find_unique_ids(cogscis, full_df):
    """ Returns unique ids (groups and people) for filtering"""
    unique_people = pd.Series(cogscis).unique()
    unique_groups = full_df.loc[full_df["rel_type"] == "group", "to"].unique()
    return set(np.concatenate((unique_people, unique_groups)))


def load_cog_hash():
    """Loads the pickled cogsci hash file (should be in parent dir)"""
    with open(Path("../cogsci19_2.pkl"), "rb") as cog:
        return pickle.load(cog)
    
    
def find_non_cogs(full_df):
    """Finds ids not recognized by the cogsci hash """
    cogs = load_cog_hash()
    non_cog_df = full_df[~full_df["from"].isin(cogs)]
    non_cog_groups = non_cog_df.loc[non_cog_df["rel_type"] == "group", "to"].unique()
    return set(np.concatenate((non_cog_df["from"], non_cog_groups)))


def remove_non_cogs(full_df):
    """ Remove all people not recognized by their cogsci hash"""
    all_non_cogs = find_non_cogs(full_df)
    non_cog_filter = ~(unique_master["to"].isin(all_non_cogs) | unique_master["from"].isin(all_non_cogs))
    return full_df[non_cog_filter]


def filter_consent(full_df, dropout_df):
    """ Filters so only people we have data / consent from """
    unique_ids = find_unique_ids(dropout_df, full_df)
    consenting_filter = full_df["from"].isin(unique_ids) & full_df["to"].isin(unique_ids)
    return full_df[consenting_filter]

def calc_group_sizes(df):
    """ Finds the size of each groupchat in the df """
    return df[df["rel_type"] == "group"].groupby("to")["from"].agg("count")


def find_hex(s):
    """ Checks whether names are valid hashes """
    try:
        int(s, 16)
        return True
    except ValueError:
        return False
    

def add_hash_check(df):
    """ Adds columns to the df checking which names are hashed """
    return df.assign(from_hex = df["from"].apply(lambda x: find_hex(x)),
                     to_hex = df["to"].apply(lambda x: find_hex(x)))

def hash_plaintext(df):
    """ hash names that haven't been hashed"""
    df.loc[~df["from_hex"], "from"] = df.loc[~df["from_hex"], "from"].apply(lambda x: hash_name(x))
    df.loc[~df["to_hex"], "to"] = df.loc[~df["to_hex"], "to"].apply(lambda x: hash_name(x))
    

def fix_vero(df):
    """ Fixes weird vero bug """
    df.loc[df["from"] == "Verus Juhasz", "from"] = hash_name("Verus Juhasz")
    df.loc[df["to"] == "Verus Juhasz", "to"] = hash_name("Verus Juhasz")


def calculate_group_weights(group_sizes):
    """ add weights to the convo depending on size """
    return 1 / (group_sizes-1)


def create_random_ids(id_tuple):
    """Inputs a tuple of pd.Series with ids and outputs a dict mapping them to new randomly generated ids"""
    unique_ids = set(np.concatenate(id_tuple))
    random_id = np.random.choice(range(len(unique_ids)), size=len(unique_ids), replace=False)
    return {k: v for k, v in zip(list(unique_ids), random_id)}

def repeat_data(weighted_data, weight_col="weight"):
    """ Repeat each row n times where n is described by the weight_col"""
    return pd.DataFrame(weighted_data.values.repeat(weighted_data[weight_col], axis=0), 
                        columns=weighted_data.columns)

def group_weight_pipe(df):
    """ Creates a df with index of group ids and a column with msg weights + series with group sizes"""
    group_sizes = calc_group_sizes(consent_df)
    return pd.DataFrame(group_sizes).assign(weight = calculate_group_weights(group_sizes))["weight"], group_sizes

def add_group_weights(df):
    """ calculates and joins the group weights to the original dataframe """
    group_weights, group_sizes = group_weight_pipe(df)
    merged_msgs = pd.merge(df, group_weights, how="left", left_on="to", right_index=True)
    merged_msgs["weight"] = merged_msgs["weight"].fillna(np.floor(np.log2(group_sizes.max())))
    return merged_msgs

def merge_group_members(df, weighted_group):
    """ Joins the members of a group to the group_id, creating a much longer dataframe """
    groups = df.loc[df["rel_type"] == "group", ["from", "to"]]
    return pd.merge(weighted_group[weighted_group["rel_type"] != "group"], groups, how="left", on="to")

def clean_merged_group(group_merge):
    """ Cleans up the merged group dataframe, renaming and dropping nans"""
    return group_merge.assign(to_person=group_merge["from_y"].combine_first(group_merge["to"]))[["from_x", "to_person", "timestamp", "rel_type", "weight"]]            .rename({"from_x": "from", "to_person":"to"}, axis=1)            .replace([np.inf, -np.inf], np.nan)            .dropna()

def pathpy_pipeline(df):
    """ Full pipeline for getting dataframe in Pathpy friendly format"""
    weighted_group = add_group_weights(df)
    merged_group = merge_group_members(df, weighted_group)
    final_merge = clean_merged_group(merged_group)
    repeated_data = repeat_data(final_merge)
    return repeated_data[["from", "to", "timestamp"]]


def tidy_pipeline(df):
    """ Full pipeline for tidyverse data """
    weighted_group = add_group_weights(df)
    merged_group = merge_group_members(df, weighted_group)
    final_merge = clean_merged_group(merged_group)
    return final_merge[["from", "to", "timestamp", "weight"]]
    


# In[3]:


DATA_DIR = Path("./data")
anonymize_folder(DATA_DIR)
data_paths = list(DATA_DIR.glob("*.zip"))


# In[4]:


dropout_df = create_dropout_df(data_paths)


# In[5]:


data_list = [None for _ in range(len(data_paths))]


# In[11]:


for i, data_path in enumerate(data_paths):
    if data_list[i] is None:
        print(f"processing person {i+1} out of {len(data_paths)}...")
        try:
            data_list[i] = process_person(data_path)
        except FileNotFoundError:
            print("no file here")
            continue
print("all done!")


# In[5]:


replacement_dict = {hash_name("Lasse Hyldig Hansen"): [hash_name("Lasse Hansen")],
                    hash_name("Pernille HÃ¸jlund Brams"): [hash_name("Pernille Brams")],
                    hash_name("Tobias GrÃ¸nhÃ¸i Hansen"): [hash_name("Tobias Hansen")]}


# In[12]:


master_df = pd.concat(data_list)
unique_master = master_df.drop_duplicates()
unique_master.to_csv(Path("../full_mess.csv"), index=False)


# In[6]:


unique_master = pd.read_csv(Path("../full_mess.csv"))
unique_master = unique_master.replace(replacement_dict)
fix_vero(unique_master)


# In[7]:


cog_df = remove_non_cogs(unique_master)
cog_df.to_csv(Path("../cog_raw.csv"), index=False)
cog_df = pd.read_csv(Path("../cog_raw.csv"))
consent_df = filter_consent(cog_df, dropout_df["name"])


# In[8]:


random_replacement_dict = create_random_ids((consent_df["from"], consent_df["to"], dropout_df["name"]))
consent_df.replace(random_replacement_dict, inplace=True)
dropout_df.replace(random_replacement_dict, inplace=True)
dropout_df.to_csv("dropout_dat.csv", index=False)

# In[10]:


consent_df.to_csv("raw_consensual.csv", index=False)


# In[6]:


consent_df = pd.read_csv("raw_consensual.csv")


# In[36]:


tidy_df = tidy_pipeline(consent_df)
tidy_df.to_csv("tidy_data.csv", index=False)

#cogs.add(hash_name("Cecilie Stilling Pedersen"))
#cogs.add(hash_name("Alba Herrero"))
#with open(Path("../cogsci19_2.pkl"), "wb") as f:
#    pickle.dump(cogs, f)


# In[ ]:


#pathpy_df = pathpy_pipeline(consent_df)


