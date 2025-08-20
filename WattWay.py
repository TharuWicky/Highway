import marimo

__generated_with = "0.14.13"
app = marimo.App(width="full")

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
    import pandas as pd
    import openpyxl


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

    csv_form = mo.md(
        '''
        # Upload CSV File of Area of Interest
        You can use the tool given below to draw a area of interest and export it as CSV!
        {file}
        '''
    ).batch(file=mo.ui.file(kind='area')).form()
    input_points = mo.ui.tabs(
        {"Single Point": single_point_form,
        "KML File": kml_form,
         "CSV File": csv_form
        }
    )
    input_points
    return csv_form, input_points, kml_form, single_point_form


@app.cell
def _(input_points):
    mo.stop(input_points.value != 'CSV File')
    iframe_csv = mo.iframe(
        r'''
        <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <title>Draw Shapes + Export Coordinates + Search</title>
      <meta name="viewport" content="width=device-width, initial-scale=1.0">

      <!-- Leaflet CSS -->
      <link rel="stylesheet" href="https://unpkg.com/leaflet/dist/leaflet.css"/>
      <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet.draw/1.0.4/leaflet.draw.css"/>
      <link rel="stylesheet" href="https://unpkg.com/leaflet-control-geocoder/dist/Control.Geocoder.css"/>

      <style>
        #map { height: 70vh; }
        #output {
          padding: 10px;
          background: #f4f4f4;
          font-family: monospace;
          white-space: pre-wrap;
        }
        button {
          padding: 8px 12px;
          background: #007bff;
          color: white;
          border: none;
          margin: 5px;
          border-radius: 4px;
          cursor: pointer;
        }
        button:hover {
          background-color: #0056b3;
        }
      </style>
    </head>
    <body>

    <div id="map"></div>
    <div id="output">
      <button onclick="extractCoordinates()">Extract Coordinates</button>
      <button onclick="downloadCSV()">Download as CSV</button>
      <div id="coordsDisplay">🛠 Draw a polygon or path to begin.</div>
    </div>

    <!-- Leaflet & Plugins -->
    <script src="https://unpkg.com/leaflet/dist/leaflet.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet.draw/1.0.4/leaflet.draw.js"></script>
    <script src="https://unpkg.com/leaflet-control-geocoder/dist/Control.Geocoder.js"></script>

    <script>
      // Initialize map
      const map = L.map('map').setView([6.9271, 79.8612], 10); // Colombo

      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19
      }).addTo(map);

      // Add search bar using Leaflet Control Geocoder
      L.Control.geocoder({
        defaultMarkGeocode: true
      }).addTo(map);

      // Layer group for drawings
      const drawnItems = new L.FeatureGroup();
      map.addLayer(drawnItems);

      // Drawing tools
      const drawControl = new L.Control.Draw({
        draw: {
          polygon: true,
          polyline: true,
          rectangle: false,
          circle: false,
          marker: false,
          circlemarker: false
        },
        edit: {
          featureGroup: drawnItems
        }
      });
      map.addControl(drawControl);

      map.on('draw:created', function (e) {
        drawnItems.clearLayers(); // Only one shape at a time
        drawnItems.addLayer(e.layer);
        document.getElementById('coordsDisplay').textContent = '✅ Shape drawn. Click "Extract Coordinates" or "Download as CSV".';
      });

      let lastCoords = [];

      // Extract coordinates from polygon or path
      function extractCoordinates() {
        if (drawnItems.getLayers().length === 0) {
          alert("Please draw a polygon or path first.");
          return;
        }

        const layer = drawnItems.getLayers()[0];
        const latlngs = layer.getLatLngs();

        let coords = [];

        if (layer instanceof L.Polygon) {
          coords = latlngs[0].map(pt => [pt.lng, pt.lat]);
        } else if (layer instanceof L.Polyline) {
          coords = latlngs.map(pt => [pt.lng, pt.lat]);
        }

        lastCoords = coords;

        const coordText = coords.map(c => `[${c[0].toFixed(6)}, ${c[1].toFixed(6)}]`).join(",\n");
        document.getElementById('coordsDisplay').textContent = `📍 Extracted Coordinates (Lng, Lat):\n${coordText}`;
      }

      // Download coordinates as CSV
      function downloadCSV() {
        if (lastCoords.length === 0) {
          alert("Please extract coordinates first.");
          return;
        }

        let csv = "Longitude,Latitude\n";
        csv += lastCoords.map(c => `${c[0]},${c[1]}`).join("\n");

        const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "drawn_coordinates.csv";
        a.click();
        URL.revokeObjectURL(url);
      }
    </script>

    </body>
    </html>


        '''
    )
    iframe_csv

    mo.md(
        f'''
        # CSV Draw Tool for Maps
    
        {iframe_csv}

        '''
    )
    return


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
    csv_form,
    input_points,
    kml_form,
    load_kml_file,
    set_area_select,
    set_optimal_point,
    set_selected_points,
    single_point_form,
):
    def _():
        set_optimal_point(None)
        set_area_select(None)
        set_selected_points(None)
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
        if(input_points.value=='CSV File'):
            if(not csv_form.value):
                return
            if(csv_form.value['file'] is None):
                return
            _file_content = csv_form.value['file'][0].contents
            _file_object = io.BytesIO(_file_content)
            _df = pd.read_csv(_file_object)
            points = list(zip(
               _df['Longitude'] ,_df['Latitude']
            ))
            set_area_select(points)
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
        if(input_points.value == "KML File" or input_points.value=='CSV File'):
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
    _val = _()
    _output = None
    if(_val):
        _output = mo.md(f'''
        # Input Visualization
    
        {_val}
        ''')
    _output
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
    return get_selected_points, set_selected_points


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


@app.function
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


@app.cell
def _():
    import requests

    NASA_POWER_API = "https://power.larc.nasa.gov/api/"


    def get_monthly_solar_irradiation(*, latitude, longitude, start_year, end_year):
        monthly_api = f"{NASA_POWER_API}temporal/monthly/point"
        parameters = dict(
            latitude=latitude,
            longitude=longitude,
            start=start_year,
            end=end_year,
            community="RE",
            parameters="ALLSKY_SFC_SW_DWN",
            format="JSON",
            user="anonymous",
        )
        response = requests.get(monthly_api, params=parameters)
        if response.status_code != 200:
            raise Exception(
                f"Error fetching data: {response.status_code} - {response.text}"
            )
        data = response.json()
        return data["properties"]["parameter"]["ALLSKY_SFC_SW_DWN"]


    def find_average_irradiation_data(irradiation_data):
        return sum(value for _, value in irradiation_data.items()) / len(irradiation_data)

    return (
        NASA_POWER_API,
        find_average_irradiation_data,
        get_monthly_solar_irradiation,
        requests,
    )


@app.cell
def _(NASA_POWER_API, requests):
    def get_wind_data(*, latitude, longitude, start_year, end_year):
        monthly_api = f"{NASA_POWER_API}temporal/monthly/point"
        parameters = dict(
            latitude=latitude,
            longitude=longitude,
            start=start_year,
            end=end_year,
            community="RE",
            parameters="WS10M,WS2M",
            format="JSON",
            user="anonymous",
        )
        response = requests.get(monthly_api, params=parameters)
        if response.status_code != 200:
            raise Exception(
                f"Error fetching data: {response.status_code} - {response.text}"
            )
        data = response.json()
        return data["properties"]["parameter"]
    return (get_wind_data,)


@app.cell
def _(NASA_POWER_API, requests):
    def get_all_data(*, latitude, longitude, start_year, end_year):
        monthly_api = f"{NASA_POWER_API}temporal/monthly/point"
        parameters = dict(
            latitude=latitude,
            longitude=longitude,
            start=start_year,
            end=end_year,
            community="RE",
            parameters="WS10M,ALLSKY_SFC_SW_DWN",
            format="JSON",
            user="anonymous",
        )
        response = requests.get(monthly_api, params=parameters)
        if response.status_code != 200:
            raise Exception(
                f"Error fetching data: {response.status_code} - {response.text}"
            )
        data = response.json()
        return data["properties"]["parameter"]



    return (get_all_data,)


@app.cell
def _():
    def color_interpolate(value):
        red = int(value*255)
        blue = 255 -red 
        return f"#{hex(red)[2:4]:0>2}00{hex(blue)[2:4]:0>2}"

    def normalize_solar_data(values):
        max_value = max(values)
        min_value = min(values)
        if(max_value == min_value):
            return (1 for _ in values)
        return ((value - min_value) / (max_value - min_value) for value in values)
    return color_interpolate, normalize_solar_data


@app.function
def wind_power_from_speed(wind_speed):
    return wind_speed**(3.2071)/10**(1.7689)


@app.cell
def _(get_optimal_point, get_selected_points):
    def _():
        points = get_selected_points()
        optimal_point = get_optimal_point()
        if(points is None and optimal_point is None):
            return



        _year_form = mo.md(
        '''
        # Please Select Year Range for Calculating Optimal Point
        Start Year: {start_year},

        End Year: {end_year}
        '''
        )

        _start_year = mo.ui.dropdown( options=tuple(range(2000,2025)),value='2024',searchable=True)
        _end_year = mo.ui.dropdown( options=tuple(range(2000,2025)),value='2024',searchable=True)

        year_form = _year_form.batch(start_year=_start_year, end_year=_end_year).form()
        return year_form
    year_form = _()
    year_form
    return (year_form,)


@app.cell
def _(
    color_interpolate,
    find_average_irradiation_data,
    get_monthly_solar_irradiation,
    get_selected_points,
    normalize_solar_data,
    year_form,
):
    def optimal_solar():
        if(year_form is None or year_form.value is None):
            return 
        start_year = year_form.value["start_year"]
        end_year = year_form.value["end_year"]
        mo.stop(start_year is None or end_year is None)
        mo.stop(int(start_year) < int(end_year))
        points = get_selected_points()
        solar_data = {}
        for _point in mo.status.progress_bar(points,
                                             title="Retrieving Irradiation Data",
                                             subtitle="Please Wait...",
                                             show_eta=True,show_rate=True):
            monthly_data = get_monthly_solar_irradiation(longitude=_point[0], latitude=_point[1],
                                                         start_year=start_year, end_year=end_year)
            average_data = find_average_irradiation_data(monthly_data)
            solar_data[tuple(_point)] = average_data
        max_solar_data = max(solar_data.values())
        _interpolated_colors = map(color_interpolate, 
                                   normalize_solar_data(
                                       tuple(solar_data[point] for point in points)))
        Map =  folium_plot_points(points, 
                           colors=_interpolated_colors, 
                           fill=True, radius=4, zoom_start=12,
                           tooltip=(str(solar_data[point]) for point in points),
                                  popup=(str(p) for p in points))

    return


@app.cell
def _(
    find_average_irradiation_data,
    get_all_data,
    get_optimal_point,
    get_selected_points,
    year_form,
):

    def optimal_data():
        if(year_form is None or year_form.value is None):
            return 
        start_year = year_form.value["start_year"]
        end_year = year_form.value["end_year"]
        mo.stop(start_year is None or end_year is None)
        mo.stop(int(start_year) < int(end_year))
        points = get_selected_points()
        if(points is None):
            op_point = get_optimal_point()
            if(op_point is None):
                return
            points = [op_point]
        solar_data = {}
        wind_data = {}
        for _point in mo.status.progress_bar(points,
                                             title="Retrieving Irradiation Data",
                                             subtitle="Please Wait...",
                                             show_eta=True,show_rate=True):
            while True:
                try:
                    monthly_data = get_all_data(longitude=_point[0], latitude=_point[1],
                                                                 start_year=start_year,
                                                                end_year=end_year)
                except Exception:
                    mo.status.toast("Error retrieving data for point: "
                                    f"{_point}. Retrying...")
                    continue
                break
            average_data = find_average_irradiation_data(monthly_data['WS10M'])
            average_data = wind_power_from_speed(average_data)
            wind_data[tuple(_point)] = average_data
            average_data = find_average_irradiation_data(monthly_data['ALLSKY_SFC_SW_DWN'])
            average_data = wind_power_from_speed(average_data)
            solar_data[tuple(_point)] = average_data
        df = pd.DataFrame({
            "Solar Power": solar_data,
            "Wind Power": wind_data
        })
        return df

    df = optimal_data()
    return (df,)


@app.cell
def _():
    toggle_button = mo.ui.switch(label="Toggle Ordering")
    return (toggle_button,)


@app.cell
def _(color_interpolate, df, normalize_solar_data, toggle_button):
    mo.stop(df is None)
    ndf = df.reset_index().rename(columns={'level_0':'longitude','level_1':'latitude'})

    point_tuples = list(zip(ndf['longitude'].to_list(),ndf['latitude']))
    point_solar_values = ndf['Solar Power'].to_list()
    point_wind_values = ndf['Wind Power'].to_list()


    tooltips = [
        f"Solar Power: {solar_value:.2f} W/m²<br>Wind Power: {wind_value:.2f} m/s"
        for solar_value, wind_value in zip(point_solar_values, point_wind_values)
    ]

    popup = [
        f"Longitude: {longitude:.6f}<br>Latitude: {latitude:.6f}"
        for longitude, latitude in zip(ndf['longitude'], ndf['latitude'])
    ] 
    label = "Order by Solar"

    if(toggle_button.value):
        label= "Order by Solar"
        ndf = ndf.sort_values(by=['Solar Power'])
        colors = list(map(color_interpolate, 
                      normalize_solar_data(ndf['Solar Power'].to_list())))
    else:
        label= "Order by Wind"
        ndf = ndf.sort_values(by=['Wind Power'])
        colors = list(map(color_interpolate, 
                      normalize_solar_data(ndf['Wind Power'].to_list())))
    table_data = mo.ui.table(ndf,selection='single')
    return colors, label, point_tuples, popup, table_data, tooltips


@app.cell
def _(colors, label, point_tuples, popup, table_data, toggle_button, tooltips):

    _M = folium_plot_points(point_tuples,colors=colors,fill=True, radius=4, zoom_start=10,tooltip=tooltips,popup=popup)

    if(len(table_data.value)!=0):
        _selected_pp = float(table_data.value['longitude']),float(table_data.value['latitude'])

        _M = folium_plot_points([_selected_pp],colors=["#00FF00"],fill=False, radius=8,zoom_start=10,M=_M)
    mo.md(
        f'''
        # Select Point for Installation
        {toggle_button}
    
        {label}
    
        {mo.hstack([table_data,_M])}
        '''
    )
    return


@app.cell
def _(table_data):
    selected_data = None
    if(len(table_data.value) != 0):
        selected_data = table_data.value

    return (selected_data,)


@app.cell
def _(selected_data):
    mo.stop(selected_data is None)
    _radio_sys = mo.ui.radio(
        ["Solar","Wind","Hybrid"]
    )
    system_type_form = mo.md(

        '''
       # Select System Type

        {radio_sys}
        '''
    ).batch(radio_sys=_radio_sys).form()
    system_type_form
    return (system_type_form,)


@app.cell
def _(selected_data, system_type_form):

    mo.stop(system_type_form.value is None)
    mo.stop(system_type_form.value['radio_sys']!= 'Solar')
    mo.stop(selected_data is None)
    solar_type = mo.ui.dropdown(["A","B","C","D"],value="A",searchable=True)
    solar_capacity = mo.ui.dropdown([i for i in range(10,120+10,10)],searchable=True,value=10)
    solar_cal_button = mo.ui.run_button(label="Calculate")


    return solar_cal_button, solar_capacity, solar_type


@app.cell
def _():
    solar_descriptions = {
        "A": '''
    |Parameters| Value|
    |---|---|
    |Nominal efficiency|20.58%|
    |Maximum power (Pmp)| 444.860 Wdc|
    |Max power voltage (Vmp)| 76.7 Vdc|
    |Max power current (Imp)| 5.8 Adc|
    |Open circuit voltage (Voc)| 90.5 Vdc|
    |Short circuit current (Isc)| 6.2 Adc|
    ''',
        "B": '''
    |Parameters| Value|
    |---|---|
    |Nominal efficiency| 21.8%|
    |Maximum power (Pmp)| 595.080 Wdc|
    |Max power voltage (Vmp)| 34.2 Vdc|
    |Max power current (Imp)| 17.4 Adc|
    |Open circuit voltage (Voc)| 41.3 Vdc|
    |Short circuit current (Isc)| 18.5 Adc|
    ''',
        "C": '''
    |Parameters| Value|
    |---|---|
    |Nominal efficiency| 21.14%|
    |Maximum power (Pmp)| 575.014 Wdc|
    |Max power voltage (Vmp)| 44.3 Vdc|
    |Max power current (Imp)| 13.0 Adc|
    |Open circuit voltage (Voc)| 53.5 Vdc|
    |Short circuit current (Isc)| 13.7 Adc|
    ''',
        "D": '''
    |Parameters| Value|
    |---|---|
    |Nominal efficiency| 20.93%|
    |Maximum power (Pmp)| 540.015 Wdc|
    |Max power voltage (Vmp)| 41.7 Vdc|
    |Max power current (Imp)| 12.9 Adc|
    |Open circuit voltage (Voc)| 49.5 Vdc|
    |Short circuit current (Isc)| 13.8 Adc|
    '''

    }
    return (solar_descriptions,)


@app.cell
def _(solar_cal_button, solar_capacity, solar_descriptions, solar_type):
    # _capacity = mo.ui.slider(10,120+10,step=10,value=10,show_value=True)


    _form = mo.callout(mo.md(f'''
    # Define PV System Parameters

    Solar Pannel Type: {solar_type}

    Installment Capacity: {solar_capacity}

    {solar_cal_button}
    '''))

    _descript = mo.callout(mo.md(f'''
    ## Parameters for type {solar_type.value}
    {solar_descriptions[solar_type.value]}
    '''))

    mo.hstack([_form,mo.md(""),_descript],align="start",justify="start").center()
    return


@app.function
def solar_cost(solar_type,capacity):
    number_of_modules = {
	10:20,
	20:36,
	30:54,
	40:72,
	50:84,
	60:100,
	70:120,
        80:135,
	90:150,
	100:175,
	110:185,
	120:210
    }
    cost_of_inverters = {
	10:280000,
	20:330000,
	30:445000,
	40:540000,
	50:575000,
	60:615000,
	70:985000,
        80:1020000,
	90:1115000,
	100:1150000,
	110:1190000,
	120:1230000
   }
    total_cost = number_of_modules[capacity] * (25000 + 150000/140 + 1500000/140) + cost_of_inverters[capacity] 
    return total_cost


@app.cell
def _(selected_data, solar_cal_button, solar_capacity, solar_type):
    mo.stop(not solar_cal_button.value)
    solar_cost_value = solar_cost(solar_type.value,solar_capacity.value)
    solar_output_power = calculate_solar_output_power(type=solar_type.value,irradiance=float(selected_data['Solar Power']),installation=solar_capacity.value)
    mo.md(
        f'''
        # Calculated Solar Parameters

        |**Parameter**|**Value**|
        |---|---|
        |**Total Cost (Rs)**|  **{int(solar_cost_value//1000*1000):,}**|
        |**Total  Irradiance ($kW/m^2$)**|  **{float(selected_data['Solar Power']):.2f}**|
        |**Total  Estimated Power output ($kW$)**|  **{solar_output_power:.2f}**|

        '''
    ).center()
    return


@app.cell
def _(
    find_average_irradiation_data,
    get_wind_data,
    selected_data,
    system_type_form,
    year_form,
):
    mo.stop(system_type_form.value is None)
    mo.stop(system_type_form.value['radio_sys']!= 'Wind')
    mo.stop(selected_data is None)

    input_height = mo.ui.text(label="Height (m) &emsp;",value='10')
    input_cp = mo.ui.slider(0,1,0.01,label="$C_p$&emsp;&emsp;&emsp;&emsp;&ensp;",show_value=True,value=0.4)
    input_area = mo.ui.text(label="Effective Area",value='10')

    wind_form = mo.md(
        '''
        # Wind Power Calculator

        {input_height}

        {input_cp}

        {input_area}
        '''
    ).batch(input_height=input_height,
            input_cp=input_cp,
            input_area=input_area).form()


    with mo.status.spinner("Retrieving Wind Data"):
        data = get_wind_data(longitude=selected_data['longitude'],
                      latitude=selected_data['latitude'],
                      start_year=year_form.value['start_year'],
                      end_year=year_form.value['end_year'])


        average_10 = find_average_irradiation_data(
            data['WS10M']
        )
        average_2 = find_average_irradiation_data(
            data['WS2M']
        )
        wind_p = math.log(average_10/average_2)/math.log(10/2)
    wind_form
    return average_10, average_2, wind_form, wind_p


@app.cell
def _(average_10, average_2, wind_form, wind_p):
    mo.stop(wind_form.value is None)
    def _():
        p = wind_p
        h = float(wind_form.value['input_height'])
        cp = float(wind_form.value['input_cp'])
        A = float(wind_form.value['input_area'])
        rho = 1.225
        v = average_10*(h/10)**p
        Power = 0.5*rho*A*v**3*cp

        return mo.md(f'''
    # Calculated Wind Results 

    Power law formula

    $${r'v = v_\text{ref}\left(\frac{h}{h_\text{ref}}\right)^p'}$$
    - v: Wind speed at height h  
    - v_ref: Wind speed at reference height (h_ref = 2 meters for NASA POWER data)  
    - h: Height at which you want to estimate wind speed  
    - h_ref: Reference height (*2 meters* in this case)  
    - p: Power-law exponent (usually between 0.1 and 0.4 depending on terrain roughness; typically *0.143* for open terrain)  

    ---

    # The Power-Law Exponent (p)

    The power-law exponent (p), also known as the wind shear coefficient, varies depending on the terrain roughness and atmospheric stability. It determines how quickly wind speed changes with height. Here's how you can determine p:


    # Calculated Values for Wind Turbine
    | Parameter | Estimated Value|
    |---|---|
    |Wind Speed at 10m (m/s)| {average_10:.2f}|
    |Wind Speed at 2m (m/s)| {average_2:.2f}|
    |Estimated Wind Speed at {h:.2f} (m/s)| {v:.2f}|
    |Estimated p value| {p:.2f}|
    |Estimated Power (W)| {Power:.2f}|
        ''')
    _().center()
    return


@app.function
def interpolate_p(df: pd.DataFrame, gir_value: float) -> float:
    # Ensure dataframe is sorted by GIR
    df = df.sort_values("GIR")

    # Reindex with the desired gir_value included
    df_ext = df.set_index("GIR")
    if gir_value not in df_ext.index:
        df_ext.loc[gir_value] = None  # insert the gir_value

    # Sort again and interpolate linearly
    df_ext = df_ext.sort_index().interpolate(method="index")

    return df_ext.loc[gir_value, "P"]


@app.function
def calculate_solar_output_power(irradiance,type,installation):
    path = mo.notebook_location()/"public"/f"{type}.xlsx"
    df = pd.read_excel(path,sheet_name=f"{installation}kW")
    P = interpolate_p(df,irradiance)
    return P


@app.cell
def _():
    mo.md("""# Hybrid System""")
    return


@app.function
def calculate_solar_for_budget(budget,type):
    best_option = None
    for p in range(10,120+10,10):
        cost = solar_cost(type,p)
        if(cost > budget):
            return best_option
        best_option = p
    return best_option


@app.function
def calculate_max_solar_for_wind(wind_power,type,irradiance,inertia_ratio = 0.15):
    best_option = None
    for p in range(10,120+10,10):
        power = calculate_solar_output_power(
            irradiance,type,p) 
        if(power*inertia_ratio > wind_power):
            return best_option
        best_option = p
    return best_option


@app.cell
def _():

    budget = mo.ui.text(label="Budget")
    Solar_type = mo.ui.dropdown(
        ['A','B','C','D'],
        label = 'Solar Type',
        value='A',searchable=True)
    inertial_percentage = mo.ui.slider(0,100,5,label="Intertia Percentage",show_value=True)
    budget_inert_cal_button = mo.ui.run_button(label='Calculate')
    return Solar_type, budget, budget_inert_cal_button, inertial_percentage


@app.cell
def _(
    Solar_type,
    budget,
    budget_inert_cal_button,
    inertial_percentage,
    selected_data,
    solar_descriptions,
    system_type_form,
):
    mo.stop(system_type_form.value is None)
    mo.stop(system_type_form.value['radio_sys']!= 'Hybrid')
    mo.stop(selected_data is None)

    max_solar_for_intertia = mo.md(

        f'''
        # Best Solar Installation for Speicific Inertia Hybrid System

        {budget} (Must be greater than 7 Million for Hybrid SystemU)

        {Solar_type}

        {inertial_percentage}

        {budget_inert_cal_button}
        '''
    )

    mo.hstack((mo.callout(max_solar_for_intertia),mo.callout(mo.md(f"##Solar Installation Type {Solar_type.value}\n\n"+solar_descriptions[Solar_type.value]))))
    return


@app.cell
def _(
    Solar_type,
    budget,
    budget_inert_cal_button,
    inertial_percentage,
    selected_data,
    system_type_form,
):
    mo.stop(system_type_form.value is None)
    mo.stop(system_type_form.value['radio_sys']!= 'Hybrid')
    mo.stop(selected_data is None)
    mo.stop(not budget_inert_cal_button.value)
    BUDGET_RESTICTED = -1
    WIND_RESTICTED = -2
    def _():
        wind_power_budget = 6_180_000
        solar_budget = int(budget.value) - wind_power_budget
        budget_restriction = calculate_solar_for_budget(solar_budget,Solar_type.value)
        if(budget_restriction is None):
            return BUDGET_RESTICTED
        wind_power = float(selected_data['Wind Power'])
        wind_restriction = calculate_max_solar_for_wind(wind_power=wind_power,type=Solar_type.value,inertia_ratio=inertial_percentage.value/100,irradiance=float(selected_data['Solar Power']))
        if(wind_restriction is None):
            return WIND_RESTICTED
        return min(wind_restriction,budget_restriction)

    
    _best_p = _()        
    output = ''
    if(_best_p > 0):
        _wp = float(selected_data["Wind Power"])
        _sp = calculate_solar_output_power(float(selected_data["Solar Power"]),installation=_best_p,type=Solar_type.value)
        _inter = _wp/_sp*100
        output = f'''
    
            |Parameter | Value|
            |---|---|
            |Solar power installation (kW) | {_best_p}|
            |Wind Output (kW)| {_wp:.2f}|
            |Solar Output (kW)| {_sp:.2f}|
            |Inertia Addition (%)| {_inter:.2f}|
        
        '''
    if(_best_p==BUDGET_RESTICTED):
        output = '''## Insufficient Budget!
           The Budget is not sufficient for establishing a Hybrid Power Plant Please Provide a Higher Budget
        '''
    if(_best_p == WIND_RESTICTED):
        output = '''## Insufficient Intertia Addition!
           The Selected Point doesn't have enough inertia addition for constructing a Hybrid Power Plant. You will need to incorporate additional Points into the system. You can refer to the generated map to select nearby bridges or apropriate wind plant establishment points.
        '''
    
    mo.md(
        f'''
        # Calculated Parameters

        {output}
        '''
    ).center()
    return


if __name__ == "__main__":
    app.run()
