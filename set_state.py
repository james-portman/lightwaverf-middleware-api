import homeassistant.remote as remote
from homeassistant.const import STATE_ON, STATE_OFF

api = remote.API('127.0.0.1', 'password')

def set_state(item, state):
    current_state = remote.get_state(api, item)
    print("Current",current_state.as_dict())
    remote.set_state(api, item, new_state=state, attributes=current_state.as_dict()['attributes'])

# set_state('switch.radiator', STATE_ON)
set_state('input_select.radiator', 'On')
