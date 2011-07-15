#!/usr/bin/env python

import sys
import os
from os import path
import shutil

def log(string):
    print string

class WeavyError(Exception):
    pass

class MicroTemplateEngine:
    def __init__(self, template_dir):
        self.template_dir = template_dir
        self.tpl = {}

    def load_all_templates(self):
        self.__load_tpl('site', 'html')
        self.__load_tpl('blog', 'html')
        self.__load_tpl('post', 'html')
        self.__load_tpl('page', 'html')

    def __load_tpl(self, template_name, file_ending):
        f = open('%s/_%s.%s' % (self.template_dir, template_name, file_ending), 'rt')
        self.tpl[template_name] = f.read().decode('utf8')
        f.close()
    
    def __render(self, template, data):
        temp = self.tpl[template]
        for key, value in data.items():
            temp = temp.replace('{{%s}}' % key, value, 1)
        return temp

    def render_post(self, title, content):
        return self.__render('post', {'title':title, 'content':content})
    
    def render_site(self, navigation, content):
        return self.__render('site', {'navigation':navigation, 'content':content})

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
     
class BlogTransformation:
    def __init__(self, in_dir, out_dir):
        self.in_dir = in_dir
        self.out_dir = out_dir


def erase_dir_contents(pathname):
    shutil.rmtree(pathname)
    os.mkdir(pathname)

def main():
    floc = FolderLocator()
   
    out_dir = floc.get_out_dir()
    log('cleaning output dir: %s' % out_dir)
    erase_dir_contents(out_dir)
    
    log('loading templates...')
    template_dir = floc.get_template_dir()
    mte = MicroTemplateEngine(template_dir)
    mte.load_all_templates()

    print mte.render_site('navi', 'the content')

    return 0

if __name__=="__main__":
    sys.exit(main())
