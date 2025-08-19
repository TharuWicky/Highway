import marimo

__generated_with = "0.14.13"
app = marimo.App(width="columns")

with app.setup:
    import marimo as mo
    import folium
    import io
    from lxml import etree as parser
    import math
    import osmnx as ox
    from shapely.geometry import Polygon,Point,LineString
    import geopandas as gpd
    import matplotlib.pyplot as plt


@app.cell
def _():
    single_point_form = mo.md(
        '''
        # Single Point Selection

        Latitude: {lat}
    
        Longitude: {lon}
        '''
    ).batch(lat=mo.ui.text(),lon=mo.ui.text()).form()


    kml_form = mo.md(
        '''
        # Upload KML File of Area of Interest

        {file}
        '''
    ).batch(file=mo.ui.file(kind='area')).form()

    input_points = mo.ui.tabs(
        {"Single Point": single_point_form,
        "KML File": kml_form
        }
    )
    input_points
    return input_points, kml_form, single_point_form


@app.cell
def _():
    get_optimal_point,set_optimal_point = mo.state(None)
    get_area_select, set_area_select = mo.state(None)
    return (
        get_area_select,
        get_optimal_point,
        set_area_select,
        set_optimal_point,
    )


@app.cell
def _(
    input_points,
    kml_form,
    load_kml_file,
    set_area_select,
    set_optimal_point,
    single_point_form,
):
    def _():
        set_optimal_point(None)
        set_area_select(None)
        if(input_points.value=='Single Point'):
            if(not single_point_form.value):
                return
            
            optimal_point = (float(single_point_form.value['lon']),
                             float(single_point_form.value['lat']))
            set_optimal_point(optimal_point)
            set_area_select(None)
        if(input_points.value=='KML File'):
            if(not kml_form.value):
                return
            if(kml_form.value['file'] is None):
                return
            _file_content = kml_form.value['file'][0].contents
            _file_object = io.BytesIO(_file_content)
            polygon_points = load_kml_file(_file_object)
            set_area_select(polygon_points)
            set_optimal_point(None)
    _()
    return


@app.cell
def _(get_area_select, get_optimal_point, input_points):
    def _():
        if(input_points.value == 'Single Point'):
            optimal_point = get_optimal_point()
            if(optimal_point is None):
                return
            map = folium_plot_points(
                [optimal_point],
                colors=["#008800"],
                fill=True,
                radius=10,
                zoom_start=14,
                tooltip=["Optimal Point"],
                popup=["Optimal Point"]
            )
            return mo.iframe(map.get_root().render())
        if(input_points.value == "KML File"):
            polygon_points = get_area_select()
            if(polygon_points is None):
                return
            map = folium_draw_polygon(
                polygon_points,
                color='blue',
                fill=True,
                fill_opacity=0.5,
                zoom_start=14
            )
            return mo.iframe(map.get_root().render())
        return None

    mo.md(f'''
    # Input Visualization

    {_()}
    ''')
    return


@app.cell
def _(get_area_select):
    def _post_processing():
        if(get_area_select() is None):
            return
        radio =  mo.ui.radio(
            ["Choose Area as Points","Find Bridges in Area"]
        )
        form = mo.md(
            '''
            # Area Post Processing

            {radio}
            '''
        ).batch(radio=radio).form()
        return form
    
    post_proc =_post_processing() 
    post_proc
    return (post_proc,)


@app.cell
def _():
    get_selected_points,set_selected_points = mo.state(None)
    return (set_selected_points,)


@app.cell
def _(get_area_select, post_proc, set_selected_points):
    def _():
        if(post_proc is None or post_proc.value is None):
            return
        if(post_proc.value['radio'] == "Choose Area as Points"):
            set_selected_points(get_area_select())
            map = folium_plot_points(
                get_area_select(),
                colors=["#0000FF"] * len(get_area_select()),
                fill=True,
                radius=5,
                zoom_start=14,
                tooltip=["Area Point"] * len(get_area_select()),
                popup=["Area Point"] * len(get_area_select())
            ) 
            return map
        if(post_proc.value['radio'] == "Find Bridges in Area"):
            map,points= calculate_bridge_points(get_area_select())
            set_selected_points(points)
            folium_plot_points(
                points,
                colors=["#00FF00"] * len(points),
                fill=True,
                radius=2,
                zoom_start=14,
                tooltip=["Bridge Point"] * len(points),
                popup=["Bridge Point"] * len(points),
                M=map
            ) 
        
                
            return map

    _()

    return


@app.function
def calculate_bridge_points(polygon_points):
    with mo.status.spinner(title="Loading Road Network Data") as spinner:
        _all_graph = extract_road_network_from_polygon(polygon_points)
        _motor_graph = extract_motor_way_from_polygon(polygon_points)
        bridges = extract_bridges_from_graph(_all_graph)
        _,_motor_edges = ox.convert.graph_to_gdfs(_motor_graph)
        m = _motor_edges.explore(style_kwds=dict(color='black'))
        bridges_map = bridges.explore(m=m,style_kwds=dict(color='red',weight=5))
        bridge_points = bridges['geometry'].apply(
            lambda x: LineString(x).interpolate(0.5,normalized=True).coords[0]).tolist()
        # return mo.iframe(bridges_map.get_root().render())
        # bridge_points = (_motor_edges['geometry'].apply(lambda x: LineString(x).coords[0]).to_list())
        return bridges_map,bridge_points
    return None


@app.function(column=1)
def folium_plot_points(points, colors=None, fill=True, radius=3, zoom_start=12,tooltip=None,popup = None,M=None
):
    mean_point = (
        sum(p[1] for p in points) / len(points),
        sum(p[0] for p in points) / len(points),
    )
    if(not M):
        m = folium.Map(location=(mean_point), zoom_start=zoom_start)
    else:
        m = M
    if(tooltip is None):
        tooltip = (None for _ in points)
    if(popup is None):
        popup = (None for _ in points)
    if(colors is None):
        colors = ("#008800" for _ in points)
    for point,color,t,pop in zip(points,colors,tooltip,popup):
        folium.CircleMarker(
            location=(point[1], point[0]), color=color, fill=fill,fill_opacity=1, radius=radius,tooltip=t,popup=pop
        ).add_to(m)
    return m


@app.cell
def _():
    def load_kml_file(file):
        tree = parser.parse(file)
        root = tree.getroot()
        namespace = {"kml": "http://www.opengis.net/kml/2.2"}
        polygons = root.xpath("//kml:Polygon", namespaces=namespace)
        coords_str = ""

        for polygon in polygons:
            coordinates = polygon.xpath(".//kml:coordinates", namespaces=namespace)
            for coord in coordinates:
                coords_str += coord.text.strip() + " "  # Collect the coordinates

        # Now coords_str contains all the coordinates from the KML file
        # Remove any trailing spaces
        coords_str = coords_str.strip()

        # Split the string by spaces first, then by commas
        coords_list = [coord.split(",") for coord in coords_str.split()]

        # Convert the coordinates into pairs of (longitude, latitude) tuples, ignoring the z-coordinate
        formatted_coords = [(float(coord[0]), float(coord[1])) for coord in coords_list]
        return formatted_coords


    # with open("fyp1.kml", "rb") as file:
    #     print(load_kml_file(file))

    return (load_kml_file,)


@app.cell
def _():


    def segment_length(p1, p2):
        return math.hypot(p2[0] - p1[0], p2[1] - p1[1])

    def find_polyline_midpoint(points):
        if len(points) < 2:
            raise ValueError("At least two points are required")

        # Step 1: Compute total length
        lengths = [segment_length(points[i], points[i+1]) for i in range(len(points)-1)]
        total_length = sum(lengths)
        half_length = total_length / 2

        # Step 2: Traverse to the segment containing midpoint
        accumulated = 0
        for i, seg_len in enumerate(lengths):
            if accumulated + seg_len >= half_length:
                # Step 3: Interpolate in this segment
                remain = half_length - accumulated
                ratio = remain / seg_len
                x = points[i][0] + ratio * (points[i+1][0] - points[i][0])
                y = points[i][1] + ratio * (points[i+1][1] - points[i][1])
                return (x, y)
            accumulated += seg_len
        print("reached here")
        # Should not reach here
        return points[-1]

    return


@app.function
def extract_road_network_from_polygon(point_collection):
    polygon = Polygon(point_collection)
    G = ox.graph_from_polygon(polygon,retain_all=True,network_type='all',truncate_by_edge=True)
    return G


@app.function
def extract_motor_way_from_polygon(point_collection):
    polygon = Polygon(point_collection)
    G_motorway = ox.graph_from_polygon(polygon,retain_all=True,network_type='all',truncate_by_edge=True,custom_filter='["highway"~"motorway"]')
    return G_motorway


@app.function
def extract_bridges_from_graph(G):
    graph_nodes,graph_edge = ox.convert.graph_to_gdfs(G)
    bridge_edges = graph_edge[graph_edge['bridge'] == 'yes'][graph_edge['highway']!='motorway']
    return bridge_edges


@app.function
def folium_draw_polygon(points, color='blue', fill=True, fill_opacity=0.5, zoom_start=12):
    mean_point = (
        sum(p[1] for p in points) / len(points),
        sum(p[0] for p in points) / len(points),
    )
    m = folium.Map(location=(mean_point), zoom_start=zoom_start)
    folium.Polygon(
        locations=[(p[1], p[0]) for p in points],
        color=color,
        fill=fill,
        fill_opacity=fill_opacity
    ).add_to(m)
    return m


@app.cell(column=2)
def _():
    _system_selection = mo.ui.radio(
        [
            "Solar",
            "Wind",
            "Hybrid"
        ]
    )
    system_selection_form = mo.md(
        '''
        # System Selection
        {system_selection}
    
        '''
    ).batch(system_selection=_system_selection).form()
    system_selection_form
    return (system_selection_form,)


@app.cell
def _():
    get_system,set_system = mo.state(None)

    return (set_system,)


@app.cell
def _(set_system, system_selection_form):
    def _():
        set_system(None)
        if(system_selection_form is None or system_selection_form.value is None):
            return
        set_system(
            system_selection_form.value['system_selection']
        )
    _()
    return


if __name__ == "__main__":
    app.run()
