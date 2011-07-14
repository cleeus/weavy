#!/usr/bin/env python

import sys
import os
from os import path

class WeavyError(Exception):
    pass

class MicroTemplate:
    pass


class FolderLocator:
    def __init__(self):
        self.in_dir = path.abspath('.')
        blog_dir = '%s/blog/' % self.in_dir
        pages_dir = '%s/pages/' % self.in_dir
        template_dir = '%s/template/' % self.in_dir
        out_dir = '%s/out/' % self.in_dir

        if  path.isdir(blog_dir):
            self.blog_dir = blog_dir
        else:
            raise WeavyError('blog dir (%s) not found' % blog_dir)

        if path.isdir(pages_dir):
            self.pages_dir = pages_dir
        else:
            raise WeavyError('pages dir (%s) not found' % pages_dir)

        if path.isdir(template_dir):
            self.template_dir = template_dir
        else:
            raise WeavyError('template dir (%s) not found' % template_dir)

        if path.isdir(out_dir):
            self.out_dir = out_dir
        else:
            raise WeavyError('out dir (%s) not found' % out_dir)

    def get_in_dir(self):
        return self.in_dir

    def get_out_dir(self):
        return self.out_dir

    def get_template_dir(self):
        return self.template_dir

    def get_blog_dir(self):
        return self.blog_dir

    def get_pages_dir(self):
        return self.pages_dir
     



def main():
    floc = FolderLocator()
    print(floc.get_out_dir())

    return 0

if __name__=="__main__":
    sys.exit(main())
