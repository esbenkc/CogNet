# -*- coding: utf-8 -*-
"""
Created on Sun May 31 12:27:01 2020

@author: jhr
"""
import json
import hashlib
import pickle
import random
import string
import shutil
import subprocess
import sys
from zipfile import ZipFile
from pathlib import Path
try:
    from flashtext import KeywordProcessor
except ModuleNotFoundError:
    print("installing flashtext...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "flashtext"])
    print("done!")
    from flashtext import KeywordProcessor
    

def flatten(l):
    return [item for sublist in l for item in sublist]

    
def read_json(file_path):
    with open(file_path, encoding="utf-8") as file: 
        return json.load(file)
    
def pickle_list(lst, file_name):
    with open(file_name, "wb") as f:
        pickle.dump(lst, f)
        
def read_pickle(file_path):
    with open(file_path, "rb") as f:
        return pickle.load(f)
    
def find_all_messages(main_dir):
    """ returns iterator of all message paths """
    return main_dir.rglob("message_*.json")


def hash_name(name):
    """ simplified version (no salt) """
    return hashlib.sha1(name.encode()).hexdigest()


def check_name(hashed_name, new_name):
    return hashed_name == hash_name(new_name)


def is_a_cogsci(cogsci_hashes, new_name):
    return any(check_name(hsh, new_name) for hsh in cogsci_hashes)


def extract_participants(convo):
    return [participant["name"] for participant in convo["participants"]]


def is_cog_convo(participants, cog_hashes):
    """ Checks whether all participants in convo are cogsci19 """
    return any(check_name(hsh, name) for hsh in cog_hashes for name in participants)


def get_other_participant(lst, part):
    return next(filter(lambda x: x != part,  lst))


def format_subscribe(sub_msg):
    keep_keys = ["type", "timestamp_ms", "users"]
    return {k: v for k, v in sub_msg.items() if k in keep_keys}


def format_message(msg, participants):
    keep_keys = ["reactions", "sender_name", "timestamp_ms"]
    new_msg = {k: v for k, v in msg.items() if k in keep_keys}
    try:
        new_msg["reactions"] = format_reaction(new_msg["reactions"])
    except KeyError:
        pass
    if len(participants) == 2:
        new_msg["receiver_name"] = get_other_participant(participants, msg["sender_name"])
    return new_msg


def format_call(call, participants):
    assert call["type"] == "Call"
    new_call = call.copy()
    new_call.pop("content", None)
    if len(participants) == 2:
        new_call["receiver_name"] = get_other_participant(participants, call["sender_name"])
    return new_call
    

def format_reaction(reactions):
    """ simply removes the reaction leaving only the sender """
    return [reaction["actor"] for reaction in reactions]


def format_share(msg, participants):
    new_msg = format_message(msg, participants)
    try:
        new_msg.pop("share")
    except KeyError:
        pass
    return new_msg


def process_message(msg, participants):
    msg_type = msg["type"]
    if msg_type == "Generic":
        return format_message(msg, participants)
    elif msg_type == "Call":
        return format_call(msg, participants)
    elif msg_type == "Share":
        return format_share(msg, participants)
    elif msg_type == "Subscribe":
        pass
    elif msg_type == "Unsubscribe":
        pass
    else:
        print(msg)
        raise AssertionError

        
def create_hash_dict(participants):
    return {hash_name(name): [name] for name in participants}
        

def init_hashifier(participants):
    hash_dict = create_hash_dict(participants)
    hashifier = KeywordProcessor()
    hashifier.add_keywords_from_dict(hash_dict)
    return hashifier


def stringify_dict(dct):
    return json.dumps(dct, ensure_ascii=False)


def anonymize_stuff(processed_msgs, participants):
    hashifier = init_hashifier(participants)
    convo_string = stringify_dict(processed_msgs)
    anon_string = hashifier.replace_keywords(convo_string)
    return anon_string
    
def get_sub_users(sub_list):
    nested_list = [[user["name"] for user in subs["users"]] for subs in sub_list]
    return flatten(nested_list)


def get_all_participants(participants, subscriptions):
    """ get all participants including people who have left (host host Anne-Line!) """
    sub_participants = get_sub_users(subscriptions)
    return set(participants + sub_participants)


def process_convo(convo):
    participants = extract_participants(convo)
    if not is_cog_convo(participants, COG_HASHES):
        return None
    processed_msgs = []
    processed_subscriptions = []
    for msg in convo["messages"]:
        if msg["type"] == "Subscribe" or msg["type"] == "Unsubscribe":
            processed_subscriptions.append(format_subscribe(msg))
        else:
            processed_msgs.append(process_message(msg, participants))
    convo["messages"] = processed_msgs
    convo["participants"] = participants
    convo["subscriptions"] = processed_subscriptions
    convo.pop("title", None)
    convo.pop("is_still_participant", None)
    convo.pop("thread_path", None)
    # Use all participants for this stuff
    all_participants = get_all_participants(participants, processed_subscriptions)
    anon_convo = anonymize_stuff(convo, all_participants)
    return anon_convo


def random_long_id(N=32):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=N))


def write_json_data(data):
    file_name = random_long_id() + ".json"
    file_path = Path("./data") / file_name
    with open(file_path, "w") as f:
        json.dump(data, f)


def anon_pipeline(convo_file):
    convo = read_json(convo_file)
    anon_convo = process_convo(convo)
    if anon_convo is not None:
        write_json_data(anon_convo)

        
def create_dir(path):
    TEMP_DATA = Path(path)
    try:
        TEMP_DATA.mkdir()
    except FileExistsError:
        pass
    return TEMP_DATA


def unzip_msg_files(zip_path, target_dir):
    with ZipFile(zip_path, 'r') as zipObj:
        # Get a list of all archived file names from the zip
        all_files = zipObj.namelist()
        for file in all_files:
            if file.endswith(".json"):
                zipObj.extract(file, target_dir)

is_dropout = input("""
Hello there! Thanks for helping us gather this awesome data :)) 
We'll do everything we can to ensure that your privacy is conserved.
All the processing is done automagically (you can check out the .zip-file afterwards)
We only have one question: Are you still attending the Cognitive Science Program? (If yes enter "1", if no enter "0")
""")



print("that's all! Now the program will do some magic :))")
print("setting up directories...")
create_dir("./data")    
hash_path = Path("cogsci19.pkl")
COG_HASHES = read_pickle(hash_path)
zip_paths = list(Path(".").glob("facebook*.zip"))
temp_data = create_dir("./temp")

print("writing activity-status...")
with open(Path("./data/dropout.json"), "w") as f:	
	json.dump({"is_dropout": is_dropout}, f)

print("finding messages in zip-file...")
if len(zip_paths) > 0:
    for zip_path in zip_paths:
        unzip_msg_files(zip_path, temp_data)
    print("done!")
    print("anonymizing the data....")
    for convo_file in find_all_messages(temp_data):
        anon_pipeline(convo_file)
    print("done!")

else:
    print("Mac has done the job for us!")
    print("anonymizing the data....")
    for convo_file in find_all_messages(Path("./messages")):
        anon_pipeline(convo_file)
    print("done!")



# Writing data to zip
print("write data to zip!")
shutil.make_archive(f"all_the_data_{random_long_id(N=8)}", 'zip', "data")
print("cleaning up directories...")
shutil.rmtree("data")
shutil.rmtree(temp_data)   
print("all done!")