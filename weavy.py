#!/usr/bin/env python

# This file is part of weavy.
# Weavy is licensed under the 2-clause BSD license.
# See the LICENSE file for full terms and conditions.
# Copyright 2011, Kai Dietrich <mail@cleeus.de>

import sys
import os
import shutil
import datetime
import time
import re
import string
import uuid
from email import utils as email_utils
try:
    from ConfigParser import SafeConfigParser as ConfigParser
except:
    from configparser import SafeConfigParser as ConfigParser
import markdown

class WeavyError(Exception):
    pass

def log(string):
    sys.stdout.write(string + os.linesep)

def read_file(filename):
    f = open(filename, "rt")
    content = f.read()
    try:
        content_unicode = content.decode("utf8")
    except UnicodeDecodeError:
        raise WeavyError('error during utf8-decode of file %s' % filename)

    f.close()
    return content_unicode

class SiteCategories:
    BLOG = "blog"
    PAGES = "page"
    MEDIA = "media"
    FEEDS = "feed"
    categories = [BLOG, PAGES, MEDIA, FEEDS]

class MicroTemplateEngine:
    def __init__(self, template_dir, item_name_resolver):
        self.template_dir = template_dir
        self.inr = item_name_resolver
        self.tpl = {}
        self.tpl_urls = {} # placeholder->itemname string

    def load_all_templates(self):
        self.__load_tpl('site', 'html')
        self.__load_tpl('blog', 'html')
        self.__load_tpl('post', 'html')
        self.__load_tpl('page', 'html')
        self.__load_tpl('tag',  'html')
        self.__load_tpl('tag_box', 'html')
        self.__load_tpl('nav_level', 'html')
        self.__load_tpl('nav_node', 'html')
        self.__load_tpl('blog_rss', 'xml')
        self.__load_tpl('post_rss', 'xml')
    
    def __make_unique_placeholder(self, data):
        temp = data[0]
        while data.find(temp) != -1:
            temp = "random_placeholder_" + str(uuid.uuid1()).replace("-", "_")
        return temp

    def __load_tpl(self, template_name, file_ending):
        filename = os.path.join(self.template_dir, '_%s.%s' % (template_name, file_ending))
        tpl_data = read_file(filename)
        
        url_placeholders = []
        for cat in SiteCategories.categories:
            url_placeholders.extend( re.findall('\$\{%s:[^}]+\}' % cat, tpl_data) )
        
        for url_ph in url_placeholders:
            item_name = url_ph[2:-1]
            new_ph = self.__make_unique_placeholder(tpl_data)
            self.tpl_urls[new_ph] = item_name
            tpl_data = tpl_data.replace( url_ph, '${%s}'%new_ph )
        
        self.tpl[template_name] = string.Template( tpl_data )

    def __render(self, template, data, from_item_name):
        tpl = self.tpl[template]
        #add new placeholders to data
        data = dict(data)
        for new_placeholder,item_name_str in self.tpl_urls.items():
            data[new_placeholder] = self.inr.get_rel_path_http(ItemName.from_str(item_name_str), from_item_name) 

        temp = tpl.safe_substitute(data)
        return temp
    
    def render_content(self, from_item_name, content):
        url_placeholders = []
        for cat in SiteCategories.categories:
            url_placeholders.extend( re.findall('\$\{%s:[^}]+\}' % cat, content) )
        
        urlmap = {} #placeholder->item_name
        for url_ph in url_placeholders:
            item_name = url_ph[2:-1]
            new_ph = self.__make_unique_placeholder(content)
            urlmap[new_ph] = item_name
            content = content.replace( url_ph, '${%s}'%new_ph )
        
        data = {}
        for placeholder, item_name_str in urlmap.items():
            data[placeholder] = self.inr.get_rel_path_http(ItemName.from_str(item_name_str), from_item_name)

        template = string.Template(content)
        rendered_content = template.safe_substitute(data)

        return rendered_content
    
    def render_tag(self, from_item_name, tag_text):
        return self.__render('tag', {'tagtext':tag_text}, from_item_name)
    
    def render_tag_box(self, from_item_name, tags_content):
        return self.__render('tag_box', {'tagscontent':tags_content}, from_item_name)

    def render_post(self, from_item_name, title, postdate, posturl, author, posttags, content):
        return self.__render_post('post', from_item_name, title, postdate, posturl, author, posttags, content)
    
    def render_post_rss(self, from_item_name, title, postdate, posturl, author, content):
        return self.__render_post('post_rss', from_item_name, title, postdate, posturl, author, "", content)

    def __render_post(self, template_name, from_item_name, title, postdate, posturl, author, posttags, content):
        return self.__render(template_name, {\
            'title':title, \
            'postdate':postdate, \
            'posturl':posturl, \
            'postauthor':author, \
            'posttags':posttags, \
            'content':content \
        }, from_item_name)


    def render_blog(self, from_item_name, content):
        return self.__render_blog('blog', from_item_name, content, "", "", "")
    
    def render_blog_rss(self, from_item_name, content, site_baseurl, site_title, site_description):
        return self.__render_blog('blog_rss', from_item_name, content, site_baseurl, site_title, site_description)

    def __render_blog(self, template_name, from_item_name, content, site_baseurl, site_title, site_description):
        return self.__render(template_name, { \
            'content':content, \
            'baseurl':site_baseurl, \
            'sitetitle':site_title, \
            'sitedescription':site_description \
        }, from_item_name)


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
                if self.__is_visible_file(filename):
                    self.files.append( os.path.join(dirpath, filename) )
    
    def __is_visible_file(self, path):
        filename = os.path.basename(path)
        return not filename.startswith(".")

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

    formats = ["%Y/%m/%d", "%Y/%m/%d %H:%M", "%Y%m%dT%H%MZ"]
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
        self.author = "" #the author
        self.tags = [] #a list of strings that are tags

    def __str__(self):
        return '{name:%s, title:%s, created:%s, last_updated:%s}' % \
                (self.name, self.title, self.created, self.last_updated)
    
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
            self.created = parse_datetime(metadata["created"])
        if metadata.has_key("author"):
            self.author = metadata["author"]
        if metadata.has_key("tags"):
            tags_str = metadata["tags"]
            self.tags.extend( [ s.strip() for s in tags_str.split(",") ] )
            
            
_mdproc = markdown.Markdown(safe_mode=False, extensions=['codehilite'], output_format='xhtml1')
def filter_content(content, filename):
    if filename.endswith(".markdown"):
        content = _mdproc.convert(content)
    return content

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
        post_list = [ v for _,v in self.posts.items() ]
        def cmp_created(x,y):
            if x.created < y.created:
                return -1
            elif x.created == y.created:
                return 0
            else:
                return 1
        post_list.sort(cmp = cmp_created, reverse=True)
        return post_list

    def __make_post(self, filename):
        post = SiteItem()
        post.set_name_from_filename(SiteCategories.BLOG, filename)
        post.path = os.path.join(self.blog_dir, filename)
        abs_filename = os.path.join(self.blog_dir, filename)
        post.created = self.__datetime_from_filename(abs_filename)
        post_data = read_file(abs_filename)
        metadata, content = parse_metadata(post_data)
        post.content = filter_content(content, filename)
        post.set_metadata(metadata)
        return post

    def __datetime_from_filename(self, abs_filename):
        datestr = os.path.dirname(abs_filename)
        datestr_parts = datestr.split(os.path.sep)
        date = datetime.datetime(int(datestr_parts[-3]), int(datestr_parts[-2]), int(datestr_parts[-1]))
        cdate = datetime.datetime.fromtimestamp( os.path.getmtime(abs_filename) )
        date = datetime.datetime(date.year, date.month, date.day, cdate.hour, cdate.minute, cdate.second)
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
        page.content = filter_content(content, filename)
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
    def __init__(self, out_dir, base_url):
        self.out_dir = out_dir
        self.base_url = base_url

    def __get_outdir_path(self, item_name):
        if item_name.category == SiteCategories.BLOG:
            return os.path.join("blog", '%s.html' % item_name.name)

        if item_name.category == SiteCategories.PAGES:
            return '%s.html' % item_name.name

        if item_name.category == SiteCategories.MEDIA:
            return os.path.join("media", item_name.name)

        if item_name.category == SiteCategories.FEEDS:
            return os.path.join("feeds", '%s.xml' % item_name.name)

    def get_abs_path(self, item_name):
        return os.path.join(self.out_dir, self.__get_outdir_path(item_name))

    def get_rel_path(self, item_name, rel_to):
        if isinstance(rel_to, ItemName):
            rel_to = self.get_abs_path(rel_to)
        rel_to = os.path.dirname(rel_to)
        abspath = self.get_abs_path(item_name)
        relpath = os.path.relpath(abspath, rel_to)
        return relpath

    def get_rel_path_http(self, item_name, rel_to):
        return self.get_rel_path(item_name, rel_to).replace("\\", "/")
    
    def get_abs_url(self, item_name):
        return '%s%s' % (self.base_url, self.__get_outdir_path(item_name))

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
        blog_node = NavTreeNode("blog", ItemName.from_parts(SiteCategories.BLOG, "index"))
        root.add_child(blog_node)
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
    def __init__(self, item_name_resolver, data_sources, micro_template_engine, site_config):
        self.inr = item_name_resolver
        self.blog = data_sources.blog
        self.pages = data_sources.pages
        self.media = data_sources.media
        self.mte = micro_template_engine
        self.config = site_config
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
        self.__render_blog_rssview(posts)

    def __render_blog_htmlview(self, posts):
        post_list_iname = ItemName.from_parts(SiteCategories.BLOG, "index")
        posts_html = []
        for post in posts:
            post_url = self.inr.get_rel_path_http(post.name, post_list_iname) 
            post_datetime = self.__make_post_date(post)
            post_author = self.__make_post_author(post)
            post_tags = self.__render_tags(post_list_iname, post)
            post_content = self.mte.render_content(post_list_iname, post.content)
            posts_html.append( self.mte.render_post(post.name, post.title, post_datetime, post_url, post_author, post_tags, post_content) )
        
        blog_html = self.mte.render_blog(post_list_iname, os.linesep.join(posts_html))
        site_html = self.mte.render_site(post_list_iname, self.make_navigation(post_list_iname), blog_html)

        filename = self.inr.get_abs_path(post_list_iname)
        self.__write_file(filename, site_html)

    def __render_blog_rssview(self, posts):
        feed_iname = ItemName.from_parts(SiteCategories.FEEDS, "blog")
        posts_xml = []
        posts_in_feeds = self.config.get_blog_posts_in_feeds()
        posts_to_render = posts[0:posts_in_feeds]
        for post in posts_to_render:
            post_url = self.inr.get_abs_url(post.name)
            post_author = self.__make_post_author(post)
            post_datetime = self.__make_post_date_rss(post)
            post_content = self.mte.render_content(feed_iname, post.content)
            posts_xml.append( self.mte.render_post_rss(post.name, post.title, post_datetime, post_url, post_author, post_content) )

        feed_xml = self.mte.render_blog_rss(feed_iname, os.linesep.join(posts_xml), \
            self.config.get_baseurl(), \
            self.config.get_site_title(), \
            self.config.get_site_description() \
        )
        filename = self.inr.get_abs_path(feed_iname)
        self.__write_file(filename, feed_xml)

    def __render_blog_post(self, post):
        filename = self.inr.get_abs_path(post.name)
        post_datetime = self.__make_post_date(post)
        post_url = self.inr.get_rel_path_http(post.name, post.name)
        post_author = self.__make_post_author(post)
        post_tags = self.__render_tags(post.name, post)
        post_content = self.mte.render_content(post.name, post.content)
        post_html = self.mte.render_post(post.name, post.title, post_datetime, post_url, post_author, post_tags, post_content)
        page_html = self.mte.render_page(post.name, post_html)
        site_html = self.mte.render_site(post.name, self.make_navigation(post.name), page_html)
        self.__write_file(filename, site_html)

    def __render_tags(self, from_item_name, post):
        tags_html = []
        for tag in post.tags:
            tags_html.append( self.mte.render_tag(from_item_name, tag) )
        tags_html = ''.join(tags_html)
        if len(tags_html) > 0:
            return self.mte.render_tag_box(from_item_name, tags_html)
        else:
            return ""

    
    def __make_post_date_rss(self, post):
        dt_tuple = post.created.timetuple()
        dt_stamp = time.mktime(dt_tuple)
        return email_utils.formatdate(dt_stamp)
    
    def __make_post_date(self, post):
        return post.created.isoformat().rsplit(":", 1)[0]
    
    def __make_post_author(self, post):
        if post.author == "" or post.author == None:
            return self.config.get_site_default_author()
        else:
            return post.author

    def __render_pages(self):
        pages = self.pages.get_pages()
        for page in pages:
            self.__render_page(page)

    def __render_page(self, page):
        filename = self.inr.get_abs_path(page.name)
        page_content = self.mte.render_content(page.name, page.content)
        page_html = self.mte.render_page(page.name, page_content)
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


class SiteConfig:
    def __init__(self, config_filename):
        self.config_file = config_filename
        self.baseurl = None
        self.site_title = None
        self.site_description = None
        self.site_default_author = None
        self.blog_posts_per_page = 10
        self.blog_posts_in_feeds = 20

    def load(self):
        parser = ConfigParser()
        parser.read(self.config_file)
        self.baseurl = parser.get("weavy", "baseurl")
        self.site_title = parser.get("weavy", "site_title")
        self.site_description = parser.get("weavy", "site_description")
        self.site_default_author = parser.get("weavy", "site_default_author")
        self.blog_posts_per_page = parser.getint("weavy", "blog_posts_per_page")
        self.blog_posts_in_feeds = parser.getint("weavy", "blog_posts_in_feeds")

    def get_baseurl(self):
        return self.baseurl

    def get_site_title(self):
        return self.site_title
    
    def get_site_description(self):
        return self.site_description
    
    def get_site_default_author(self):
        return self.site_default_author

    def get_blog_posts_per_page(self):
        return self.blog_posts_per_page

    def get_blog_posts_in_feeds(self):
        return self.blog_posts_in_feeds

def erase_dir_contents(pathname):
    shutil.rmtree(pathname)
    os.mkdir(pathname)

def main():
    floc = FolderLocator()
  
    log('loading site.conf...')
    config = SiteConfig(os.path.join(floc.get_in_dir(), "site.conf"))
    config.load()

    out_dir = floc.get_out_dir()
    log('cleaning output dir %s...' % out_dir)
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

    inr = ItemNameResolver(out_dir, config.get_baseurl())
    ds = DataSources(blog_data, pages_data, media_data)

    log('loading templates...')
    template_dir = floc.get_template_dir()
    mte = MicroTemplateEngine(template_dir, inr)
    mte.load_all_templates() 
    
    log('rendering site...')
    siteR = SiteRenderer(inr, ds, mte, config)
    siteR.render()

    return 0

if __name__=="__main__":
    sys.exit(main())
