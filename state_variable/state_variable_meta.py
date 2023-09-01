"""General simple state variable module."""
from copy import copy, deepcopy
from tabulate import tabulate
from . import sv_util
from .state_variable_error import StateVariableError


class Metastate:
    parameters = {
        'label': {'type': (str), 'choices': None, 'default': 'StateVarDef'},
        'note': {'type': (str), 'choices': None, 'default': 'StateVariable class'},
        'state': {'type': (dict), 'choices': None, 'default': {}},
        'attr': {'type': (list), 'choices': None, 'default': []},
        'verbose': {'type': (bool), 'choices': [True, False], 'default': False},
        'enforce_set': {'type': (bool), 'choices': [True, False], 'default': False},
        'enforce_type': {'type': (bool), 'choices': [True, False], 'default': False},
        'notify_set': {'type': (str), 'choices': ['ignore', 'alert', 'error'], 'default': 'ignore'},
        'notify_type': {'type': (str), 'choices': ['ignore', 'alert', 'error'], 'default': 'ignore'},
        'package': {'type': (str, dict), 'choices': None, 'default': 'default'},
        'override': {'type': (bool, str, dict), 'choices': None, 'default': False}
        }
    state_key_defaults = {'state_name': None, 'state_value': None, 'state_type': 'auto', 'state_description': None}

    def __init__(self, **kwargs):
        """
        Initialize state variable class with any of the metastate parameters.

        Note that actual 'state' changes done here are only done within the metastate dictionary, not the state variable attribute.

        Parameters
        ----------
        **kwargs (parameters: label, note, state, attr, verbose, enforce_set, enforce_type, notify_set, notify_type, package)
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

    def metalize(self, kwargs):
        """
        Makes sure all kwargs keys start with 'meta_' --> used in state_variable.

        Parameters _into_ state_variable use the meta_ prefix
        Parameters _into_ state_variable_meta don't

        I'm hoping to make this easier by doing this, but we'll see.
        """
        metalize = {}
        for key, val in kwargs.items():
            if key.startswith('meta_'):
                if key[5:] in self.parameters:
                    metalize[key] = val
                else:
                    raise ValueError(f"{key} not a valid metastate parameter.")
            else:
                if key in self.parameters:
                    metalize[f"meta_{key}"] = val
                else:
                    raise ValueError(f"{key} not a valid metastate parameter.")
        return metalize

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

    def apply_package(self, package):
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
           Must be one of the metastate parameters.  State is handled separately
        this_val : metastate parameter types
           Must be a value of one of the metastate parameters types or derived from it.
        
        Returns
        -------
        The value derived for that metastate parameter -- it IS one of the metastate parameter types or INVALID|.
        """
        if this_key not in self.parameters:
            return f"{sv_util.INVALID}|{this_key}"
        if this_key == 'state':
            print("Hmmm, you shouldn't be here...")
            return
        if this_key.startswith('enforce') or this_key == 'verbose':
            return sv_util._bool_from_input_(this_val)
        if this_key.startswith('notify'):
            if this_val.lower() in self.parameters[this_key]['choices']:
                return this_val.lower()
            print(f"Invalid {this_key} choice [{this_val}] - must be one of {self.parameters[this_key]['choices']}")
            print(f"Returning {self.parameters[this_key]['choices'][-1]}")
            return copy(self.parameters[this_key]['choices'][-1])
        if self.parameters[this_key]['choices'] is None and isinstance(this_val, self.parameters[this_key]['type']):
            return this_val
        elif isinstance(self.parameters[this_key]['choices'], list) and this_val in self.parameters[this_key]['choices']:
            return this_val
        return f"{sv_util.INVALID}|{this_key}={this_val}"

    def _complies(self, update_state):
        """
        # Check if state variable types are compliant
        # 'enforce_set': {'type': (bool), 'choices': [True, False], 'default': False},
        # 'enforce_type': {'type': (bool), 'choices': [True, False], 'default': False},
        # 'notify_set': {'type': (str), 'choices': ['ignore', 'alert', 'error'], 'default': 'ignore'},
        # 'notify_type': {'type': (str), 'choices': ['ignore', 'alert', 'error'], 'default': 'ignore'},

        """
        entry_complies = True
        if isinstance(update_state['state_type'], type) and type(update_state['state_value']) != update_state['state_type']:
            msg = f"incorrect type for {update_state['state_name']}: {type(update_state['state_value'])} should be {update_state['state_type']}"
            preamble = 'Setting value although'
            if self.enforce_type:
                entry_complies = False
                preamble = 'Not setting value since'
            if self.notify_type == 'alert':
                print(self._svm_alert_(f"{preamble} {msg}"))
            elif self.notify_type == 'error':
                raise StateVariableError(self._svm_alert_(msg))
        if update_state['state_name'] not in self.state:
            msg = f"{update_state['state_name']} is not a defined state variable."
            preamble = "Setting value although"
            if self.enforce_set:
                entry_complies = False
                preamble = "Not setting value since"
            if self.notify_set == 'alert':
                print(self._svm_alert_(f"{preamble} {msg}"))
            elif self.notify_set == 'error':
                raise StateVariableError(self._svm_alert_(msg))
        return entry_complies

    def _update_meta_state_parameter(self, meta_state):
        """
        Make complete state attribute dictionary given updates in metastate

        Parameter
        ---------
        states2update : something handleable by sv_utils._dict_from_input_

        """
        for sv_name, sv_val in sv_util._dict_from_input_(meta_state).items():
            if sv_name in self.state:
                update_state = deepcopy(self.state[sv_name])
            else:
                update_state = {}  # Make new with defaults.
                for k, v in self.state_key_defaults.items():
                    update_state[k] = deepcopy(v)
            if isinstance(sv_val, dict) and 'state_value' in sv_val:
                if 'state_name' in sv_val:
                    if sv_val['state_name'] != sv_name:
                        print(f"{sv_name} != {sv_val['state_name']} -> using {sv_val['state_name']}")
                else:
                    sv_val['state_name'] = sv_name
                update_state.update(sv_val)
            else:
                update_state.update({'state_name': sv_name, 'state_value': sv_val})
            if update_state['state_type'] == 'auto':
                update_state['state_type'] = type(update_state['state_value'])
            if self._complies(update_state):
                self.state[update_state['state_name']] = deepcopy(update_state)
    
    def mset(self, **kwargs):
        """
        Check and set the internal state.

        This is the workhorse method that sets the metastate parameters, where the work is done in _process_meta_key_val_

        Parameters
        ----------
        **kwargs - see Metastate.parameters
            appropriate values for the 'state' parameter are e.g.:
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
        # Apply package
        if 'package' in kwargs:
            setargs = self.apply_package(kwargs['package'])
            del kwargs['package']
        else:
            setargs = {}
        setargs.update(kwargs)  #T This is the new version of kwargs with package info

        # Process verbose
        if 'verbose' in setargs:  # Do 1st since used below.
            self.verbose = self._process_meta_key_val_('verbose', setargs['verbose'])

        print("SVM279 MAKE RESET WORK WITH OVERRIDE META_ ETC")
        # reset_par = self.meta.to_dict(update_meta=kwargs)
        # if reset_par:
        #     if self.meta.verbose:
        #         print(f"Modifying meta parameters to {reset_par['new']}")
        #     self.meta.mset(**reset_par['new'])
        # # Process override
        # if 'override' in setargs:
        #     print("set override")
        reset_par = False

        # Process other meta parameters than
        skip_these = ['package', 'verbose', 'override', 'state']
        for this_key, this_val in setargs.items():
            if this_key in skip_these:
                continue
            value = self._process_meta_key_val_(this_key, this_val)
            if isinstance(value, str) and value.startswith(sv_util.INVALID):
                if self.verbose:
                    print(self._svm_alert_(f"{value.split('|')[1]} not allowed metastate option"))
            else:
                setattr(self, this_key, value)
        
        # Process meta state
        if 'state' in setargs:
            self._update_meta_state_parameter(setargs['state'])

        # Reset override if needed.
        if reset_par:
            if self.meta.verbose:
                print(f"Resetting meta parameters to {reset_par['old']}")
            self.meta.mset(**reset_par['old'])  # don't like this recursive...just use setattr()

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
        table_data = []
        keys = ['state_name', 'state_value', 'state_type', 'state_description']
        hdr = [_x.split('_')[1].capitalize() for _x in keys]
        _l = int(max_entry_len / 2 - 2)
        for k in self.state:
            table_row = []
            for sk in keys:
                value = str(self.state[k][sk])
                if len(value) > max_entry_len:
                    value = '{}....{}'.format(value[:_l], value[-_l:])
                table_row.append(value)
            table_data.append(table_row)
        print(tabulate(table_data, headers=hdr), '\n')

    def to_dict(self, update_meta=False):
        """
        Return the full metastate as a dictionary or old/new/flag if update_state is not None.

        Parameters
        ----------
        update_state : False or dict of kwargs
            If dict, it will return an "uber" dict of 'old'/'new' differences.

        """
        kwargs_par = {}
        if isinstance(update_meta, dict) and not len(update_meta):
            return kwargs_par # An empty dictionary is returned as a null update_state
        for k in self.parameters:
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