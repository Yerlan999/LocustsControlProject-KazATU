from shapely.geometry import Polygon, MultiPolygon, Point, mapping
import os, json, random, pyproj, requests, csv, codecs, sys
from django.http import JsonResponse
from django.shortcuts import render
import matplotlib.pyplot as plt
from bs4 import BeautifulSoup
import plotly.express as px
import geopandas as gpd
import numpy as np
import urllib.request
import urllib.error
import pandas as pd


forecast_parameters = [
"temperature_2m_max",
"temperature_2m_min",
"apparent_temperature_max",
"apparent_temperature_min",
"precipitation_sum",
"rain_sum",
"showers_sum",
"snowfall_sum",
"precipitation_hours",
"precipitation_probability_max",
"precipitation_probability_min",
"precipitation_probability_mean",
"weathercode",
"sunrise",
"sunset",
"windspeed_10m_max",
"windgusts_10m_max",
"winddirection_10m_dominant",
"shortwave_radiation_sum",
"et0_fao_evapotranspiration",
"uv_index_max",
"uv_index_clear_sky_max",]

history_parameters = [
"temperature_2m_max",
"temperature_2m_min",
"apparent_temperature_max",
"apparent_temperature_min",
"precipitation_sum",
"rain_sum",
"snowfall_sum",
"precipitation_hours",
"weathercode",
"sunrise",
"sunset",
"windspeed_10m_max",
"windgusts_10m_max",
"winddirection_10m_dominant",
"shortwave_radiation_sum",
"et0_fao_evapotranspiration",]


last_main_description = ""

def get_weather_mapping():
    global last_main_description

    url = "https://www.nodc.noaa.gov/archive/arc0021/0002199/1.1/data/0-data/HTML/WMO-CODE/WMO4677.HTM"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    weather_mapping = {}

    for i_table, table in enumerate(soup.select('table[BORDER]')):
        for i_row, row in enumerate(table.find_all('tr')[1:]):
            code_and_description = row.find_all('td')[:2]
            code = int(code_and_description[0].text.strip())
            description = code_and_description[1].text.strip()
            if not description.startswith("-"):
                last_main_description = description
            else:
                description = last_main_description
            weather_mapping[code] = description


    return weather_mapping

def weather_code_to_string(wmo_code):
    return weather_mapping.get(wmo_code, "Unknown Weather Code")

# Generate the weather mapping
weather_mapping = get_weather_mapping()


def apply_params_to_URL(URL, parameters):
    URL += "&daily="
    for i, parameter in enumerate(parameters):
        if i < len(parameters) - 1:
            URL += parameter + ","
        else:
            URL += parameter
    URL += "&timezone=auto"

#     print("URL updated: ", URL)
    return URL

def make_API_request(URL):
    try:
        # Convert from bytes to text
        resp_text = urllib.request.urlopen(URL).read().decode('UTF-8')
        # Use loads to decode from text
        json_obj = json.loads(resp_text)
#         print("Successfull API request!")
        return json_obj
    except urllib.error.HTTPError  as e:
        ErrorInfo= e.read().decode()
        print('Error code: ', e.code, ErrorInfo)
        sys.exit()
    except  urllib.error.URLError as e:
        ErrorInfo= e.read().decode()
        print('Error code: ', e.code,ErrorInfo)
        sys.exit()



def index(request):

    os.chdir("gismodel")

    main_shapefile_path = "geoBoundaries-KAZ-ADM0-all//geoBoundaries-KAZ-ADM0.geojson"
    shapefile_path = "geoBoundaries-KAZ-ADM1-all//geoBoundaries-KAZ-ADM1.geojson"
    shapefile_path = "geoBoundaries-KAZ-ADM2-all//geoBoundaries-KAZ-ADM2.geojson"

    shapefile_path = "kaz_adm_unhcr_2023_shp//kaz_admbnda_adm2_unhcr_2023.shp"

    gdf = gpd.read_file(shapefile_path)
    random_numbers = np.random.normal(30, 40, len(gdf))
    random_numbers = np.clip(random_numbers, 0, 100)
    rounded_numbers = np.round(random_numbers).astype(int)

    gdf['density'] = rounded_numbers

    main_gdf = gpd.read_file(main_shapefile_path)

    latitude, lonitude = main_gdf.geometry.centroid[0].xy[0][0], main_gdf.geometry.centroid[0].xy[1][0]

    target_crs = 'EPSG:4326'
    transformer = pyproj.Transformer.from_crs(gdf.crs, target_crs, always_xy=True)

    def reproject_geometry(geom):
        if isinstance(geom, Polygon):
            transformed_coords = [transformer.transform(x, y) for x, y in geom.exterior.coords]
            return Polygon(transformed_coords)
        elif isinstance(geom, MultiPolygon):
            reprojected_parts = [Polygon([transformer.transform(x, y) for x, y in part.exterior.coords]) for part in geom.geoms]
            return MultiPolygon(reprojected_parts)
        elif isinstance(geom, Point):
            x, y = transformer.transform(coords[0][0], coords[0][1])
            print(x, y)
            return Point(x, y)
        else:
            raise ValueError("Unsupported geometry type")

    gdf['geometry'] = gdf['geometry'].apply(reproject_geometry)
    gdf["centroid"] = gdf.geometry.centroid
    gdf.crs = target_crs

    geojson_data = gdf.to_json(default=mapping)
    context = {
        "geojson_data": geojson_data,
        "center_of_map": (latitude, lonitude),
    }
    os.chdir("..")
    return render(request, "gismodel/main.html", context)



def ajax_request(request):
    if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest' and request.method == 'GET':

        query_params = request.GET

        adm1_name = query_params.get('adm1_name', None)
        adm2_name = query_params.get('adm2_name', None)
        shape_lat = query_params.get('shape_lat', None)
        shape_lon = query_params.get('shape_lon', None)

        URL = f'https://api.open-meteo.com/v1/forecast?latitude={shape_lat}&longitude={shape_lon}&past_days=2&forecast_days=16'
        URL = apply_params_to_URL(URL, forecast_parameters)
        forecast_json_obj = make_API_request(URL)
        forecast_df = pd.DataFrame(forecast_json_obj["daily"])

        json_data = forecast_df.to_json(orient='records')
        # data = {'message': 'Ajax Back!'}
        return JsonResponse(json_data, safe=False)
