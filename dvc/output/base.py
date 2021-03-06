import re
from schema import Or, Optional

from dvc.exceptions import DvcException


class OutputDoesNotExistError(DvcException):
    def __init__(self, path):
        msg = "output '{}' does not exist".format(path)
        super(OutputDoesNotExistError, self).__init__(msg)


class OutputIsNotFileOrDirError(DvcException):
    def __init__(self, path):
        msg = "output '{}' is not a file or directory".format(path)
        super(OutputIsNotFileOrDirError, self).__init__(msg)


class OutputAlreadyTrackedError(DvcException):
    def __init__(self, path):
        msg = "output '{}' is already tracked by scm (e.g. git)".format(path)
        super(OutputAlreadyTrackedError, self).__init__(msg)


class OutputBase(object):
    IS_DEPENDENCY = False

    REMOTE = None

    PARAM_PATH = 'path'
    PARAM_CACHE = 'cache'
    PARAM_METRIC = 'metric'
    PARAM_METRIC_TYPE = 'type'
    PARAM_METRIC_XPATH = 'xpath'

    METRIC_SCHEMA = Or(None, bool,
                       {Optional(PARAM_METRIC_TYPE): Or(str, None),
                        Optional(PARAM_METRIC_XPATH): Or(str, None)})

    DoesNotExistError = OutputDoesNotExistError
    IsNotFileOrDirError = OutputIsNotFileOrDirError

    def __init__(self,
                 stage,
                 path,
                 info=None,
                 remote=None,
                 cache=True,
                 metric=False):
        self.stage = stage
        self.project = stage.project
        self.url = path
        self.info = info
        self.remote = remote or self.REMOTE(self.project, {})
        self.use_cache = False if self.IS_DEPENDENCY else cache
        self.metric = False if self.IS_DEPENDENCY else metric

        if self.use_cache and getattr(self.project.cache,
                                      self.REMOTE.scheme) is None:
            raise DvcException("no cache location setup for '{}' outputs."
                               .format(self.REMOTE.scheme))

    def __repr__(self):
        return "{class_name}: '{url}'".format(
            class_name=type(self).__name__,
            url=(self.url or 'No url')
        )

    def __str__(self):
        return self.url

    @classmethod
    def match(cls, url):
        return re.match(cls.REMOTE.REGEX, url)

    def group(self, name):
        match = self.match(self.url)
        if not match:
            return None
        return match.group(name)

    @classmethod
    def supported(cls, url):
        return cls.match(url) is not None

    @property
    def scheme(self):
        return self.REMOTE.scheme

    @property
    def path(self):
        return self.path_info['path']

    @property
    def sep(self):
        return '/'

    @property
    def exists(self):
        return self.remote.exists(self.path_info)

    def changed(self):
        if not self.exists:
            return True

        if not self.use_cache:
            return self.info != self.remote.save_info(self.path_info)

        return getattr(self.project.cache, self.scheme).changed(self.path_info,
                                                                self.info)

    def status(self):
        if self.changed():
            # FIXME better msgs
            return {str(self): 'changed'}
        return {}

    def save(self):
        if not self.use_cache:
            self.info = self.remote.save_info(self.path_info)
        else:
            self.info = getattr(self.project.cache,
                                self.scheme).save(self.path_info)

    def dumpd(self):
        ret = self.info.copy()
        ret[self.PARAM_PATH] = self.url

        if self.IS_DEPENDENCY:
            return ret

        ret[self.PARAM_CACHE] = self.use_cache

        if isinstance(self.metric, dict):
            if self.PARAM_METRIC_XPATH in self.metric \
               and not self.metric[self.PARAM_METRIC_XPATH]:
                del self.metric[self.PARAM_METRIC_XPATH]

        ret[self.PARAM_METRIC] = self.metric

        return ret

    def download(self, to_info):
        self.remote.download([self.path_info], [to_info])

    def checkout(self, force=False):
        if not self.use_cache:
            return

        getattr(self.project.cache, self.scheme).checkout(self.path_info,
                                                          self.info,
                                                          force=force)

    def remove(self, ignore_remove=False):
        self.remote.remove(self.path_info)
        if self.scheme != 'local':
            return

        if ignore_remove and self.use_cache and self.is_local:
            self.project.scm.ignore_remove(self.path)

    def move(self, out):
        if self.scheme == 'local' and self.use_cache and self.is_local:
            self.project.scm.ignore_remove(self.path)

        self.remote.move(self.path_info, out.path_info)
        self.url = out.url
        self.path_info = out.path_info
        self.save()

        if self.scheme == 'local' and self.use_cache and self.is_local:
            self.project.scm.ignore(self.path)
