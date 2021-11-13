# bdfr2text
Converts output files from [Bulk Downloader for Reddit](https://github.com/aliparlakci/bulk-downloader-for-reddit) into pretty text files for viewing by humans, like this:

![](demo.png)

## Usage
```
$ git clone https://github.com/DownrightNifty/bdfr2text.git
$ cd bdfr2text
$ python3 bdfr2text.py INPUT_DIR OUTPUT_DIR
```
Note: Currently, only JSON or YAML output from BDFR supported. While BDFR supports XML output, it is not supported. If converting YAML files, PyYAML is necessary (but this should already have been installed by BDFR). Otherwise, no dependencies.

There are a few options at the top of `bdfr2text.py` you can change:
```py
INDENT_SPACES = 6
# add URLs for each comment (if False, only short IDs are added)
ADD_URLS = False
# add timestamps for each comment (if False, the age of each comment is added)
ADD_TIMESTAMPS = False
```

The output text files are easily searchable with your favorite programs, e.g. `grep`. Personally, I use Sublime Text's "Find in Files" feature, which can search an entire folder. You can double-click on a result to jump to its position within the containing file. The [Clickable URLs](https://packagecontrol.io/packages/Clickable%20URLs) plugin is also helpful, if `ADD_URLS` is enabled.

To enable smart wrapping in vim (as depicted in the demo screenshot), add this to your `.vimrc`:
```
set breakindent
set linebreak
```

## Contributing
Issues and PRs are welcome.

## See also
* [bdfr-html](https://github.com/BlipRanger/bdfr-html)
