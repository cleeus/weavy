#!/usr/bin/env python

# This file is part of weavy.
# Weavy is licensed under the 2-clause BSD license.
# See the LICENSE file for full terms and conditions.
# Copyright 2011, Kai Dietrich <mail@cleeus.de>

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

class SiteCategories:
    BLOG = "blog"
    PAGES = "page"
    MEDIA = "media"
    categories = [BLOG, PAGES, MEDIA]

class MicroTemplateEngine:
    def __init__(self, template_dir, item_name_resolver):
        self.template_dir = template_dir
        self.inr = item_name_resolver
        self.tpl = {}

    def load_all_templates(self):
        self.__load_tpl('site', 'html')
        self.__load_tpl('blog', 'html')
        self.__load_tpl('post', 'html')
        self.__load_tpl('page', 'html')
        self.__load_tpl('nav_level', 'html')
        self.__load_tpl('nav_node', 'html')

    def __load_tpl(self, template_name, file_ending):
        filename = '%s/_%s.%s' % (self.template_dir, template_name, file_ending)
        self.tpl[template_name] = read_file(filename)
    
    def __render(self, template, data, from_item_name):
        temp = self.tpl[template]
        for key, value in data.items():
            temp = temp.replace('{{%s}}' % key, value, 1)
        
        urls = []
        for cat in SiteCategories.categories:
            urls.extend( re.findall('\{\{%s:.+\}\}' % cat, temp) )

        for url in urls:
            item_name = url[2:-2]
            temp = temp.replace(url, self.inr.get_rel_path_http(ItemName.from_str(item_name), from_item_name))

        return temp

    def render_post(self, from_item_name, title, content):
        return self.__render('post', {'title':title, 'content':content}, from_item_name)

    def render_blog(self, from_item_name, content):
        return self.__render('blog', {'content':content}, from_item_name)
    
    def render_site(self, from_item_name, navigation, content):
        return self.__render('site', {'navigation':navigation, 'content':content}, from_item_name)

    def render_page(self, from_item_name, content):
        return self.__render('page', {'content':content}, from_item_name)

    def render_nav_level(self, from_item_name, content):
        return self.__render('nav_level', {'content': content}, from_item_name)

    def render_nav_node(self, from_item_name, linkedpage, visualtext, subnavcontent):
        return self.__render('nav_node', {'linkedpage':linkedpage, 'visualtext':visualtext, 'subnavcontent':subnavcontent}, from_item_name)

class FolderLocator:
    def __init__(self):
        self.in_dir = os.path.abspath('.')
        self.blog_dir = '%s/blog/' % self.in_dir
        self.pages_dir = '%s/pages/' % self.in_dir
        self.template_dir = '%s/template/' % self.in_dir
        self.out_dir = '%s/out/' % self.in_dir
        self.media_dir = '%s/media/' % self.in_dir

        def _check_dir(dirpath, dirname):
            if not os.path.isdir(dirpath):
                raise WeavyError('%s dir (%s) not found' % dirname, dirpath)

        _check_dir(self.blog_dir, 'blog')
        _check_dir(self.pages_dir, 'pages')
        _check_dir(self.template_dir, 'template')
        _check_dir(self.out_dir, 'out')
        _check_dir(self.media_dir, 'media')

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

    def get_media_dir(self):
        return self.media_dir


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

class ItemName:
    def __init__(self):
        self.category = ""
        self.name = ""

    def __str__(self):
        return '%s:%s' % (self.category, self.name)

    @classmethod
    def from_str(cls, full_name_str):
        parts = full_name_str.split(":", 1)
        parts[1] = parts[1].replace("\\", "/")
        return ItemName.from_parts(parts[0], parts[1])

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
        if site_category == SiteCategories.MEDIA:
            name = filename
        else:
            fileext = os.path.splitext(filename)
            name = filename[:-len(fileext[1])]

        self.name = ItemName.from_parts( site_category, name )

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


class PagesDataSource:
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

class MediaDataSource:
    def __init__(self, media_dir):
        self.media_dir = media_dir
        self.media = {}

    def load_data(self):
        load_site_data(self.media_dir, self.media, self.__make_media)

    def get_media(self, media_name):
        return self.media[media_name]

    def get_medias(self):
        return [ v for _,v in self.media.items() ]

    def __make_media(self, filename):
        media = SiteItem()
        media.set_name_from_filename(SiteCategories.MEDIA, filename)
        media.path = os.path.join( self.media_dir, filename )
        return media



class DataSources:
    def __init__(self, blog_data_source, pages_data_source, media_data_source):
        self.blog = blog_data_source
        self.pages = pages_data_source
        self.media = media_data_source

class ItemNameResolver:
    def __init__(self, out_dir):
        self.out_dir = out_dir

    def get_abs_path(self, item_name):
        if item_name.category == SiteCategories.BLOG:
            return os.path.join( self.out_dir, os.path.join("blog", '%s.html' % item_name.name) )

        if item_name.category == SiteCategories.PAGES:
            return os.path.join( self.out_dir, '%s.html' % item_name.name )

        if item_name.category == SiteCategories.MEDIA:
            return os.path.join( self.out_dir, os.path.join("media", item_name.name) )

    def get_rel_path(self, item_name, rel_to):
        if isinstance(rel_to, ItemName):
            rel_to = self.get_abs_path(rel_to)
        rel_to = os.path.dirname(rel_to)
        abspath = self.get_abs_path(item_name)
        relpath = os.path.relpath(abspath, rel_to)
        return relpath

    def get_rel_path_http(self, item_name, rel_to):
        return self.get_rel_path(item_name, rel_to).replace("\\", "/")


class NavTreeNode:
    def __init__(self, visual_text, linked_item_name):
        self.visual_text = visual_text
        self.linked_item_name = linked_item_name
        self.child_list = []
    
    def __str__(self):
        return self.pretty_str()

    def pretty_str(self, indent_level=0):
        def _indent(level, string):
            return " "*level + string

        lines = []
        lines.append( _indent(indent_level, '%s->%s' % (self.visual_text, self.linked_item_name) ) )
        for child in self.child_list:
            lines.append( child.pretty_str(indent_level+1) )
        return os.linesep.join(lines)

    def add_child(self, node):
        self.child_list.append(node)

    def get_child(self, visual_text):
        for child in self.child_list:
            if child.visual_text == visual_text:
                return child
        return None

    def get_children(self):
        return self.child_list



class NavigationRenderer:
    def __init__(self, item_name_resolver, data_sources, micro_template_engine):
        self.inr = item_name_resolver
        self.mte = micro_template_engine
        self.ds = data_sources

    def make_navigation(self, from_item_name):
        tree = self.__make_nav_tree()
        return self.__recursive_render(tree, from_item_name)
    
    def __recursive_render(self, root_node, from_item_name):
        children = root_node.get_children()
        if len(children) > 0:
            children_html = []
            for child in children:
                subnavcontent = self.__recursive_render(child, from_item_name)
                linked_url = self.inr.get_rel_path_http(child.linked_item_name, from_item_name)
                visual_text = child.visual_text
                child_html = self.mte.render_nav_node(from_item_name, linked_url, visual_text, subnavcontent)
                children_html.append( child_html )

            return self.mte.render_nav_level(from_item_name, os.linesep.join(children_html))
        else:
            return ""

    def __make_nav_tree(self):
        root = NavTreeNode(None, None)
        for page in self.ds.pages.get_pages():
            visual_path = self.__name_to_visual_path(page.name)
            self.__recursive_add_path(root, visual_path)
        return root

    def __name_to_visual_path(self, item_name):
        path_elems = item_name.name.split("/")[:-1]
        visual_path = []
        path = ""
        for path_elem in path_elems:
            path += path_elem
            visual_path.append( (path_elem, ItemName.from_parts(SiteCategories.PAGES, '%s/index' % path) ) )
            path += "/"
        return visual_path 
        
    def __recursive_add_path(self, root_node, visual_path):
        if len(visual_path) > 0:
            visual_text, linked_page = visual_path[0]
            child = root_node.get_child(visual_text)
            if child == None:
                child = NavTreeNode(visual_text, linked_page)
                root_node.add_child(child)
            self.__recursive_add_path(child, visual_path[1:])

class SiteRenderer:
    def __init__(self, item_name_resolver, data_sources, micro_template_engine):
        self.inr = item_name_resolver
        self.blog = data_sources.blog
        self.pages = data_sources.pages
        self.media = data_sources.media
        self.mte = micro_template_engine
        self.navR = NavigationRenderer(self.inr, data_sources, self.mte)
    
    def render(self):
        self.__render_blog()
        self.__render_pages()
        self.__render_media()

    def __render_blog(self):
        posts = self.blog.get_posts()
        for post in posts:
            self.__render_blog_post(post)
        self.__render_blog_htmlview(posts)

    def __render_blog_htmlview(self, posts):
        posts_html = []
        for post in posts:
            posts_html.append( self.mte.render_post(post.name, post.title, post.content) )
        
        post_list_iname = ItemName.from_parts(SiteCategories.BLOG, "index")
        blog_html = self.mte.render_blog(post_list_iname, os.linesep.join(posts_html))
        site_html = self.mte.render_site(post_list_iname, self.make_navigation(post_list_iname), blog_html)

        filename = self.inr.get_abs_path(post_list_iname)
        self.__write_file(filename, site_html)

    def __render_blog_post(self, post):
        filename = self.inr.get_abs_path(post.name)
        post_html = self.mte.render_post(post.name, post.title, post.content)
        page_html = self.mte.render_page(post.name, post.content)
        site_html = self.mte.render_site(post.name, self.make_navigation(post.name), page_html)
        self.__write_file(filename, site_html)

    def __render_pages(self):
        pages = self.pages.get_pages()
        for page in pages:
            self.__render_page(page)

    def __render_page(self, page):
        filename = self.inr.get_abs_path(page.name)
        page_html = self.mte.render_page(page.name, page.content)
        site_html = self.mte.render_site(page.name, self.make_navigation(page.name), page_html)
        self.__write_file(filename, site_html)

    def __render_media(self):
        for media_item in self.media.get_medias():
            filename = self.inr.get_abs_path(media_item.name)
            self.__copy_file(media_item.path, filename)

    def __write_file(self, filename, content):
        self.__mkpath_for_file(filename)
        f = open(filename, "wt")
        f.write(content.encode("utf8"))
        f.close()

    def __copy_file(self, src, dst):
        self.__mkpath_for_file(dst)
        shutil.copy(src, dst)
        
    def __mkpath_for_file(self, filename):
        path = os.path.dirname(filename)
        if not os.path.exists(path):
            os.makedirs(path)

    def make_navigation(self, from_item_name):
        return self.navR.make_navigation(from_item_name)



def erase_dir_contents(pathname):
    shutil.rmtree(pathname)
    os.mkdir(pathname)

def main():
    floc = FolderLocator()
   
    out_dir = floc.get_out_dir()
    log('cleaning output dir: %s' % out_dir)
    erase_dir_contents(out_dir)
    
    log('loading blog data...')
    blog_dir = floc.get_blog_dir()
    blog_data = BlogDataSource(blog_dir)
    blog_data.load_data()
    
    log('loading pages data...')
    pages_dir = floc.get_pages_dir()
    pages_data = PagesDataSource(pages_dir)
    pages_data.load_data()
    
    log('loading media data...')
    media_dir = floc.get_media_dir()
    media_data = MediaDataSource(media_dir)
    media_data.load_data()

    inr = ItemNameResolver(out_dir)
    ds = DataSources(blog_data, pages_data, media_data)

    log('loading templates...')
    template_dir = floc.get_template_dir()
    mte = MicroTemplateEngine(template_dir, inr)
    mte.load_all_templates() 
    
    log('rendering site...')
    siteR = SiteRenderer(inr, ds, mte)
    siteR.render()

    return 0

if __name__=="__main__":
    sys.exit(main())
