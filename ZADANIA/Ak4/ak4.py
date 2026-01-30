from shapely.geometry import Point
from shapely.geometry import LineString
from shapely.geometry import Polygon
from shapely.geometry.base import BaseGeometry
import pandas as pd
# 1.
print("--- 1. ---")
def create_point_geometry(x, y):
    return Point(x, y)

point = create_point_geometry(0, 1)
print(point)
print(point.geom_type)

# 2.
print("--- 2. ---")
def create_line_geometry(points):
    assert isinstance(points, list), "Parametr musi być listą!"
    assert len(points) >= 2, "Linia musi się składać z minimum dwóch punktów"
    for point in points:
        assert point.geom_type == 'Point', "Linia musi się składać z punktów"

    return LineString(points)

points = []
points.append(create_point_geometry(0, 0))
points.append(create_point_geometry(1, 1))

line = create_line_geometry(points)
print(line)
print(line.geom_type)

# 3.
print("--- 3. ---")
def create_polygon_geometry(coordinates):
    assert isinstance(coordinates, list), "Parametr musi być listą!"
    assert len(coordinates) >= 3, "Wielokąt musi się składać z minimum trzech punktów"
    for coordinate in coordinates:
        assert isinstance(coordinate, tuple), "Lista musi składać się z dwuelementowych krotek!"
        assert isinstance(coordinate[0], int or float) and isinstance(coordinate[1], int or float)

    return Polygon(coordinates)

coordinates = []
coordinates.append((0, 0))
coordinates.append((1, 1))
coordinates.append((2, 0))

polygon = create_polygon_geometry(coordinates)
print(polygon)
print(polygon.geom_type)

# 4.
print("--- 4. ---")
def get_centroid(geom):
    assert isinstance(geom, BaseGeometry), 'Parametr musi być geometrią!'

    return geom.centroid

centroid = get_centroid(polygon)
print(centroid)

# 5.
print("--- 5. ---")
def get_area(polygon):
    assert polygon.geom_type == 'Polygon', 'Parametr musi być wielokątem'
    return polygon.area

area = get_area(polygon)
print(round(area, 2))

# 6.
print("--- 6. ---")
def get_length(geometry):
    assert geometry.geom_type == 'LineString' or geometry.geom_type == 'Polygon', 'Parametr musi być linią albo wielokątem!'
    return geometry.length

line_length = get_length(line)
print(round(line_length, 2))

polygon_perimeter = get_length(polygon)
print(round(polygon_perimeter, 2))
# 7.
print("--- 7. ---")
data = pd.read_csv('travel_times_2015_helsinki.txt', sep=';')

print(data.shape)
print('--head:')
print(data.head())

# 8.
data = data[['from_x', 'from_y', 'to_x', 'to_y']]
assert list(data.columns) == ['from_x', 'from_y', 'to_x', 'to_y'], 'Wybrano błędne kolumny!'

# 9.
origin_points = [create_point_geometry(x, y) for x, y in zip(data['from_x'], data['from_y'])]
destination_points = [create_point_geometry(x, y) for x, y in zip(data['to_x'], data['to_y'])]

assert len(origin_points) == len(data), 'Błędnie wczytano punkty początkowe!'
assert len(destination_points) == len(data), 'Błędnie wczytano punkty końcowe!'

# 10.
def create_routes(origin_points, destination_points):
    lines = [create_line_geometry([x, y]) for x, y in zip(origin_points, destination_points)]
    return lines

lines = create_routes(origin_points, destination_points)
assert len(lines) == len(data), 'Błędnie wczytano trasy!'

# 11.
def calculate_total_distance(lines):
    sum = 0
    for line in lines:
        sum+=get_length(line)
    return sum

distance = calculate_total_distance(lines)
assert round(distance, 2) == 3148.57, 'Błędnie obliczono łączny dystans!'
