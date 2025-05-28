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


# print(
#     find_average_irradiation_data(
#         get_monthly_solar_irradiation(
#             latitude=37.7749, longitude=-122.4194, start_year=2020, end_year=2020
#         )
#     )
# )
