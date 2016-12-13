import os
import ast
import git
import logging
import magic
from collections import Counter
from stdlib_list import stdlib_list, long_versions

LOGGER = logging.getLogger(__name__)

STANDARD_LIBRARY = set()
for version in long_versions:
    STANDARD_LIBRARY = STANDARD_LIBRARY.union(set(stdlib_list(version)))

class NotDecodableError(Exception):
    def __init__(self, *args, **kwargs):
        LOGGER.debug('Skipping blob due to binary encoding!')
        super().__init__(*args, **kwargs)

class MissingPathInTree(Exception):
    def __init__(self, path, *args, **kwargs):
        LOGGER.debug('Missing path {} in git tree!'.format(path))
        super().__init__('Missing path {} in git tree!'.format(path))

class ReferenceCollector(ast.NodeVisitor):

    def __init__(self, git_tree = None):
        super().__init__()
        self.private_namespace = self.__get_tree_namespaces(git_tree, git_tree.path) if git_tree else set()
        self.standard_namespace = STANDARD_LIBRARY
        self.private_counter = Counter()
        self.standard_counter = Counter()
        self.third_party_counter = Counter()

    def __add_to_counter(self, name):
        if name in self.private_namespace:
            self.private_counter.update([ name ])
        elif name in self.standard_namespace:
            self.standard_counter.update([ name ])
        else:
            self.third_party_counter.update([ name ])

    @classmethod
    def __get_tree_namespaces(cls, tree, base_path):
        known_namespaces = set()
        for entry in tree:
            if isinstance(entry, git.Tree):
                new_namespaces = cls.__get_tree_namespaces(entry, base_path)
                known_namespaces.update(new_namespaces)
            elif entry.name == '__init__.py':
                path_relative_to_repo = entry.path.replace(base_path, '')
                package_name = os.path.dirname(path_relative_to_repo).replace('/', '.')
                known_namespaces.add(package_name)
        return known_namespaces

    def visit(self, node):
        super().visit(node)
        return (self.private_counter, self.standard_counter, self.third_party_counter)

    def noop(self):
        return (self.private_counter, self.standard_counter, self.third_party_counter)

    def visit_Import(self, node):
        for name in node.names:
            self.__add_to_counter(name.asname or name.name)

    def visit_ImportFrom(self, node):
        self.__add_to_counter(node.module)

    def visit_Node(self, node):
        LOGGER.debug('Visted node with id {}'.format(node.id))
        self.__add_to_counter(self, node.id)

def parse_python(tree, path):
    if not tree:
        return ReferenceCollector().noop()
    try:
        blob = tree[path].data_stream.read()
    except KeyError as exc:
        raise MissingPathError(path)

    encoding = magic.Magic(mime_encoding = True).from_buffer(blob)
    if encoding == 'binary': raise NotDecodableError()

    collector = ReferenceCollector(tree)
    return collector.visit(ast.parse(blob.decode(encoding)))

