State Variable

pip install 'state_variable @ git+https://github.com/david-deboer/state_variable@main'

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
                    meta_state = {'frequency': {'state_value': 1420}}
                    meta_state = {'frequency': 1420, 'bandwidth': 20}
                    # Starts with state_
                    state_name='frequency', state_value=1420.0, state_type='float', state_description='Frequency in MHz' (at least state_name/_value)
                    # Is just a state/value pair(s)
                    frequency = 1420, bandwith=20, etc
