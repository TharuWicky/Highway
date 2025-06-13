import marimo

__generated_with = "0.13.13"
app = marimo.App(
    width="columns",
    app_title="WattWay",
    layout_file="layouts/Highway_Main.grid.json",
)

with app.setup:
    from lxml import etree as parser
    import folium
    import marimo as mo
    import io
    from matplotlib import pyplot as plt
    import polars as pd
    from tqdm.notebook import tqdm


@app.cell
def _():
    mo.md(r"""# Please Upload the KML File""")
    return


@app.cell
def _():
    file_upload_widget = mo.ui.file(kind="area")
    file_upload_widget
    return (file_upload_widget,)


@app.cell
def _(file_upload_widget, load_kml_file):
    mo.stop(not file_upload_widget.value)
    file_content = file_upload_widget.value[0].contents
    file_object = io.BytesIO(file_content)
    points = load_kml_file(file_object)
    return (points,)


@app.cell
def _():
    mo.md(
        r"""
    # You have Selected the Following Points

    * **Click** on a point to **see its Coordinates**.
    """
    )
    return


@app.cell
def _(points):
    folium_plot_points(points=points,radius=5,popup=(str(p) for p in points))
    return


@app.cell
def _():
    _year_form = mo.md(
        '''
        # Please Select Year Range
        Start Year: {start_year},

        End Year: {end_year}
        '''
    )

    _start_year = mo.ui.dropdown( options=tuple(range(2000,2025)),value='2024',searchable=True)
    _end_year = mo.ui.dropdown( options=tuple(range(2000,2025)),value='2024',searchable=True)

    year_form = _year_form.batch(start_year=_start_year, end_year=_end_year).form()
    year_form
    return (year_form,)


@app.cell
def _(
    find_average_irradiation_data,
    get_monthly_solar_irradiation,
    points,
    year_form,
):
    mo.stop(year_form.value is None)
    start_year = year_form.value["start_year"]
    end_year = year_form.value["start_year"]
    mo.stop(start_year is None or end_year is None)
    mo.stop(int(start_year) < int(end_year))

    solar_data = {}
    for _point in tqdm(points):

        monthly_data = get_monthly_solar_irradiation(longitude=_point[0], latitude=_point[1], start_year=start_year, end_year=end_year)
        average_data = find_average_irradiation_data(monthly_data)
        solar_data[tuple(_point)] = average_data

    # solar_data
    return (solar_data,)


@app.cell
def _(solar_data):
    _insolation_data = list(solar_data.values())
    _insolation_data
    plt.stem(_insolation_data)
    plt.gca()
    return


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


@app.cell(hide_code=True)
def _():
    mo.md(
        r"""
    # Optimality of Points
    * Optimality of the points are colour coded. **More** optimal points are **Red**, while **Less** optimal points are **Blue**.

    * **Hover over** a Point to find the average **Solar Insolation**.

    * **Click** on a Point to see the **Coordinates**.
    """
    )
    return


@app.cell
def _(color_interpolate, normalize_solar_data, points, solar_data):
    max_solar_data = max(solar_data.values())
    _interpolated_colors = map(color_interpolate, normalize_solar_data(tuple(solar_data[point] for point in points)))
    folium_plot_points(points, colors=_interpolated_colors, fill=True, radius=4, zoom_start=12,tooltip=(str(solar_data[point]) for point in points),popup=(str(p) for p in points))
    return


@app.cell
def _(points):
    points_selected_ui = mo.ui.dropdown(label="Number of Optimal Points:", full_width=True,options=tuple(i for i in range(1,len(points)+1)),value=1)
    num_points_form = mo.md(
        '''
        # How many Optimal Points do you need? 
        {points_selected_ui}
        '''
    ).batch(points_selected_ui=points_selected_ui).form()
    num_points_form
    return (num_points_form,)


@app.cell
def _(num_points_form, solar_data):
    mo.stop(num_points_form.value is None)
    p_i_list = list(solar_data.items())
    p_i_list.sort(key=lambda x:x[1],reverse=True)
    table_rows = [{"point": f"{point[0]:.6f}, {point[1]:.6f}","solar insolation":f"{ins:.2f}"} for (point,ins) in p_i_list]
    number_of_points = num_points_form.value["points_selected_ui"]
    mo.ui.table(table_rows[:number_of_points])
    return


@app.cell(column=1)
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

    return find_average_irradiation_data, get_monthly_solar_irradiation


@app.function
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
    mo.md(
        r"""
    <br></br>
    <br></br>
    <br></br>
    <br></br>
    <br></br>
    """
    )
    return


if __name__ == "__main__":
    app.run()
