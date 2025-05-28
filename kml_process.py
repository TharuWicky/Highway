from lxml import etree as parser


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
