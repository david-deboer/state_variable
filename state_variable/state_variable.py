"""General simple state variable module."""
from copy import deepcopy
from . import sv_util
from . import state_variable_meta
from .state_variable_error import StateVariableError

class StateVariable:
    """
    General state variable class to keep track of groups of parameters within a class - typically will only use
    the wrapper functions 'state' and 'reset'.

    A summary is that this class does 2 things:
        (1) acts as a gatekeeper depending on the meta parameters (and let's you view them), but primarily...
        (2) writes the state variables as attributes to this class.

    The class accepts parameters, values and othe meta data to generate state variables.  A state variable
    has the following parameters:
        state_name:  the name of the variable -- it becomes an attribute of the class.
        state_value:  the value of the state_name -- the value of the class attribute.
        state_type:  the data-type -- the expected data-type, which may or may not be ignored.
        state_description:  a description of the state variable.
    The state_name becomes an attribute of the class itself and is referenced in that manner.  Beware you don't
    overwrite it for something else or vice versa (meta_attr tries to help you not do this).  The state variables
    and its parameters may be viewed as a set to help you keep track of them.  This can be used as a base class
    or an additional namespace for state variables.

    Parameters
    ----------
    meta_label : str
        the overall label for this set of state variables
    meta_note : str 
        a note/description if desired
    meta_state : dict, str 
        state variables and their parameters (see under set_sv_state)
    meta_attr : list
        protected attributes - starts with the attributes of this module (vars(self))
    meta_verbose : bool 
        verbosity setting for the class
    meta_enforce_set : bool
        If True, a general call to set a state variable won't work unless it is already defined.  What happens
        (other than just setting the new state variable) is set by the notify_set parameter
    meta_enforce_type : bool
        If True, a call to set a state variable that does not conform ot the expected data-type won't work.
        What happens (other than not setting the new state variable value) is set by the notify_type parameter
    meta_notify_set : str, one of ['ignore', 'alert', 'error']
        ignore: will be silent on the matter (so if enforce_set is True, the variable won't get set and you
            won't be alerted))
        alert: if the state variable is not present, you will be told.  Note that if enforce_set is False, it
            will still get set to the new value.
        error: if the state variable is not present and enforce_set is True, it will raise a StateVariableError.
            if enforce_set is False, this is the same thing as 'alert'
    meta_notify_type : str one of ['ignore', 'alert', 'error']
        ignore: will be silent on the matter (so if enforce_type is True, the variable won't get set and you
            won't be alerted))
        alert: if the state variable is not present, you will be told.  Note that if enforce_type is False, it
            will still get set to the new value.
        error: if the state variable is not present and enforce_type is True, it will raise a StateVariableError.
            if enforce_type is False, this is the same thing as 'alert'
    meta_package :  str
        this is a pseudo-meta in that it helps track groups of metas (e.g. to init, or reset etc)
        when used as an argument, one can pass a dictionary of values of above, a json/yaml file or one of the
        "named" packages defined in meta_packages (currently 'init', 'reset', 'default', 'minimal', 'middle', 'maximal')
    meta_override : bool, str, dict
        this is a pseudo-meta that does a one-time override of meta parameters and then resets to previous.
        If bool, uses package 'init', if str uses that package, if dict uses those parameters
        
    """

    def __init__(self, **kwargs):
        """
        Initialize state variable class with any of the meta_parameters, i.e. only accepts meta parameters.
        If kwargs key does not start with 'meta_' it will be prepended to it (hopefully this is better...?)
        
        __Can't__ directly include state variable outside state dict

        Parameters
        ----------
        **kwargs (meta_parameters: label, note, state, attr, verbose, enforce_set, enforce_type, notify_set, notify_type, package)
            package is either a dict with appropriate meta values, or a str with the filename [and :key] of appropriate meta values
            state is either a dict with appropriate state values, or a str with the filename [and :key] of appropriate state values
                appropriate state values (either directly or in the supplied file) are discussed in sv_set_state

        """
        self.meta = state_variable_meta.Metastate()  # Make instance, but only defaults (ie don't include kwargs here)
        # Make sure they all start with 'meta_'
        kwmeta = self.meta.metalize(kwargs)
        if 'meta_attr' in kwmeta:  # Collect attributes to avoid overwriting
            kwmeta['meta_attr'] += dir(self)
        else:
            kwmeta['meta_attr'] = dir(self)
        self.state(**kwmeta)  # Include them here to get checked by state

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

    def sv_set_state(self, **kwargs):
        """
        See <state>: functional internal version to set states, generally called by self/child.state method.

        Has three overall options (see examples below)
            1 - meta_...=...                                 # can change a number of things - see examples
                meta_state has to be either a filename:[key], list of dicts of states, dict of state_name/_value pairs
            2 - state_name='frequency', state_value=1420     # has to at least have those, can only change one state
            3 - frequency=1420, bandwidth=20                 # any number of state_name/state_value pairs

        Parameters
        ----------
        **kwargs: Change a state variable or one-time change a meta (i.e. to initialize etc).
                  All kwarg keys will begin with either meta_ or state_, except for an actual state.
                  A special flag called 'meta_init' is included to allow for one-time initialization.
                  Examples of the different call types:
                    # Starts with meta_
                    meta_label = 'This State' (see list of meta parameters in state_variable_meta.py, but state is one)
                    ...meta_state has a few options
                    meta_state = 'a_file_with_states.json/yaml:[...keys]'  (conforms to below)
                    meta_state = [{'state_name': 'ThisState', 'state_value': ThisValue}, ] (has to at least have state_name/_value, or...)
                    meta_state = {'ThisState': {'state_value': ThisValue}}
                    meta_state = {'frequency': 1420, 'bandwidth': 20}
                    # Starts with state_
                    state_name='frequency', state_value=1420.0, state_type='float', state_description='Frequency in MHz' (at least state_name/_value)
                    # Is just a state/value pair(s)
                    frequency = 1420, bandwith=20, etc

        """
        if not len(kwargs):
            self.meta.mlist(show_full=False)  # Just show values and return
            return
        kwmeta = {'state': {}}
        for k, v in kwargs.items():
            if k.startswith('state_'):
                kwmeta['state'].setdefault(kwargs['state_name'], {})
                kwmeta['state'][kwargs['state_name']][k] = deepcopy(v)
            elif k == 'meta_state':
                kwmeta['state'].update(sv_util._dict_from_input_(v))
            elif k.startswith('meta_'):
                kwmeta[k[5:]] = deepcopy(v)  # Strip off the 'meta_'
            else:
                kwmeta['state'][k] = {'state_name': k, 'state_value': deepcopy(v)}
        self.meta.mset(**kwmeta)  # Update the meta_data
        # Copy state parameters to attributes
        for k, val in self.meta.state.items():
            setattr(self, k, val['state_value'])

    def reset(self, override_yn=None):
        """
        This is a wrapper around sv_reset_state
        """
        self.sv_reset_state(override_yn=override_yn)

    def sv_reset_state(self, override_yn=None):
        """
        Delete state attributes and empty meta_state.

        Parameter
        ---------
        override_yn :
            If anything other than None, it will skip the yn safeguard query.
            
        """
        if override_yn is None:
            yn = input("This will delete all state variables and metadata.  Do you wish to continue (y/n)? ")
        else:
            yn = override_yn
        if sv_util._bool_from_input_(yn):
            for this_state in self.meta.state:
                delattr(self, this_state)
            self.meta.reset_state_key()
        elif self.meta.verbose:
            print("Not deleting state.")