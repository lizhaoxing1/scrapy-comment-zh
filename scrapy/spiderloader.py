# -*- coding: utf-8 -*-
from __future__ import absolute_import
from collections import defaultdict
import traceback
import warnings

from zope.interface import implementer

from scrapy.interfaces import ISpiderLoader
from scrapy.utils.misc import walk_modules
from scrapy.utils.spider import iter_spider_classes


@implementer(ISpiderLoader)
class SpiderLoader(object):
    """
    SpiderLoader is a class which locates and loads spiders
    in a Scrapy project.
    """
    def __init__(self, settings):
        self.spider_modules = settings.getlist('SPIDER_MODULES')  # 这里如果没有任何项目是空的,创建了项目以后这里是自己写爬虫的路径
        self.warn_only = settings.getbool('SPIDER_LOADER_WARN_ONLY')
        self._spiders = {}
        self._found = defaultdict(list)
        self._load_all_spiders()

    def _check_name_duplicates(self):
        dupes = ["\n".join("  {cls} named {name!r} (in {module})".format(
                                module=mod, cls=cls, name=name)
                           for (mod, cls) in locations)
                 for name, locations in self._found.items()
                 if len(locations)>1]
        if dupes:
            msg = ("There are several spiders with the same name:\n\n"
                   "{}\n\n  This can cause unexpected behavior.".format(
                        "\n\n".join(dupes)))
            warnings.warn(msg, UserWarning)

    def _load_spiders(self, module):
        # 这里加载自己编写的spider.py文件里的CrawlSpider类.并将类中定义的name 作为key 实例化子类,赋值给self_spiders
        for spcls in iter_spider_classes(module):
            self._found[spcls.name].append((module.__name__, spcls.__name__))
            self._spiders[spcls.name] = spcls

    def _load_all_spiders(self):
        # 将自己编写的CrawlSpider子类,实例化给 self_spiders(字典) 并将子类中name作为key
        for name in self.spider_modules:
            try:
                for module in walk_modules(name):
                    self._load_spiders(module)
            except ImportError as e:
                if self.warn_only:
                    msg = ("\n{tb}Could not load spiders from module '{modname}'. "
                           "See above traceback for details.".format(
                                modname=name, tb=traceback.format_exc()))
                    warnings.warn(msg, RuntimeWarning)
                else:
                    raise
        self._check_name_duplicates()

    @classmethod
    def from_settings(cls, settings):
        return cls(settings)

    def load(self, spider_name):
        """
        Return the Spider class for the given spider name. If the spider
        name is not found, raise a KeyError.
        """
        try:
            return self._spiders[spider_name]
        except KeyError:
            raise KeyError("Spider not found: {}".format(spider_name))

    def find_by_request(self, request):
        """
        Return the list of spider names that can handle the given request.
        """
        return [name for name, cls in self._spiders.items()
                if cls.handles_request(request)]

    def list(self):
        """
        Return a list with the names of all spiders available in the project.
        """
        return list(self._spiders.keys())
