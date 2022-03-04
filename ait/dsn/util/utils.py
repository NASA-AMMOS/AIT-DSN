# Advanced Multi-Mission Operations System (AMMOS) Instrument Toolkit (AIT)
#
# Copyright 2021, by the California Institute of Technology. ALL RIGHTS
# RESERVED. United States Government Sponsorship acknowledged. Any
# commercial use must be negotiated with the Office of Technology Transfer
# at the California Institute of Technology.
#
# This software may be subject to U.S. export control laws. By accepting
# this software, the user agrees to comply with all applicable U.S. export
# laws and regulations. User has the responsibility to obtain export licenses,
# or other export authority as may be required before exporting such
# information to foreign countries or providing access to foreign persons.

import os

_ROOT_DIR = os.path.abspath(os.environ.get('AIT_ROOT', os.getcwd()))

# Why DSN has it's own function when something similar is in AIT-Core?
# Well, the latter does not expand envVars, which I would like to support.

def expand_path(path, relative_to_absolute=True):
    '''
    Expands path value to replace home-dir (~), environment variables,
    and optionally, returns an absolute path.
    When converting relative paths, then the parent
    directory is presumed to be the AIT_ROOT envVar, or if not set,
    the current working directory
    :param path: Path to be expanded
    :return: Expanded, and possibly absolute, path
    '''
    expanded = path

    # Check for ~ or relative-paths
    if expanded[0] == '~':
        expanded = os.path.expanduser(expanded)

    # Expand any envvars in the path
    expanded = os.path.expandvars(expanded)

    if relative_to_absolute:
        if expanded[0] != '/':
            expanded = os.path.join(_ROOT_DIR, expanded)

        # Return the absolute path
        expanded = os.path.abspath(expanded)

    return expanded