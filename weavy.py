#!/usr/bin/env python

import sys
import os
import shutil
import datetime

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
        self.in_dir = os.path.abspath('.')
        blog_dir = '%s/blog/' % self.in_dir
        pages_dir = '%s/pages/' % self.in_dir
        template_dir = '%s/template/' % self.in_dir
        out_dir = '%s/out/' % self.in_dir

        if  os.path.isdir(blog_dir):
            self.blog_dir = blog_dir
        else:
            raise WeavyError('blog dir (%s) not found' % blog_dir)

        if os.path.isdir(pages_dir):
            self.pages_dir = pages_dir
        else:
            raise WeavyError('pages dir (%s) not found' % pages_dir)

        if os.path.isdir(template_dir):
            self.template_dir = template_dir
        else:
            raise WeavyError('template dir (%s) not found' % template_dir)

        if os.path.isdir(out_dir):
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


class DirectoryLister:
    def __init__(self, directory):
        self.directory = directory
        self.files = []
        self.dirs = []

    def collect(self):
        for dirpath, dirnames, filenames in os.walk(self.directory):
            self.dirs = []
            self.files = []
            for dirname in dirnames:
                self.dirs.append( os.path.join(dirpath, dirname) )
            for filename in filenames:
                self.files.append( os.path.join(dirpath, filename) )
        

    def get_files(self, relative=True):
        if not relative:
            return self.files
        else:
            return self.__make_relative(self.files)

    def get_dirs(self, relative=True):
        if not relative:
            return self.dirs
        return self.__make_relative(self.dirs)

    def __make_relative(self, names):
        return [ x[len(self.directory):] for x in names ]

class BlogPost:
    def __init__(self):
        self.name = "" #relative path minus file ending
        self.title = "" #a title from the metadata
        self.created = None #datetime.datetime object
        self.last_updated = None #datetime.datetime object
        self.content = "" #the raw content
        self.renderas = "html" #the rendering to use on the content (html/markdown/...)

    def __str__(self):
        return '{name:%s, title:%s, created:%s, last_updated:%s, renderas:%s}' % \
                (self.name, self.title, self.created, self.last_updated, self.renderas)

class BlogDataSource:
    def __init__(self, blog_dir):
        self.blog_dir = blog_dir
        self.posts = {} #map name->post

    def load_data(self):
        dirlst = DirectoryLister(self.blog_dir)
        dirlst.collect()
        files = dirlst.get_files()
        for filename in files:
            post = self.__make_post(filename)
            self.posts[post.name] = post

    def get_post(self, name):
        ''' @param name the name of a blog post
                e.g. blog:2011/07/13/post_01
            @return a single BlogPosts element
        '''
        return self.posts[name]

    def get_posts(self):
        return [ v for _,v in self.posts.items() ]

    def __make_post(self, filename):
        post = BlogPost()
        post.name = self.__name_from_filename(filename)
        post.renderas = self.__renderas_from_filename(filename)
        post.created = self.__datetime_from_filename(filename)
        print post
        return post

    def __name_from_filename(self, filename):
        fileext = os.path.splitext(filename)
        name = 'blog:%s' % filename[:-len(fileext[1])]
        return name

    def __datetime_from_filename(self, filename):
        datestr = os.path.dirname(filename)
        datestr_parts = datestr.split(os.path.sep)
        date = datetime.datetime(int(datestr_parts[0]), int(datestr_parts[1]), int(datestr_parts[2]))
        return date 

    def __renderas_from_filename(self, filename):
        fileext = os.path.splitext(filename)
        fileext = fileext[1].replace(".", "")
        if fileext != "":
            return fileext
        else:
            return "html"




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
    
    log('loading blog data...')
    blog_dir = floc.get_blog_dir()
    blog_data = BlogDataSource(blog_dir)
    blog_data.load_data()

    return 0

if __name__=="__main__":
    sys.exit(main())
