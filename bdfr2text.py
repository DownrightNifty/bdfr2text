import argparse
import json
import time
from io import StringIO
from pathlib import Path

YAML_INSTALLED = False
try:
    import yaml
    YAML_INSTALLED = True
except ImportError:
    pass

OPEN_DELIM = ('[', '&lsqb;')
CLOSE_DELIM = (']', '&rsqb;')
SEPARATOR = ('---', '&#x2504;')

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
            p.unlink()
        else: # dir
            rmtree(p)
    path.rmdir()

# creates a new dir (dest) with the same dir structure of src (but without the
# files)
# raises FileNotFoundError, FileExistsError
def cp_dir_structure(src, dest):
    src, dest = Path(src), Path(dest)
    if not src.exists():
        raise FileNotFoundError
    dest.mkdir(parents=True)

    # dest should be a blank directory every call
    def _cp_dir_structure(src, dest, lvl):
        src_dirs = [p for p in src.glob('*') if p.is_dir()]
        for p in src_dirs:
            (dest / p.name).mkdir()
            _cp_dir_structure(p, dest / p.name, lvl + 1)
    
    _cp_dir_structure(src, dest, 1)

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
    units_in_secs = (YEAR, MONTH, DAY, HOUR, MINUTE, SECOND)
    unit_names = ('yr', 'mo', 'day', 'hr', 'min', 'sec')
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
def metadata_str(p, add_urls, add_timestamps, parsable):
    # True if post, False if comment
    is_post = 'title' in p
    score = p['score']
    author = p['author']
    timestamp = int(p['created_utc'])
    if add_timestamps:
        # use timestamp
        date = timestamp
    else:
        # use age
        now = time.time()
        date = pretty_time_diff(timestamp, now)
    if add_urls:
        if is_post:
            r_id = f'http://reddit.com/comments/{p["id"]}'
        else:
            r_id = f'http://reddit.com/comments/{p["submission"]}//{p["id"]}'
    else:
        r_id = p['id']
    if is_post:
        delims = ''
        if parsable:
            delims += ' | '
            for i, d in enumerate((OPEN_DELIM, CLOSE_DELIM, SEPARATOR)):
                delims += d[1]
                if i != 2:
                    delims += ' '
        metadata = (f'{OPEN_DELIM[0]} {score} | {author} | {date} | '
                    f'{p["num_comments"]} comments | {r_id}{delims} '
                    f'{CLOSE_DELIM[0]}')
    else:
        metadata = (f'{OPEN_DELIM[0]} {score} | {author} | {date} | {r_id} '
                    f'{CLOSE_DELIM[0]}')
    return metadata

# p is a post or comment
def generate_body(p, parsable):
    is_post = 'title' in p
    if is_post:
        if p['selftext'] != '':
            body = p['selftext'].strip()
        else:
            body = p['url']
    else:
        body = p['body'].strip()

    if parsable:
        for d in (OPEN_DELIM, CLOSE_DELIM, SEPARATOR):
            if d[1] in body:
                # info will be lost
                body = body.replace(d[1], '')
            body = body.replace(d[0], d[1])
    
    return body

def post_to_text(p, indent, add_urls, add_timestamps, parsable):
    out = StringIO()

    body = generate_body(p, parsable)
    metadata = metadata_str(p, add_urls, add_timestamps, parsable)
    p_str = (f'{metadata}' + '\n\n' + p['title'] + '\n' + body + '\n'
             f'{SEPARATOR[0]}\n\n')
    out.write(p_str)

    def comments_to_text(comments, tree_depth):
        padding = ' ' * (indent * tree_depth)
        for c in comments:
            metadata = metadata_str(c, add_urls, add_timestamps, parsable)
            body = generate_body(c, parsable)
            c_str = padding + metadata + '\n\n' + body + f'\n{SEPARATOR[0]}'
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
    desc = 'Converts BDFR output into pretty text files'
    p = argparse.ArgumentParser(description=desc)
    p.add_argument('in_dir', metavar='IN_DIR',
                   help='input dir (output dir of BDFR)')
    p.add_argument('-o', metavar='OUT_DIR',
                   help='output dir (emptied before each run, default: IN_DIR +'
                   ' "_out")', dest='out_dir')
    p.add_argument('--indent', help='indent level (default: 6)', type=int,
                   default=6)
    p.add_argument('--parsable-out', '-p',
                   help='generate parsable output (see docs)',
                   action='store_true')
    p.add_argument('--shorten-urls', '-s', help='add IDs instead of full URLs',
                   action='store_true')
    p.add_argument('--timestamps', '-t', help='add timestamps instead of ages',
                   action='store_true')
    args = p.parse_args()

    in_dir = Path(args.in_dir)
    print(f'scanning for .json/.yaml files in {in_dir}...')
    yaml_paths = list(in_dir.glob('**/*.yaml'))
    if len(yaml_paths) > 0 and not YAML_INSTALLED:
        p.error(f'PyYAML not installed, cannot convert .yaml files')
    json_paths = list(in_dir.glob('**/*.json'))
    in_paths = yaml_paths + json_paths
    if len(in_paths) == 0:
        p.error('input dir does not contain .json/.yaml files')
    relative_paths = [p.relative_to(in_dir) for p in in_paths]

    if args.out_dir:
        out_dir = Path(args.out_dir)
    else:
        out_dir = (in_dir / Path('..') / f'{in_dir.name}_out').resolve()
    try:
        rmtree(out_dir)
    except FileNotFoundError:
        pass
    cp_dir_structure(in_dir, out_dir)

    for p in relative_paths:
        with open(in_dir / p, 'r') as in_f:
            if p.suffix == '.json':
                post = json.load(in_f)
            else: # yaml
                post = yaml.safe_load(in_f)
        out_text = post_to_text(post, args.indent, not args.shorten_urls,
                                args.timestamps, args.parsable_out)
        out_fp = out_dir / p.with_name(p.name + '.txt')
        with open(out_fp, 'w') as of:
            of.write(out_text)

if __name__ == '__main__':
    main()
