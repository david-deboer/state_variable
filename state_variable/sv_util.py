from copy import copy
from .state_variable_error import StateVariableError

INVALID = '_x_iNvAlId_x_'

def _dict_from_input_(inputv, list_key='state_name'):
    """Handle input to yield a dict -- inputv is either a dict or a filename:[key]."""
    if isinstance(inputv, dict):
        return inputv
    if inputv is None:
        return {}
    if isinstance(inputv, list):
        return_dict = {}
        for entry in inputv:
            return_dict[entry[list_key]] = entry
        return return_dict
    # Assume is string containing input filename
    ivsplit = inputv.split(':')
    filename = ivsplit[0]
    if filename.lower().endswith('.json'):
        import json
        with open(filename, 'r') as fp:
            readfile = json.load(fp)
    elif filename.lower().endswith('.yaml') or filename.lower().endswith('.yml'):
        import yaml
        with open(filename, 'r') as fp:
            readfile = yaml.safe_load(fp)
    if len(ivsplit) == 1:
        return readfile
    elif len(ivsplit) == 2:
        return readfile[ivsplit[1]]
    elif len(ivsplit) == 3:
        return readfile[ivsplit[1]][ivsplit[2]]
    else:
        raise StateVariableError(f"Too mamy levels ({len(ivsplit)}) in state file.")

def _bool_from_input_(inputv):
    """Produce a sensible bool."""
    if isinstance(inputv, bool):
        return copy(inputv)
    if isinstance(inputv, str):
        if inputv.lower()[0] in ['f', 'n', '0']:
            return False
        if inputv.lower()[0] in ['t', 'y', '1']:
            return True
        raise StateVariableError(f"Ambiguous bool eval ({inputv}).")
    return bool(inputv)

def _type_from_input_(inputv, etval=None):
    """Produce an appropriate data type."""
    if isinstance(inputv, type):
        return copy(inputv)
    if inputv is None:
        return None
    if isinstance(inputv, str):
        if inputv in ['str', 'int', 'float', 'complex', 'tuple', 'list', 'tuple', 'set', 'dict', 'bool']:
            return eval(inputv)
        if inputv.lower() == 'none':
            return None
        if inputv.lower() == 'auto':
            if etval is None:
                return None
            return type(etval)
        return str
    return type(inputv)
