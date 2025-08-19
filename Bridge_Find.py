import osmnx as ox
from shapely.geometry import Polygon
import geopandas as gpd
import xml.etree.ElementTree as ET
import pandas as pd
import folium

# --- STEP 1: Load Polygon from KML ---
def load_polygon_from_kml(kml_path):
    ns = {"kml": "http://www.opengis.net/kml/2.2"}
    tree = ET.parse(kml_path)
    root = tree.getroot()
    coords_text = root.find(".//kml:coordinates", ns).text.strip()
    coords = [(float(c.split(",")[0]), float(c.split(",")[1])) for c in coords_text.split()]
    return Polygon(coords)

# --- STEP 2: Define KML path and load polygon ---
kml_path = r"C:\Users\tharu\Videos\EE405\Codes\fyp2.kml"  # ← change this path
polygon = load_polygon_from_kml(kml_path)

# --- STEP 3: Load graphs inside the polygon ---
G_drive = ox.graph_from_polygon(polygon, network_type='drive')
G_all = ox.graph_from_polygon(polygon, network_type='all')

# --- STEP 4: Convert graphs to GeoDataFrames using updated OSMnx API ---
gdf_drive_nodes, gdf_drive_edges = ox.convert.graph_to_gdfs(G_drive)
gdf_all_nodes, gdf_all_edges = ox.convert.graph_to_gdfs(G_all)

# --- STEP 5: Filter bridges in full network that are NOT part of drivable edges (bridges OVER roads) ---
bridges_all = gdf_all_edges[gdf_all_edges["bridge"] == "yes"]
bridges_over_roads = bridges_all[~bridges_all.index.isin(gdf_drive_edges.index)]

# --- STEP 6: Reproject to a projected CRS (for accurate centroid calculations) ---
bridges_over_roads_proj = bridges_over_roads.to_crs(epsg=5234)  # Sri Lanka projected CRS

# --- STEP 7: Calculate centroid and convert back to WGS84 (EPSG:4326) ---
bridge_coords = bridges_over_roads_proj.geometry.centroid.to_crs(epsg=4326)
bridge_df = pd.DataFrame({
    "Longitude": bridge_coords.x,
    "Latitude": bridge_coords.y,
    "Name": bridges_over_roads.get("name", "Unknown")
})

# --- STEP 8: Save bridge data ---
bridge_df.to_csv("bridges_crossing_roads.csv", index=False)
print("✅ Bridges crossing drivable roads saved to 'bridges_crossing_roads.csv'")

# --- STEP 9: Create Folium map for easy viewing ---
map_center = [polygon.centroid.y, polygon.centroid.x]
m = folium.Map(location=map_center, zoom_start=14)

for _, row in bridge_df.iterrows():
    folium.Marker(
        location=[row["Latitude"], row["Longitude"]],
        popup=row["Name"] if pd.notna(row["Name"]) else "Unnamed Bridge",
        icon=folium.Icon(color="blue", icon="road", prefix="fa")
    ).add_to(m)

m.save("bridges_crossing_roads_map.html")
print("✅ Interactive map saved as 'bridges_crossing_roads_map.html'")
