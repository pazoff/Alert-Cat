import requests
import time
from datetime import datetime
import threading
import folium


def get_recent_earthquakes_emsc(min_magnitude, minlatitude=35, maxlatitude=48, minlongitude=22, maxlongitude=48):
    try:
        url = f"https://www.seismicportal.eu/fdsnws/event/1/query?format=json&minmagnitude={min_magnitude}&orderby=time&limit=10&minlatitude={minlatitude}&maxlatitude={maxlatitude}&minlongitude={minlongitude}&maxlongitude={maxlongitude}"
        response = requests.get(url)
        response.raise_for_status()  # Raises an exception for 4xx/5xx status codes
        data = response.json()
        filtered_data = [quake for quake in data['features'] if quake['properties']['mag'] >= min_magnitude]
        return filtered_data
    except requests.exceptions.RequestException as e:
        print("Error fetching data:", e)
        return None
    except KeyError as e:
        print("KeyError:", e)
        return None


def draw_map(maxlat, maxlon, minlon, minlat):
    try:
        # Calculate the center of the bounding box
        center_lat = (maxlat + minlat) / 2
        center_lon = (maxlon + minlon) / 2

        # Create a Folium map centered at the calculated center
        m = folium.Map(location=[center_lat, center_lon], zoom_start=5)

        # Draw a rectangle overlay for the bounding box
        folium.Rectangle(bounds=[[minlat, minlon], [maxlat, maxlon]], color='blue', fill=True, fill_color='blue', fill_opacity=0.2).add_to(m)

        # Save the map as an HTML file
        m.save('/admin/assets/geo-location-map.html')

        return True
    
    except Exception as e:
        print("An error occurred:", e)
        return False


def get_recent_earthquakes(min_magnitude, minlatitude=35, maxlatitude=48, minlongitude=22, maxlongitude=48):
    try:
        earthquakes = get_recent_earthquakes_emsc(min_magnitude, minlatitude=minlatitude, maxlatitude=maxlatitude, minlongitude=minlongitude, maxlongitude=maxlongitude)
        #print(str(earthquakes))
        results = []
        for quake in earthquakes:
            mag = quake['properties']['mag']
            place = quake['properties']['flynn_region']
            time_str = quake['properties']['time']
            url = "https://www.seismicportal.eu/eventdetails.html?unid=" + quake['id']
            result = {
                'Magnitude': mag,
                'Location': place,
                'Time': time_str,
                'URL': url
            }
            results.append(result)
        return results
    except Exception as e:
        print("Error:", e)
        return None


def format_earthquake_results(earthquake_data):
    try:
        if earthquake_data is None:
            return "No earthquake data available."

        result_string = "<b>Recent Earthquakes:</b><br><br>"
        for idx, quake in enumerate(earthquake_data, start=1):
            result_string += f"<b>{idx}: {quake['Location']}</b>\n"
            result_string += f"Magnitude: {quake['Magnitude']}\n"
            result_string += f"Location: {quake['Location']}\n"
            result_string += f"Time: {quake['Time']}\n"
            result_string += f"URL: <a href='{quake['URL']}' target='_blank'>more info</a><br><br>"  # Add an empty line between earthquakes

        return result_string
    except Exception as e:
        return f"Error occurred while formatting earthquake results: {e}"

stop_flag = threading.Event()

def stop_checking():
    global stop_flag
    try:
        stop_flag.set()
        return True
    except Exception as e:
        print("Error while stopping checking:", e)
        return False

def check_and_send_earthquakes(cat, min_magnitude, check_interval, minlatitude=35, maxlatitude=48, minlongitude=22, maxlongitude=48):
    global stop_flag, alert_thread
    last_quake_time = 0

    while not stop_flag.is_set():
        try:
            print("Alert Cat: CHECKING for new earthquakes ...")
            earthquakes = get_recent_earthquakes_emsc(min_magnitude, minlatitude=minlatitude, maxlatitude=maxlatitude, minlongitude=minlongitude, maxlongitude=maxlongitude)
            for quake in earthquakes:
                time_epoch = datetime.strptime(quake['properties']['time'], "%Y-%m-%dT%H:%M:%S.%fZ").timestamp()
                if time_epoch > last_quake_time:
                    mag = quake['properties']['mag']
                    place = quake['properties']['flynn_region']
                    depth = quake['properties']['depth']
                    url = f"https://www.seismicportal.eu/eventdetails.html?unid={quake['id']}"
                    message = f"[{time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(time_epoch + 7200))}]\nMagnitude {mag} earthquake detected at {place}.\nDepth(Km): {depth}\nSee more details <a href='{url}' target='_blank'>here</a>."
                    
                    cat.send_ws_message(content=f'<b>Alert Cat: Earthquake Report. Magnitude above {min_magnitude}</b>', msg_type='chat')
                    cat.send_ws_message(content=message, msg_type='chat')
                    print(str(message))
                    
                    last_quake_time = time_epoch
            print("Alert Cat: FINISHED check for new earthquakes.")
        except Exception as e:
            print("Error:", e)
        
        #time.sleep(check_interval)
        stop_flag.wait(check_interval)

    stop_flag.clear()
    print("Alert Cat: Earthquakes notifications STOPPED.")
    #cat.send_ws_message(content='<b>Alert Cat: Earthquakes notifications stopped</b>', msg_type='chat')



