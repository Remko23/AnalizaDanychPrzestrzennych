--Maciej Miazek
--Kacper Romek
--Remigiusz Tomecki

------- Wprowadzenie -------

--1. Utwórz tabelę geometries z dwoma kolumnami: name typu tekstowego oraz geom typu geometrycznego.
CREATE TABLE geometries(
	name TEXT,
	geom GEOMETRY
)

--2. Dodaj do tabeli geometries następujące rekordy:
--– punkt o nazwie Point oraz współrzędnych (0,0),
INSERT INTO geometries(name, geom) VALUES (
	'Point', ST_GeomFromText('POINT(0 0)')
)
--– linię o nazwie Linestring oraz współrzędnych (0,0), (1,1), (2,1), (2,2),
INSERT INTO geometries(name, geom) VALUES (
	'Linestring', ST_GeomFromText('LINESTRING(0 0, 1 1, 2 1, 2 2)')
)

--– wielokąt o nazwie Polygon oraz współrzędnych (0,0), (1,0), (1,1), (0,1), (0,0),
INSERT INTO geometries(name, geom) VALUES (
	'Polygon', ST_GeomFromText('POLYGON((0 0, 1 0, 0 1, 0 0))')
)

--– wielokąt o nazwie PolygonWithHole oraz współrzędnych (0,0), (10,0), (10,10), (0,10), (0,0), posiadający wycięcie o współrzędnych (1,1), (1,2), (2,2), (2,1), (1,1),
INSERT INTO geometries(name, geom) VALUES (
	'PolygonWithHole', ST_GeomFromText('POLYGON((0 0, 10 0, 10 10, 0 10, 0 0), (1 1, 1 2, 2 2, 2 1, 1 1))')
)

--– kolekcję geometrii o nazwie Collection, składającą się z punktu o współrzędnych (2,0) oraz wielokąta o współrzędnych (0,0), (1,0), (1,1), (0,1), (0,0).
INSERT INTO geometries(name, geom) VALUES (
	'Collection', ST_GeomFromText('GEOMETRYCOLLECTION(POINT(2 0), POLYGON((0 0, 1 0, 1 1, 0 1, 0 0)))')
)

--3. Wyświetl zawartość tabeli geometries. Zwróć uwagę na sposób wyświetlania danych typu geometrycznego (WKB).
SELECT *
FROM geometries;

--4. Ponownie wyświetl zawartość tabeli geometries, ale w taki sposób, aby typ geometryczny był zrozumiały dla człowieka (WKT).
SELECT name, ST_AsText(geom)
FROM geometries;

--5. Wyświetl zawartość widoku geometry_columns. Sprawdź, czy widzisz kolumnę geom z tabeli geometries.
SELECT *
FROM geometry_columns;

--6. Dla każdej geometrii wyświetl jej nazwę, typ, liczbę wymiarów oraz SRID.
SELECT name, GeometryType(geom), ST_Dimension(geom), ST_SRID(geom)
FROM geometries;

--7. Wyświetl współrzędne punktu Point.
SELECT name, ST_X(geom), ST_Y(geom)
FROM geometries
WHERE name LIKE 'Point';

--8. Wyświetl długość linii Linestring.
SELECT name, ROUND(ST_Length(geom)::numeric,2) as dlugosc
FROM geometries
WHERE name LIKE 'Linestring';

--9. Wyświetl powierzchnię wielokątów Polygon i PolygonWithHole.
SELECT name, ST_Area(geom)
FROM geometries
WHERE name IN ('Polygon', 'PolygonWithHole');

--10. Wyświetl liczbę elementów w kolekcji geometrii Collection.
SELECT name, ST_NumGeometries(geom)
FROM geometries
WHERE name LIKE 'Collection';

------- Zapytania do nyc -------

--1. Wyświetl powierzchnię osiedla West Village.
SELECT ROUND(ST_Area(geom)::numeric,0)
FROM nyc_neighborhoods
WHERE name LIKE 'West Village';

--2. Wyświetl procentowy udział poszczególnych dzielnic w całkowitej powierzchni miasta.
SELECT boroname, (SUM(ST_Area(geom))/(SELECT SUM(ST_Area(geom)) FROM nyc_neighborhoods))*100 as procentowy_udzial
FROM nyc_neighborhoods
GROUP BY boroname;

--3. Wyświetl łączną długość dróg.
SELECT SUM(ST_Length(geom))
FROM nyc_streets;

--4. Wyświetl nazwę najdłuższej drogi. Uwzględnij, że może być ich kilka.
SELECT name
FROM nyc_streets
WHERE ST_Length(geom) = (SELECT MAX(ST_Length(geom)) FROM nyc_streets);

--5. Wyświetl, jakim typem geometrycznym jest stacja metra Morris Park.
SELECT GeometryType(geom)
FROM nyc_subway_stations
WHERE name LIKE 'Morris Park';

--6. Dla każdej stacji metra wyświetl jej nazwę oraz geometrię w formatach GML i GeoJSON.
SELECT name, ST_AsGML(geom) as GML, ST_AsGeoJSON(geom) as GeoJSON
FROM nyc_subway_stations;

--7. Wyświetl nazwę najbardziej wysuniętej na zachód stacji metra. Uwzględnij, że może być ich kilka.
SELECT name, ST_X(geom)
FROM nyc_subway_stations
WHERE ST_X(geom) = (SELECT MIN(ST_X(geom)) FROM nyc_subway_stations);

--8. Dla każdego typu drogi wyświetl jego nazwę oraz łączną długość dróg tego typu.
SELECT type, ROUND(SUM(ST_Length(geom))::numeric,0)
FROM nyc_streets
GROUP BY type;
