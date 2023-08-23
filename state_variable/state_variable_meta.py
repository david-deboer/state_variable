"""General simple state variable module."""
from copy import copy, deepcopy
from . import sv_util


class Metastate:
    parameters = {
        'label': {'type': (str), 'choices': None, 'default': 'StateVarDef'},
        'note': {'type': (str), 'choices': None, 'default': 'StateVariable class'},
        'state': {'type': (dict), 'choices': None, 'default': {}},
        'verbose': {'type': (bool), 'choices': [True, False], 'default': False},
        'enforce_set': {'type': (bool), 'choices': [True, False], 'default': False},
        'enforce_type': {'type': (bool), 'choices': [True, False], 'default': False},
        'notify_set': {'type': (str), 'choices': ['ignore', 'alert', 'error'], 'default': 'alert'},
        'notify_type': {'type': (str), 'choices': ['ignore', 'alert', 'error'], 'default': 'alert'},
        'package': {'type': (str, dict), 'choices': None, 'default': 'default'}
        }
    state_key_defaults = {'state_name': None, 'state_value': None, 'state_type': 'auto', 'state_description': None}

    def __init__(self, **kwargs):
        """
        Initialize state variable class with any of the metastate parameters.

        Note that actual 'state' changes done here are only done within the metastate dictionary, not the state variable attribute.

        Parameters
        ----------
        **kwargs (parameters: label, note, state, verbose, enforce_set, enforce_type, notify_set, notify_type, package)
            package is either a dict with appropriate meta values, or a str with the filename [and :key] of appropriate meta values
            state is either a dict with appropriate state values, or a str with the filename [and :key] of appropriate state values
                "appropriate state values" (either directly or in the supplied file) are e.g.:
                    state = {'frequency': {'state_value': 1420.0, 'state_type': 'float', 'state_description': 'Frequency in MHz'},
                     'bandwidth': {'state_value': 1.0, 'state_type': 'float', 'state_description': 'Bandwidth in MHz'}}
                    state = {'frequency': 1420.0, 'bandwidth': 1.0}

        """
        self._make_defined_packages_()
        for k, v in self.parameters.items():
            setattr(self, k, copy(v['default']))
        self.mset(**kwargs)

    def _svm_alert_(self, msg):
        return f"ALERT:MSV[{self.label}]: {msg}"

    def _make_defined_packages_(self):
        # default, minimal, middle, maximal, reset, init
        self.defined_pkg = {'default': {'package': 'default'}}
        for k in ['verbose', 'enforce_set', 'enforce_type', 'notify_set', 'notify_type']:
            self.defined_pkg['default'][k] = self.parameters[k]['default']
        self.defined_pkg['minimal'] = {'package': 'minimal', 'verbose': False,
                                       'enforce_set': False, 'enforce_type': False,
                                       'notify_set': 'ignore', 'notify_type': 'ignore'}
        self.defined_pkg['middle'] = {'package': 'middle', 'verbose': True,
                                      'enforce_set': True, 'enforce_type': False,
                                      'notify_set': 'alert', 'notify_type': 'alert'}
        self.defined_pkg['maximal'] = {'package': 'maximal', 'verbose': True,
                                       'enforce_set': True, 'enforce_type': True,
                                       'notify_set': 'error', 'notify_type': 'error'}
        self.defined_pkg['init'] = {'package': 'init',
                                    'enforce_set': False, 'enforce_type': False,
                                    'notify_set': 'ignore', 'notify_type': 'ignore'}

    def get_package(self, package):
        """
        Provide package of metastates given an input "package" name or dict.

        If a dict is supplied, it adds it to self.defined_pkg, as supplied name or 'user'

        Parameter
        ---------
        package : None, str or dict
            If None, returns empty dict.
            If dict, returns same dict but with 'package' name if not present.
            If str, (a) endswith .json/.yaml/.yml will read files
                    (b) can be one of the "defined" packages from _make_defined_packages_
                    Other strings are just ignored and an empty dict is returned.

        Returns
        -------
        dict
            The return dict has keys that correspond to the metastate parameters.

        """
        this_package = {}
        if package in ['none', 'None', None]:
            return {}
        if isinstance(package, dict):
            if 'package' not in package or package['package'] is None:
                package['package'] = 'user'
            self.defined_pkg[package['package']] = deepcopy(package)
            this_package = package
        elif package.endswith('.json') or package.endswith('.yaml') or package.endswith('.yml'):
            this_package = {'package': package}
            this_package.update(sv_util._dict_from_input_(package))
        elif package in self.defined_pkg:
            this_package = self.defined_pkg[package]
        cull_package = list(this_package.keys())
        for this_key in cull_package:
            if this_key not in self.parameters:
                if self.verbose:
                    print(f"Warning: {this_key} is not a valid metastate parameter.")
                del this_package[this_key]
        if len(this_package) == 1 and list(this_package.keys())[0] == 'package':
            return {}
        return deepcopy(this_package)

    def _process_meta_key_val_(self, this_key, this_val):
        """
        Get a valid metastate value for a single metastate 'this_key'.

        This ensures that the value is of the appropriate type and choices.
        
        Parameters
        ----------
        this_key : str
           Must be one of the metastate parameters.
        this_val : metastate parameter types
           Must be a value of one of the metastate parameters types or derived from it.
        
        Returns
        -------
        The value derived for that metastate parameter -- it IS one of the metastate parameter types or INVALID|.
        """
        key_lower = this_key.lower()
        if key_lower not in self.parameters:
            return f"{sv_util.INVALID}|{this_key}"
        if key_lower.startswith('enforce') or key_lower == 'verbose':
            return sv_util._bool_from_input_(this_val)
        if key_lower.startswith('notify'):
            if this_val.lower() in self.parameters[key_lower]['choices']:
                return this_val.lower()
            print(f"Invalid {this_key} choice [{this_val}] - must be one of {self.parameters[key_lower]['choices']}")
            print(f"Returning {self.parameters[key_lower]['choices'][-1]}")
            return copy(self.parameters[key_lower]['choices'][-1])
        if key_lower == 'state':
            return self._poke_statevar_dict_(this_val)
        if self.parameters[key_lower]['choices'] is None and isinstance(this_val, self.parameters[key_lower]['type']):
            return this_val
        elif isinstance(self.parameters[key_lower]['choices'], list) and this_val in self.parameters[key_lower]['choices']:
            return this_val
        return f"{sv_util.INVALID}|{this_key}={this_val}"

    def _poke_statevar_dict_(self, state2update):
        """
        Make complete state attribute dictionary given updates in state2update.
        
        Called from _proecss_meta_key_val_

        Parameter
        ---------
        state2update : something handleable by sv_utils._dict_from_input_

        Returns
        -------
        dict
            Contains values for all of the metastate state:  state_name, state_value, etc

        """
        state2update = sv_util._dict_from_input_(state2update)
        if state2update is None:
            return {}
        return_state = {}
        if 'state_name' in state2update:
            tmp = {state2update['state_name']: {}}
            tmp[state2update['state_name']].update(state2update)
            state2update = deepcopy(tmp)
        for sv_name, sv_val in state2update.items():
            if sv_name in self.state:
                update_state = deepcopy(self.state[sv_name])
            else:
                update_state = {}
                for k, v in self.state_key_defaults.items():
                    update_state[k] = deepcopy(v)
            if isinstance(sv_val, dict):
                if self.verbose and 'state_name' in sv_val and sv_val['state_name'] != sv_name:
                    print(f"{sv_name} != {sv_val['state_name']} -> using {sv_name}")
                update_state.update(sv_val)    
            else:
                raise ValueError("The new state_variable scheme shouldn't get here")
            update_state['state_name'] = copy(sv_name)
            update_state['state_type'] = sv_util._type_from_input_(update_state['state_type'], update_state['state_value'])
            return_state[sv_name] = deepcopy(update_state)
        return return_state

    def mset(self, **kwargs):
        """
        Check and set the internal state - can change everything regardless of enforcement.

        This is the workhorse method that sets the metastate parameters, where the work is done in _process_meta_key_val_

        Parameters
        ----------
        **kwargs (parameters: label, note, state, verbose, enforce_set, enforce_type, notify_set, notify_type, package)
            appropriate state values are e.g.:
                'file_with_info.yaml' or 
               {'frequency': {'state_value': 1420.0, 'state_type': 'float', 'state_description': 'Frequency in MHz'},
                'bandwidth': {'state_value': 1.0, 'state_type': 'float', 'state_description': 'Bandwidth in MHz'}}
               {'frequency': 1420.0, 'bandwidth': 1.0}

        Attributes
        ----------
        sets the appropriate self.metastate attributes

        """
        if not len(kwargs):
            return
        if 'package' in kwargs:
            setargs = self.get_package(kwargs['package'])
            del kwargs['package']
        else:
            setargs = {}
        setargs.update(kwargs)

        if 'verbose' in setargs:  # Do 1st since used below.
            self.verbose = self._process_meta_key_val_('verbose', setargs['verbose'])
            del setargs['verbose']

        actually_updated = False
        for this_key, this_val in setargs.items():
            value = self._process_meta_key_val_(this_key, this_val)
            if isinstance(value, str) and value.startswith(sv_util.INVALID):
                if self.verbose:
                    print(self._svm_alert_(f"{value.split('|')[1]} not allowed metastate option"))
            elif isinstance(value, dict):
                getattr(self, this_key).update(deepcopy(value))
            else:
                if getattr(self, this_key) != value:
                    actually_updated = True
                setattr(self, this_key, deepcopy(value))
        if 'package' not in setargs and actually_updated:
            self.package = 'user'

    def reset_state_key(self):
        """Since dicts get updated, not overwritten, this allows a reset."""
        if self.verbose:
            print("This will erase all of the current state keys.")
        self.state = {}

    def mlist(self, show_full=True, max_entry_len=50):
        """
        Lists the states and metastates (if show_full).

        Parameter
        ---------
        show_full : bool
            If True, will include the metastates.

        """
        if show_full:
            print("Internal state:  ")
            for k in self.parameters:
                if k != 'state':
                    print("\t{:12s}   {}".format(k, getattr(self, k)))
        print("State variables:")
        table = []
        maxlen = {'state_name': 4, 'state_value': 5, 'state_type': 4, 'state_description': 11}
        hdr = ['Name', 'Value', 'Type', 'Description']
        _tr = int(max_entry_len / 2 - 2)
        for k in self.state:
            row = []
            for sk in ['state_name', 'state_value', 'state_type', 'state_description']:
                value = str(self.state[k][sk])
                if len(value) > max_entry_len:
                    value = '{}....{}'.format(value[:_tr], value[-_tr:])
                row.append(value)
                if len(value) > maxlen[sk]:
                    maxlen[sk] = len(value)
            table.append(row)
        spacer = ['-'*maxlen['state_name'], '-'*maxlen['state_value'], '-'*maxlen['state_type'], '-'*maxlen['state_description']] 
        print()
        print(f"{hdr[0]:{maxlen['state_name']}s} | {hdr[1]:{maxlen['state_value']}s} | {hdr[2]:{maxlen['state_type']}s} | {hdr[3]:{maxlen['state_description']}s}")
        print(f"{spacer[0]}-+-{spacer[1]}-+-{spacer[2]}-+-{spacer[3]}")
        for row in table:
            print(f"{row[0]:{maxlen['state_name']}s} | {row[1]:{maxlen['state_value']}s} | {row[2]:{maxlen['state_type']}s} | {row[3]:{maxlen['state_description']}s}")
        print(f"{spacer[0]}-+-{spacer[1]}-+-{spacer[2]}-+-{spacer[3]}")


    def to_dict(self, skip_state=False, update_meta=False):
        """
        Return the full metastate as a dictionary or old/new/flag if update_state is not None.

        Parameters
        ----------
        skip_state : bool
            Won't include the 'state' metavariable if True.
        update_state : False or dict
            If dict, it will return an "uber" dict of 'old'/'new' differences.

        """
        kwargs_par = {}
        if isinstance(update_meta, dict) and not len(update_meta):
            return kwargs_par # An empty dictionary is returned as a null update_state
        for k in self.parameters:
            if k == 'state' and skip_state:
                continue
            current_entry = copy(getattr(self, k))
            if not update_meta:
                kwargs_par[k] = current_entry
            elif k in update_meta:
                new_entry = self._process_meta_key_val_(k, update_meta[k])
                if new_entry != sv_util.INVALID and new_entry != current_entry:
                    kwargs_par.setdefault('old', {})
                    kwargs_par.setdefault('new', {})
                    kwargs_par['old'][k] = current_entry
                    kwargs_par['new'][k] = new_entry
        return kwargs_par