# usage: python3 bdfr2text.py INPUT_DIR OUTPUT_DIR
# INPUT_DIR is the output dir of bdfr
# OUTPUT_DIR is emptied before every run

import json
import os
import sys
import time
from io import StringIO
from pathlib import Path

YAML_INSTALLED = False
try:
    import yaml
    YAML_INSTALLED = True
except ImportError:
    pass

INDENT_SPACES = 6
# add URLs for each comment (if False, only short IDs are added)
ADD_URLS = True
# add timestamps for each comment (if False, the age of each comment is added)
ADD_TIMESTAMPS = False

# I didn't want to import shutil just for rmtree(), so I just re-wrote it :)
# raises FileNotFoundError
def rmtree(path):
    # ensure path is a Path
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError
    # get all files/dirs in this dir (non-recursive)
    paths_to_rm = list(path.glob('*'))
    for p in paths_to_rm:
        if p.is_file():
            #print(f'FILE: rm {p}')
            os.remove(p)
        else: # dir
            #print(f'DIR: rmtree({p})')
            rmtree(p)
            #print(f'DIR DONE: rmdir({p})')
    os.rmdir(path)

# generates pretty time diff string from two UTC timestamps
def pretty_time_diff(start, end):
    diff_in_secs = end - start

    SECOND = 1
    MINUTE = 60
    HOUR = MINUTE * 60
    DAY = HOUR * 24
    MONTH = DAY * 30
    YEAR = DAY * 365

    # start at highest and work down
    units_in_secs = [YEAR, MONTH, DAY, HOUR, MINUTE, SECOND]
    unit_names = ['yr', 'mo', 'day', 'hr', 'min', 'sec']
    i = 0
    while i < len(units_in_secs):
        diff_in_unit = int(diff_in_secs / units_in_secs[i])
        if diff_in_unit == 1:
            return f'{diff_in_unit} {unit_names[i]}'
        if diff_in_unit > 1:
            return f'{diff_in_unit} {unit_names[i]}s'
        i = i + 1
    return 'now'

# p is a post or comment
# generates string of metadata of the post/comment in the format:
# "[ pts | author | date | # comments (if post) | id ]"
def metadata_str(p):
    # True if post, False if comment
    is_post = 'title' in p
    score = p['score']
    author = p['author']
    timestamp = int(p['created_utc'])
    if ADD_TIMESTAMPS:
        # use timestamp
        date = timestamp
    else:
        # use age
        now = time.time()
        date = pretty_time_diff(timestamp, now)
    if ADD_URLS:
        if is_post:
            r_id = f'https://reddit.com/comments/{p["id"]}'
        else:
            r_id = f'https://reddit.com/comments/{p["submission"]}//{p["id"]}'
    else:
        r_id = p['id']
    if is_post:
        metadata = (f'[ {score} | {author} | {date} | {p["num_comments"]} '
                    f'comments | {r_id} ]')
    else:
        metadata = f'[ {score} | {author} | {date} | {r_id} ]'
    return metadata

def post_to_text(p):
    out = StringIO()

    if p['selftext'] != '':
        body = p['selftext'].strip()
    else:
        body = p['url']

    metadata = metadata_str(p)
    p_str = f'{metadata}' + '\n\n' + p['title'] + '\n' + body + '\n---\n\n'
    out.write(p_str)

    def comments_to_text(comments, tree_depth):
        padding = ' ' * (INDENT_SPACES * tree_depth)
        for c in comments:
            metadata = metadata_str(c)
            body = c['body'].strip()
            c_str = padding + metadata + '\n\n' + body + '\n---'
            c_str = c_str.replace('\n', '\n' + padding)
            c_str += '\n\n'

            out.write(c_str)

            if len(c['replies']) > 0:
                comments_to_text(c['replies'], tree_depth + 1)
    
    comments_to_text(p['comments'], 0)
    out_str = out.getvalue()
    out.close()
    return out_str

def main():
    if len(sys.argv) != 3:
        sys.exit('invalid arguments')

    in_dir = Path(sys.argv[1])
    out_dir = Path(sys.argv[2])
    print(f'output dir: {out_dir}')

    paths = list(in_dir.glob('*'))
    if len(paths) == 0:
        sys.exit(f'input dir is empty or does not exist: {in_dir}')

    # create fresh output dir
    try:
        rmtree(out_dir)
    except FileNotFoundError:
        pass
    os.makedirs(out_dir)

    print(f'scanning for .json/.yml files in {in_dir}...')
    for in_fp in paths:
        with open(in_fp, 'rb') as in_f:
            if in_fp.suffix == '.json':
                post = json.loads(in_f.read().decode('utf-8'))
                print(f'converting {in_fp}...')
            elif in_fp.suffix == '.yaml':
                if not YAML_INSTALLED:
                    print(f'PyYAML not installed: {in_fp}, skipping...')
                    continue
                post = yaml.safe_load(in_f)
                print(f'converting {in_fp}...')
            elif in_fp.suffix == '.txt':
                continue
            else:
                print(f'unrecognized file: {in_fp}, skipping...')
                continue
        out_text = post_to_text(post)
        out_fp = out_dir / f'{in_fp.stem}_{in_fp.suffix[1:]}.txt'
        with open(out_fp, 'w', encoding='utf-8') as of:
            of.write(out_text)

if __name__ == '__main__':
    main()
