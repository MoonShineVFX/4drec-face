#!/usr/bin/env python3
import sys


def __main__():
    fdrec_path = 'G:/app/4drec-face/'
    src_path = fdrec_path + 'src/'
    resolve_path = src_path + 'resolve/'
    std_path = src_path + '/.python/Lib/'
    module_path = src_path + '/.python/Lib/site-packages/'

    for insert_path in (src_path, resolve_path, std_path, module_path):
        if insert_path not in sys.path:
            sys.path.insert(0, insert_path)
