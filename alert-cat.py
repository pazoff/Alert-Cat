from cat.mad_hatter.decorators import tool, hook, plugin
from cat.log import log
from .earthquakes import check_and_send_earthquakes, get_recent_earthquakes, format_earthquake_results, stop_checking, draw_map
import threading
from pydantic import BaseModel

# Settings

# Default values
default_earthquake_min_magnitude = 3.5
default_min_latitude = 35
default_max_latitude = 48
default_min_longitude = 22
default_max_longitude = 48
default_earthquake_check_interval_seconds = 300

class AlertCatSettings(BaseModel):
    earthquake_min_magnitude: float = default_earthquake_min_magnitude
    earthquake_check_interval_seconds: int = default_earthquake_check_interval_seconds
    min_latitude: float = default_min_latitude
    max_latitude: float = default_max_latitude
    min_longitude: float = default_min_longitude
    max_longitude: float = default_max_longitude
    

# Give your settings schema to the Cat.
@plugin
def settings_schema():
    return AlertCatSettings.schema()


alert_thread = None

@hook
def agent_fast_reply(fast_reply, cat):
    return_direct = True
    global alert_thread

    # Get user message from the working memory
    message = cat.working_memory["user_message_json"]["text"]

    if message.endswith('!!stop') or message.endswith('!!start') or message.endswith('!!alert'):
        # Load settings
        settings = cat.mad_hatter.get_plugin().load_settings()
        earthquake_min_magnitude = settings.get("earthquake_min_magnitude")
        earthquake_check_interval_seconds = settings.get("earthquake_check_interval_seconds")
        min_latitude = settings.get("min_latitude")
        max_latitude = settings.get("max_latitude")
        min_longitude = settings.get("min_longitude")
        max_longitude = settings.get("max_longitude")
        
        # Set default value for missing or invalid setting
        if (earthquake_min_magnitude is None) or (earthquake_min_magnitude < 1):
            earthquake_min_magnitude = default_earthquake_min_magnitude

        if (earthquake_check_interval_seconds is None) or (earthquake_check_interval_seconds < 60):
            earthquake_check_interval_seconds = default_earthquake_check_interval_seconds

        if not min_latitude:
            min_latitude = default_min_latitude

        if not max_latitude:
            max_latitude = default_max_latitude

        if not min_longitude:
            min_longitude = default_min_longitude

        if not max_longitude:
            max_longitude = default_max_longitude

    
        if message.endswith('!!stop'):
            if alert_thread is not None and alert_thread.is_alive():
                if stop_checking():
                    return {"output": "Earthquakes notifications <b>OFF</b>"}
                else:
                    return {"output": "Error stopping earthquakes notifications."}
            else:
                return {"output": "Cannot stop. Earthquakes notifications are <b>already OFF</b>"}

        if message.endswith('!!start'):
            if alert_thread is not None and alert_thread.is_alive():
                return {"output": "Cannot start. Earthquakes notifications are <b>already ON</b>"}

            if alert_thread is None or not alert_thread.is_alive(): 
                alert_thread = threading.Thread(target=check_and_send_earthquakes, args=(cat, earthquake_min_magnitude, earthquake_check_interval_seconds), kwargs={'minlatitude': min_latitude, 'maxlatitude': max_latitude, 'minlongitude': min_longitude, 'maxlongitude': max_longitude})
                alert_thread.start()
                return {"output": "Earthquakes notifications <b>ON</b>"}

        if message.endswith('!!alert'):
            message = message[:-4]
            recent_earthquakes = format_earthquake_results(get_recent_earthquakes(earthquake_min_magnitude, minlatitude=min_latitude, maxlatitude=max_latitude, minlongitude=min_longitude, maxlongitude=max_longitude))
            log.warning(str(recent_earthquakes))
            cat.send_ws_message(content=f'<b>Alert Cat: Recent Earthquakes Report. Magnitude above {earthquake_min_magnitude}</b>', msg_type='chat')
            if draw_map(max_latitude, max_longitude, min_longitude, min_latitude):
                cat.send_ws_message(content=f'You are getting report for earthquakes from <a href="/admin/assets/geo-location-map.html" target="_blank">this</a> region.<br>You can set your location coordinates in the plugin settings.', msg_type='chat')
            return {"output": str(recent_earthquakes)}

    return None
