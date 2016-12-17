import os
import json
import base64
import logging

from collections import defaultdict, Counter
from functools import lru_cache

import git

from asynctcp import BlockingTCPClient

LOGGER = logging.getLogger()

class LanguageKnowledge(object):
    
    def __init__(self, name, parser_host, parser_port, private_namespace_generator, standard_library_namespace_generator):
        self.private_module_use = defaultdict(list)
        self.standard_module_use = defaultdict(list)
        self.external_module_use = defaultdict(list)

        self.name = name
        self.private_namespace_generator = private_namespace_generator
        self.standard_library_namespace = standard_library_namespace_generator()
        self.parser = BlockingTCPClient(parser_host, parser_port, encode = base64.b64encode, decode = lambda d: d.decode())

    def parse_code(self, code):
        if not code:
            return Counter()
        use_dict = self.parser.send(code)
        return Counter(json.loads(use_dict))

    def get_private_namespace(self, tree):
        #tree = HashableTree(tree)
        return self._get_private_namespace(tree)

    @lru_cache()
    def _get_private_namespace(self, tree):
        return self.private_namespace_generator(tree)


    def add_knowledge_data(self, authored_datetime, private_namespace, use_before, use_after, allow_unrecognized = True):
        for module in (use_before | use_after):
            use_delta = abs(use_before[module] - use_after[module])

            if module in private_namespace:
                self.private_module_use[module] += [ authored_datetime for _ in range(use_delta) ]

            elif module in self.standard_library_namespace:
                self.standard_module_use[module] += [ authored_datetime for _ in range(use_delta) ]

            elif allow_unrecognized or module in self.external_module_use:
                self.external_module_use[module] += [ authored_datetime for _ in range(use_delta) ]


    def analyze_diff(self, diff, commit):
        _namespace_before = self.get_private_namespace(commit.parents[0].tree)
        private_namespace = _namespace_before.union(self.get_private_namespace(commit.tree))

        use_before = self.parse_code(commit.parents[0].tree[diff.a_path].data_stream.read() if not diff.new_file else None)
        use_after = self.parse_code(commit.tree[diff.b_path].data_stream.read() if not diff.deleted_file else None)
        self.add_knowledge_data(commit.authored_datetime, private_namespace, use_before, use_after)


    def analyze_blob(self, blob, commit):
        use_before = self.parse_code(None)
        use_after = self.parse_code(commit.tree[blob.path].data_stream.read() if not diff.deleted_file else None)
        self.add_knowledge_data(commit.authored_datetime, private_namespace, use_before, use_after)

class PythonKnowledge(LanguageKnowledge):
    NAME = 'python'

    def __init__(self):
        super().__init__(self.NAME, 'python_parser', 25252, lambda tree: self.get_python_module_names(tree, tree), self.get_python_standard_library_names)

    def get_python_module_names(self, tree, base_tree):
        known_modules = set()
        if not tree:
            return known_modules
        for entry in tree:
            try:
                if isinstance(entry, git.Tree):
                    new_modules = self.get_python_module_names(entry, base_tree)
                    known_modules.update(new_modules)
                elif entry.name == '__init__.py':
                    path_relative_to_repo = entry.path.replace(base_tree.path, '')
                    module_name = os.path.dirname(path_relative_to_repo).replace('/', '.')
                    known_modules.add(module_name)
            except Exception as exc:
                LOGGER.error('Unhandled exception in git tree traversal: {}'.format(str(exc)))
                LOGGER.error(str(dir(entry)))
        return known_modules

    @classmethod
    def get_python_standard_library_names(cls):
        from stdlib_list import stdlib_list, long_versions
        known_standard_library_modules = set()
        for version in long_versions:
            known_standard_library_modules = known_standard_library_modules.union(set(stdlib_list(version)))
        return known_standard_library_modules

