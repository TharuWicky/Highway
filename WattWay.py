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
    from shapely.geometry import Polygon,Point
    import geopandas as gpd
    import matplotlib.pyplot as plt


@app.cell
def _():
    kml_file_upload = mo.ui.file(kind='area')
    return (kml_file_upload,)


@app.cell
def _(kml_file_upload, kml_map):
    kml_file_input = mo.md(
        f'''
           ## Upload KML File 
            {kml_file_upload}

            <h2>Visualization of the Points</h2>

            <center>{kml_map.style(max_height='600px',max_width='900px',overflow='auto') if kml_map else mo.Html("<h3>No KML File Uploaded</h3>").center()}</center>

        '''
    )
    kml_file_input
    return (kml_file_input,)


@app.cell
def _(kml_file_upload, load_kml_file):
    kml_points=None
    if(kml_file_upload.value):
        _file_content = kml_file_upload.value[0].contents
        _file_object = io.BytesIO(_file_content)
        kml_points = load_kml_file(_file_object)
    return (kml_points,)


@app.cell
def _():
    single_point_lat_input = mo.ui.text(
        label='Latitude',
        placeholder='Enter latitude',
        value='',

    )
    single_point_long_input = mo.ui.text(
        label='Latitude',
        placeholder='Enter longitude',
        value='',

    )
    return single_point_lat_input, single_point_long_input


@app.cell
def _(single_point_lat_input, single_point_long_input):
    def float_or_none(s):
        try:
            return float(s)
        except ValueError:
            return None

    single_point_lat = float_or_none(single_point_lat_input.value)
    single_point_long = float_or_none(single_point_long_input.value)

    if(single_point_lat is None or single_point_long is None):
        single_point = None
    else:
        single_point = (single_point_long, single_point_lat)
    single_point
    return (single_point,)


@app.cell
def _(single_point_lat_input, single_point_long_input, single_point_map):
    val = (single_point_lat_input.value == 'hello')
    single_point_input = mo.md(
        f'''
           ## Singel Point Selection

           {single_point_lat_input}

           {single_point_long_input}

            <h2>Visualization of the Points</h2>
           <center>{single_point_map.style(max_height="400px",max_width="900px") if single_point_map else mo.Html("<h3>No point selected</h3>")}</center>

        '''
    )
    single_point_input
    return (single_point_input,)


@app.cell
def _(single_point):
    single_point_map = (mo.as_html(folium_plot_points( 
       points=(single_point,) ,colors=('#008800',), fill=True, radius=5, zoom_start=12,
    )) if single_point else None)

    return (single_point_map,)


@app.cell
def _(kml_points):

    kml_map = (mo.as_html(folium_plot_points( 
       points=kml_points ,colors=('#008800' for point in kml_points), fill=True, radius=5, zoom_start=12,
    )) if kml_points else None)
    return (kml_map,)


@app.cell
def _():
    get_point_state,set_point_state = mo.state('KML File')
    return get_point_state, set_point_state


@app.cell
def _(
    create_bridge_output,
    get_point_state,
    kml_file_input,
    set_point_state,
    single_point_input,
):

    input_stage = mo.ui.tabs(
        {
            'KML File': kml_file_input,
            'Single Point': single_point_input,
            'Bridge Find':create_bridge_output()
        },
        value = get_point_state(),
        on_change = lambda x: set_point_state(x) 
    )
    return (input_stage,)


@app.cell
def _(input_stage):
    mo.md(
        f"""
    # Point Selection
    {input_stage}
    """
    )
    return


@app.cell
def _(get_point_state, kml_points):
    print(get_point_state())
    point_collection = None

    if(get_point_state() == 'KML File'):
        point_collection = kml_points

    return


@app.cell
def _():
    bridge_find_kml_file = mo.ui.file(kind='area')
    # bridge_find_kml_file
    return (bridge_find_kml_file,)


@app.cell
def _(bridge_find_kml_file, load_kml_file):
    def calculate_bridge_points():
        if(bridge_find_kml_file.value):
            with mo.status.spinner(title="Loading Road Network Data") as spinner:
                _file_content = bridge_find_kml_file.value[0].contents
                _file_object = io.BytesIO(_file_content)
                polygon_points = load_kml_file(_file_object)
                _all_graph = extract_road_network_from_polygon(polygon_points)
                _motor_graph = extract_motor_way_from_polygon(polygon_points)
                bridges = extract_bridges_from_graph(_all_graph)
                _,_motor_edges = ox.convert.graph_to_gdfs(_motor_graph)
                m = _motor_edges.explore(style_kwds=dict(color='black'))
                bridges_map = bridges.explore(m=m,style_kwds=dict(color='red',weight=5))

                return mo.iframe(bridges_map.get_root().render())
        return None


    return (calculate_bridge_points,)


@app.cell
def _(bridge_find_kml_file, calculate_bridge_points):

    def create_bridge_output():
        _bridge_map = calculate_bridge_points()
        _output = mo.md(
           f'''
        # Find Bridges
        ## Upload KML File 
            {bridge_find_kml_file}
        ## Visualization:

            <center>{_bridge_map.style(max_height="400px",max_width="900px") if _bridge_map else mo.Html("<h3>No point selected</h3>")}</center>
           ''' 
        )

        return _output
    output = create_bridge_output()
    return (create_bridge_output,)


@app.function(column=1)
def folium_plot_points(points, colors=None, fill=True, radius=3, zoom_start=12,tooltip=None,popup = None
):
    mean_point = (
        sum(p[1] for p in points) / len(points),
        sum(p[0] for p in points) / len(points),
    )
    m = folium.Map(location=(mean_point), zoom_start=zoom_start)
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


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
