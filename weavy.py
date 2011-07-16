#!/usr/bin/env python

import sys
import os
import shutil
import datetime
import re

def log(string):
    sys.stdout.write(string + os.linesep)

def read_file(filename):
    f = open(filename, "rt")
    content = f.read().decode("utf8")
    f.close()
    return content

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
        filename = '%s/_%s.%s' % (self.template_dir, template_name, file_ending)
        self.tpl[template_name] = read_file(filename)
    
    def __render(self, template, data):
        temp = self.tpl[template]
        for key, value in data.items():
            temp = temp.replace('{{%s}}' % key, value, 1)
        return temp

    def render_post(self, title, content):
        return self.__render('post', {'title':title, 'content':content})

    def render_blog(self, content):
        return self.__render('blog', {'content':content})
    
    def render_site(self, navigation, content):
        return self.__render('site', {'navigation':navigation, 'content':content})

    def render_page(self, content):
        return self.__render('page', {'content':content})

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
        self.files = []
        self.dirs = []
        for dirpath, dirnames, filenames in os.walk(self.directory):
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

def parse_datetime(datestring):
    dt = None

    formats = ["%Y/%m/%d"]
    for fmt in formats:
        try:
            dt = datetime.datetime.strptime(datestring, fmt)
        except ValueError:
            pass

    if not dt:
        raise WeavyError('date string %s matches none of the known format patterns (%s)' % (datestring, formats))
    
    return dt
    
    
def parse_metadata_line(line):
    line_parts = line.split(":", 1)
    if len(line_parts) != 2:
        raise WeavyError("metadata lines must be of the form \"key: value\"")
        
    key = line_parts[0].strip()
    value = line_parts[1].strip()
    if not re.match("[a-z_]+", key):
        raise WeavyError('key in metadata must be [a-z_]+ but is: %s' % key)
            
    return (key, value)


def parse_metadata(site_elem_data):
    if not site_elem_data.startswith("---\n") or site_elem_data.startswith("---\r"):
        return ({}, site_elem_data)
        
    lines = site_elem_data.splitlines()
    metadata = {}
    content_begin_lineno = 1
    for line in lines[1:]:
        content_begin_lineno += 1
        if line == "---":
            break
            
        key, value = parse_metadata_line(line)
        metadata[key] = value

    return (metadata, os.linesep.join( lines[content_begin_lineno:] ))

def load_site_data(dirtoload, out_map, site_item_facmethod):
    dirlst = DirectoryLister(dirtoload)
    dirlst.collect()
    files = dirlst.get_files()
    for filename in files:
        item = site_item_facmethod(filename)
        out_map[str(item.name)] = item

class SiteCategories:
    BLOG = "blog"
    PAGES = "page"
    MEDIA = "media"


class ItemName:
    def __init__(self):
        self.category = ""
        self.name = ""

    def __str__(self):
        return '%s:%s' % (self.category, self.name)

    @classmethod
    def from_str(cls, full_name_str):
        parts = full_name_str.split(":", 1)
        self.category = parts[0]
        self.name = parts[1]

    @classmethod
    def from_parts(cls, category, name):
        iname = ItemName()
        iname.category = category
        iname.name = name
        return iname


class SiteItem:
    def __init__(self):
        self.name = None #ItemName / relative path minus file ending plus prefix ("blog:", "page:", "media:", ...)
        self.path = "" #full absolute path into the filesystem
        self.title = "" #a title from the metadata
        self.created = None #datetime.datetime object
        self.last_updated = None #datetime.datetime object
        self.content = "" #the raw content
        self.renderas = "html" #the rendering to use on the content (html/markdown/...)
        self.author = "" #the author

    def __str__(self):
        return '{name:%s, title:%s, created:%s, last_updated:%s, renderas:%s}' % \
                (self.name, self.title, self.created, self.last_updated, self.renderas)
    
    def set_name_from_filename(self, site_category, filename):
        fileext = os.path.splitext(filename)
        self.name = ItemName.from_parts( site_category, filename[:-len(fileext[1])] )

    def set_metadata(self, metadata):
        if metadata.has_key("title"):
            self.title = metadata["title"]
        if metadata.has_key("last_changed"):
            self.last_changed = parse_datetime(metadata["last_changed"])
        if metadata.has_key("created"):
            self.created = parse_datetime(metadata["last_changed"])
        if metadata.has_key("author"):
            self.author = metadata["author"]
    
    def set_renderas_from_filename(self, filename):
        fileext = os.path.splitext(filename)
        fileext = fileext[1].replace(".", "")
        if fileext != "":
            self.renderas = fileext
        else:
            self.renderas = "html"



class BlogDataSource:
    def __init__(self, blog_dir):
        self.blog_dir = blog_dir
        self.posts = {} #map name->post

    def load_data(self):
        load_site_data(self.blog_dir, self.posts, self.__make_post)

    def get_post(self, name):
        ''' @param name the name of a blog post
                e.g. blog:2011/07/13/post_01
            @return a single BlogPosts element
        '''
        return self.posts[name]

    def get_posts(self):
        return [ v for _,v in self.posts.items() ]

    def __make_post(self, filename):
        post = SiteItem()
        post.set_name_from_filename(SiteCategories.BLOG, filename)
        post.path = os.path.join(self.blog_dir, filename)
        post.set_renderas_from_filename(filename)
        post.created = self.__datetime_from_filename(filename)
        post_data = read_file(os.path.join(self.blog_dir, filename))
        metadata, content = parse_metadata(post_data)
        post.content = content 
        post.set_metadata(metadata)
        return post

    def __datetime_from_filename(self, filename):
        datestr = os.path.dirname(filename)
        datestr_parts = datestr.split(os.path.sep)
        date = datetime.datetime(int(datestr_parts[0]), int(datestr_parts[1]), int(datestr_parts[2]))
        return date 


class PagesDataSource :
    def __init__(self, pages_dir):
        self.pages_dir = pages_dir
        self.pages = {}

    def load_data(self):
        load_site_data(self.pages_dir, self.pages, self.__make_page)

    def get_page(self, page_name):
        return self.pages[page_name]

    def get_pages(self):
        return [ v for _,v in self.pages.items() ]

    def __make_page(self, filename):
        page = SiteItem()
        page.set_name_from_filename(SiteCategories.PAGES, filename)
        page.path = os.path.join( self.pages_dir, filename )
        page_data = read_file( os.path.join( self.pages_dir, filename) )
        metadata, content = parse_metadata(page_data)
        page.content = content
        page.set_metadata(metadata)
        return page


class SiteRenderer:
    def __init__(self, out_dir, blog_data_source, pages_data_source, micro_template_engine):
        self.out_dir = out_dir
        self.blog = blog_data_source
        self.pages = pages_data_source
        self.mte = micro_template_engine
    
    def render(self):
        self.__render_blog()
        self.__render_pages()

    def __render_blog(self):
        posts = self.blog.get_posts()
        posts_html = []
        for post in posts:
            posts_html.append( self.mte.render_post(post.title, post.content) )

        blog_html = self.mte.render_blog(os.linesep.join(posts_html))
        site_html = self.mte.render_site(self.__make_navigation(), blog_html)

        self.__write_file(os.path.join(self.out_dir, "blog/index.html"), site_html)

    def __render_pages(self):
        pages = self.pages.get_pages()
        for page in pages:
            self.__render_page(page)

    def __render_page(self, page):
        filename = os.path.join( self.out_dir, '%s.html' % page.name.name )
        page_html = self.mte.render_page(page.content)
        site_html = self.mte.render_site(self.__make_navigation(), page_html)
        self.__write_file(filename, site_html)

    def __write_file(self, filename, content):
        dirname = os.path.dirname(filename)

        if not os.path.exists(dirname):
            os.makedirs(dirname)

        f = open(filename, "wt")
        f.write(content)
        f.close()


    def __make_navigation(self):
        return \
        '''
        <ul>
            <li>blog</li>
            <li>pages</li>
        </ul>
        '''
        




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
    
    log('loading pages data...')
    pages_dir = floc.get_pages_dir()
    pages_data = PagesDataSource(pages_dir)
    pages_data.load_data()

    log('rendering site...')
    siteR = SiteRenderer(out_dir, blog_data, pages_data, mte)
    siteR.render()

    return 0

if __name__=="__main__":
    sys.exit(main())
