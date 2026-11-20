# from tools.tavily_tool import search
from tools.flight_tool import search_flights

# res = search("Best Hotels in India")
# print(res)

# dep_iata = get_airport_code("Hyderabad")
# arr_iata = get_airport_code("Visakhapatnam")

# res = search_flights(dep_iata, arr_iata)

# print(parse_route("Flights from Hyderabad to Delhi"))


# query = "Find flights from Hyderabad to Vizag"

# result = parse_route(query)

# print(result)
print(search_flights("Plan a 7 days Vizag trip from Bangalore"))
# print("\n" + "=" * 80 + "\n")
# print(search_flights("all country flight info"))