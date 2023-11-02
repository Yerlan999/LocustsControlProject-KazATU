from shapely.geometry import Polygon, MultiPolygon
from django.shortcuts import render
import matplotlib.pyplot as plt
import plotly.express as px
import geopandas as gpd
import numpy as np
import os, json
import pyproj



def index(request):

    os.chdir("gismodel")

    main_shapefile_path = "geoBoundaries-KAZ-ADM0-all//geoBoundaries-KAZ-ADM0.geojson"
    shapefile_path = "geoBoundaries-KAZ-ADM1-all//geoBoundaries-KAZ-ADM1.geojson"
    shapefile_path = "geoBoundaries-KAZ-ADM2-all//geoBoundaries-KAZ-ADM2.geojson"

    shapefile_path = "kaz_adm_unhcr_2023_shp//kaz_admbnda_adm2_unhcr_2023.shp"

    gdf = gpd.read_file(shapefile_path)
    gdf['density'] = np.random.normal(0, 1000, len(gdf))  # Example: Normal distribution

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
        else:
            raise ValueError("Unsupported geometry type")

    gdf['geometry'] = gdf['geometry'].apply(reproject_geometry)
    gdf.crs = target_crs

    geojson_data = gdf.to_json()
    context = {
        "geojson_data": geojson_data,
        "center_of_map": (latitude, lonitude),
    }
    os.chdir("..")
    return render(request, "gismodel/main.html", context)
