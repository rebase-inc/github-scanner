import logging

LOGGER = logging.getLogger()

def get_python_module_names(tree, base_tree):
    known_modules = set()
    if not tree:
        return known_modules
    for entry in tree:
        try:
            if isinstance(entry, git.Tree):
                new_modules = get_python_module_names(entry, base_tree)
                known_modules.update(new_modules)
            elif entry.name == '__init__.py':
                path_relative_to_repo = entry.path.replace(base_tree.path, '')
                module_name = os.path.dirname(path_relative_to_repo).replace('/', '.')
                known_modules.add(module_name)
        except Exception as exc:
            LOGGER.error('Unhandled exception in git tree traversal: {}'.format(str(exc)))
            LOGGER.error(str(dir(entry)))
    return known_modules
