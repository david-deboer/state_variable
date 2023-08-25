"""General simple state variable module."""
from copy import deepcopy
from . import sv_util
from . import state_variable_meta
from .state_variable_error import StateVariableError

class StateVariable:
    """
    General state variable class to keep track of groups of parameters within a class.

    A summary is that this class does 2 things:
        (1) acts as a gatekeeper depending on the meta parameters, but primarily
        (2) writes the state variables as attributes to this class.

    The class accepts parameters, values and othe meta data to generate state variables.  A state variable
    has the following parameters:
        state_name:  the name of the variable -- it becomes an attribute of the class.
        state_value:  the value of the state_name -- the value of the class attribute.
        state_type:  the data-type -- the expected data-type, which may or may not be ignored.
        state_description:  a description of the state variable.
    The state_name becomes an attribute of the class itself and is referenced in that manner.  Beware you don't
    overwrite it for something else or vice versa.  The state variables and its parameters may be viewed as a set
    to help you keep track of them.  This can be used as a base class or an additional namespace for state variables.

    Parameters
    ----------
    label : str
        the overall label for this set of state variables
    note : str 
        a note/description if desired
    state : dict, str 
        state variables and their parameters (see the keys in state_variable_meta.Metastate.state_key_defaults
    attr : list
        protected attributes - starts with the attributes of this module (vars(self))
    verbose : bool 
        verbosity setting for the class
    enforce_set : bool
        If True, a general call to set a state variable won't work unless it is already defined.  What happens
        (other than just setting the new state variable) is set by the notify_set parameter
    enforce_type : bool
        If True, a call to set a state variable that does not conform ot the expected data-type won't work.
        What happens (other than not setting the new state variable value) is set by the notify_type parameter
    notify_set : str, one of ['ignore', 'alert', 'error']
        ignore: will be silent on the matter (so if enforce_set is True, the variable won't get set and you
            won't be alerted))
        alert: if the state variable is not present, you will be told.  Note that if enforce_set is False, it
            will still get set to the new value.
        error: if the state variable is not present and enforce_set is True, it will raise a StateVariableError.
            if enforce_set is False, this is the same thing as 'alert'
    notify_type : str one of ['ignore', 'alert', 'error']
        ignore: will be silent on the matter (so if enforce_type is True, the variable won't get set and you
            won't be alerted))
        alert: if the state variable is not present, you will be told.  Note that if enforce_type is False, it
            will still get set to the new value.
        error: if the state variable is not present and enforce_type is True, it will raise a StateVariableError.
            if enforce_type is False, this is the same thing as 'alert'
    package :  str
        this is a pseudo-meta in that it helps track groups of metas (e.g. to init, or reset etc)
        when used as an argument, one can pass a dictionary of values of above, a json/yaml file or one of the
        "named" packages defined in meta_packages (currently 'init', 'reset', 'default', 'minimal', 'middle', 'maximal')

    """

    def __init__(self, **kwargs):
        """
        Initialize state variable class with any of the meta_parameters.
        
        __Can't__ directly include state variable outside state dict

        Parameters
        ----------
        **kwargs (meta_parameters: label, note, state, attr, verbose, enforce_set, enforce_type, notify_set, notify_type, package)
            package is either a dict with appropriate meta values, or a str with the filename [and :key] of appropriate meta values
            state is either a dict with appropriate state values, or a str with the filename [and :key] of appropriate state values
                "appropriate state values" (either directly or in the supplied file) are e.g.:
                    {'frequency': {'state_value': 1420.0, 'state_type': 'float', 'state_description': 'Frequency in MHz'},
                     'bandwidth': {'state_value': 1.0, 'state_type': 'float', 'state_description': 'Bandwidth in MHz'}}
                    {'frequency': 1420.0, 'bandwidth': 1.0}
                    {'state_name': 'frequency', 'state_value': 1420.0, 'state_type': 'float', 'state_description': 'Frequency in MHz'}

        """
        if 'attr' in kwargs:
            kwargs['attr'] += dir(self)
        else:
            kwargs['attr'] = dir(self)
        self.meta = state_variable_meta.Metastate(**kwargs)
        for k in self.meta.state:
            setattr(self, k, self.meta.state[k]['state_value'])

    def _sv_alert_(self, msg):
        return f"ALERT:SV[{self.meta.label}]: {msg}"

    def state(self, **kwargs):
        """
        Show or set the state_variables -- this is the wrapper around the "workhorse" method sv_set_state.

        This is the internal method -- if a parent, may wish to recast state to do specific instructions/checking.

        Some examples:
        <>.state(a_new_variable=a_new_value)

        Parameters
        ----------
        **kwargs: Change a state variable or one-time change a meta (i.e. to initialize etc).
                  All names will begin with either meta_ or state_, except for an actual state.

        """
        self.sv_set_state(**kwargs)

    def reset_state(self, override_yn=None):
        """
        Delete state attributes and empty meta_state.

        Parameter
        ---------
        override_yn :
            If anything other than None, it will skip the yn safeguard query.
            
        """
        if override_yn is None:
            yn = input("This will delete all state variables.  Do you wish to continue (y/n)? ")
        else:
            yn = override_yn
        if sv_util._bool_from_input_(yn):
            for this_state in self.meta.state:
                delattr(self, this_state)
            self.meta.reset_state_key()
        elif self.meta.verbose:
            print("Not deleting state.")

    def _process_sv_set_state_kwargs_(self, **kwargs):
        """Takes input kwargs and packages them for meta.mset"""
        kwproc = {'state': {}}
        if 'meta_init' in kwargs and kwargs['meta_init']:
            kwproc.update(self.meta.get_package('init'))
            del(kwargs['meta_init'])
        for k, v in kwargs.items():
            if k.startswith('meta_'):
                mpar = k[5:]
                kwproc[mpar] = deepcopy(v)
            elif k.startswith('state_'):
                this_state_name = kwargs['state_name']   # has to have state_name if any state_
                kwproc['state'].setdefault(this_state_name, {})
                kwproc['state'][this_state_name][k] = deepcopy(v)
            else:
                kwproc['state'][k] = {'state_name': k, 'state_value': deepcopy(v)}
        return kwproc

    def sv_set_state(self, **kwargs):
        """
        See <state>: functional internal version to set states, generally called by self/child.state method.

        Parameters
        ----------
        **kwargs: Change a state variable or one-time change a meta (i.e. to initialize etc).
                  All kwarg keys will begin with either meta_ or state_, except for an actual state.
                  A special flag called 'meta_init' is included to allow for one-time initialization.
                  Appropriate meta_state values are e.g.:
                      'file_with_info.yaml/json' or 
                     {'frequency': {'state_value': 1420.0, 'state_type': 'float', 'state_description': 'Frequency in MHz'},
                      'bandwidth': {'state_value': 1.0, 'state_type': 'float', 'state_description': 'Bandwidth in MHz'}}
                     {'frequency': 1420.0, 'bandwidth': 1.0}
                  Appropriate state values are e.g.:
                     state_name='frequency', state_value=1420.0, state_type='float', state_description='Frequency in MHz'
                  or
                     frequency=1420, bandwidth=1.0
            Generally, you'll use the last...

        """
        if not len(kwargs):
            self.meta.mlist(show_full=False)  # Just show values and return
            return
        kwargs = self._process_sv_set_state_kwargs_(**kwargs)
        if 'state' not in kwargs or not len(kwargs['state']):
            if self.meta.verbose:
                print("Nothing to update.")
            return
        # Change meta for this time if present.
        reset_par = self.meta.to_dict(update_meta=kwargs)
        if reset_par:
            if self.meta.verbose:
                print(f"Modifying meta parameters to {reset_par['new']}")
            self.meta.mset(**reset_par['new'])

        state2update = sv_util._dict_from_input_(kwargs['state'])  # Allows to read json/yaml files and keys therein

        # Check if state variables already exist
        eliminate_keys = []
        if self.meta.enforce_set:
            for k in state2update:
                if k not in self.meta.state:
                    eliminate_keys.append(k)
                    if self.meta.notify_set == 'alert':
                        print(self._sv_alert_(f"!!!Not setting {k} since not a state variable."))
                    elif self.meta.notify_set == 'error':
                        raise StateVariableError(self._sv_alert_(f"{k} is not a state variable."))
        else:
            for k in state2update:
                if k not in self.meta.state and self.meta.notify_set in ['alert', 'error']:
                    print(self._sv_alert_(f"Setting {k} to {state2update[k]} even though it is new."))
        for k in eliminate_keys:
            del state2update[k]

        # Check if state variable types are compliant
        eliminate_keys = []
        for k, v in state2update.items():
            checking_type = {'state_type': self.meta.state_key_defaults['state_type'],
                             'state_value': self.meta.state_key_defaults['state_value']}
            for this_check in checking_type:
                if this_check == v:
                    checking_type[this_check] = v[this_check]
                elif k in self.meta.state and this_check in self.meta.state[k]:
                    checking_type[this_check] = self.meta.state[k][this_check]
            this_state_type = sv_util._type_from_input_(checking_type['state_type'], checking_type['state_value'])
            if this_state_type is None or type(checking_type['state_value']) == this_state_type:
                continue # all is OK
            if self.meta.enforce_type:
                eliminate_keys.append(k)
                if self.meta.notify_type == 'alert':
                    print(self._sv_alert_(f"!!!Not setting {k} since not {v['state_type']}"))
                elif self.meta.notify_type == 'error':
                    raise StateVariableError(self._sv_alert_(f"Incorrect type for {k} - should be {v['state_type']}"))
            else:
                if self.meta.notify_type in ['alert', 'error']:
                    print(self._sv_alert_(f"Setting {k} to {state2update[k]} even though not {v['state_type']}."))
        for k in eliminate_keys:
            del state2update[k]

        # First update the underlying meta state
        self.meta.mset(state = state2update)
        # Copy meta state parameters back to self attributes
        for k in state2update:
            setattr(self, k, self.meta.state[k]['state_value'])

        if reset_par:
            if self.meta.verbose:
                print(f"Resetting meta parameters to {reset_par['old']}")
            self.meta.mset(**reset_par['old'])