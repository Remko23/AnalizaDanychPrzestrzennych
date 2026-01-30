--1. Wyświetl, czy wielokąty Polygon i PolygonWithHole są jednakowe.
SELECT ST_Equals(g1.geom, g2.geom)
FROM geometries as g1 
JOIN geometries as g2 
ON g1.name like 'Polygon' and g2.name like 'PolygonWithHole';

--2. Wyświetl, czy wielokąty Polygon i PolygonWithHole na siebie zachodzą.
SELECT ST_Overlaps(g1.geom, g2.geom)
FROM geometries as g1 
JOIN geometries as g2 
ON g1.name like 'Polygon' and g2.name like 'PolygonWithHole';

--3. Wyświetl, czy wielokąt Polygon znajduje się wewnątrz wielokąta PolygonWithHole.
SELECT ST_Within(g1.geom, g2.geom)
FROM geometries as g1 
JOIN geometries as g2 
ON g1.name like 'Polygon' and g2.name like 'PolygonWithHole';

--4. Wyświetl, czy wielokąt PolygonWithHole zawiera wielokąt Polygon.
SELECT ST_Contains(g1.geom, g2.geom)
FROM geometries as g1 
JOIN geometries as g2 
ON g1.name like 'PolygonWithHole' and g2.name like 'Polygon';

--5. Wyświetl, czy linia Linestring oraz wielokąt Polygon są rozłączne.
SELECT ST_Disjoint(g1.geom, g2.geom)
FROM geometries as g1 
JOIN geometries as g2 
ON g1.name like 'Linestring' and g2.name like 'Polygon';

--6. Wyświetl, czy linia Linestring oraz wielokąt Polygon krzyżują się.
SELECT ST_Crosses(g1.geom, g2.geom)
FROM geometries as g1 
JOIN geometries as g2 
ON g1.name like 'Linestring' and g2.name like 'Polygon';

--7. Wyświetl, czy linia Linestring oraz wielokąt Polygon przecinają się.
SELECT ST_Intersects(g1.geom, g2.geom)
FROM geometries as g1 
JOIN geometries as g2 
ON g1.name like 'Linestring' and g2.name like 'Polygon';

--8. Wyświetl, czy linia Linestring oraz wielokąt Polygon dotykają się.
SELECT ST_Touches(g1.geom, g2.geom)
FROM geometries as g1 
JOIN geometries as g2 
ON g1.name like 'Linestring' and g2.name like 'Polygon';

--9. Wyświetl, czy punkt Point znajduje się w promieniu 5 jednostek od linii Linestring.
SELECT ST_DWithin(g1.geom, g2.geom, 5)
FROM geometries as g1 
JOIN geometries as g2 
ON g1.name like 'Point' and g2.name like 'Linestring';

--10. Wyświetl odległość między punktem Point a linią Linestring.
SELECT ST_Distance(g1.geom, g2.geom) as odleglosc
FROM geometries as g1 
JOIN geometries as g2 
ON g1.name like 'Point' and g2.name like 'Linestring';

----------- nyc -----------
--1. Wyświetl nazwę osiedla oraz nazwę dzielnicy, w których znajduje się stacja metra East Broadway.
SELECT nn.boroname, nn.name
FROM nyc_subway_stations as nss
JOIN nyc_neighborhoods as nn
ON ST_Intersects(nn.geom,nss.geom)
WHERE nss.name like 'East Broadway';

--2. Wyświetl nazwy osiedli oraz nazwy dzielnic, przez które przebiega linia metra F.
SELECT nn.name, nn.boroname
FROM nyc_subway_stations as nss
JOIN nyc_neighborhoods as nn
ON ST_Intersects(nn.geom,nss.geom)
WHERE nss.routes like '%F%';

--3. Wyświetl nazwy dróg, które znajdują się w promieniu 20 metrów od stacji metra Botanic Garden.
SELECT ns.name
FROM nyc_streets as ns
JOIN nyc_subway_stations as nss
ON ST_DWithin(nss.geom, ns.geom, 20)
WHERE nss.name like 'Botanic Garden';

--4. Wyświetl nazwy dróg, które mają skrzyżowanie z drogą Pulaski St.
SELECT ns1.name
FROM nyc_streets as ns1
JOIN nyc_streets as ns2
ON ST_Intersects(ns1.geom, ns2.geom)
WHERE ns2.name like 'Pulaski St' and ns1.name not like ns2.name;

--5. Wyświetl nazwy stacji metra, które znajdują się na osiedlu Utopia.
SELECT nss.name
FROM nyc_subway_stations as nss
JOIN nyc_neighborhoods as nn
ON ST_Intersects(nn.geom, nss.geom)
WHERE nn.name like 'Utopia';


--6. Dla każdej stacji metra wyświetl jej nazwę oraz liczbę mieszkańców, którzy żyją w promieniu 100 metrów od niej. Ogranicz rezultaty jedynie do tych stacji metra, przez które przebiega linia fioletowa. Dane posortuj malejąco według liczby mieszkańców.
SELECT nss.name, SUM(ncb.popn_total) as l_mieszkancow
FROM nyc_subway_stations as nss
JOIN nyc_census_blocks as ncb
ON ST_DWithin(nss.geom, ncb.geom, 100)
WHERE nss.color LIKE '%PURPLE%'
GROUP BY nss.name
ORDER BY l_mieszkancow DESC;

--7. Dla każdego rodzaju broni wyświetl jego nazwę oraz liczbę zabójstw popełnionych przy użyciu broni tego rodzaju na osiedlu Clearview.
SELECT COALESCE(nh.weapon, 'unknown') as weapon, SUM(nh.num_victim::integer) as killed
FROM nyc_homicides as nh
JOIN nyc_neighborhoods as nn
ON ST_Intersects(nn.geom,nh.geom)
WHERE nn.name like 'Clearview'
GROUP BY nh.weapon;

--8. Wyświetl liczbę mieszkańców osiedla Battery Park.
SELECT SUM(ncb.popn_total) as l_mieszkancow
FROM nyc_neighborhoods as nn
JOIN nyc_census_blocks as ncb
ON ST_Intersects(nn.geom, ncb.geom)
WHERE nn.name like 'Battery Park';


--9. Wyświetl liczbę mieszkańców, którzy żyją w promieniu 100 metrów od drogi Kosciuszko St.
SELECT SUM(ncb.popn_total) as l_mieszkancow
FROM nyc_streets as ns
JOIN nyc_census_blocks as ncb
ON ST_DWithin(ns.geom, ncb.geom, 100)
WHERE ns.name like 'Kosciuszko St';

--10. Dla każdego osiedla wyświetl jego nazwę oraz procentowy udział w całkowitej liczbie mieszkańców osób rasy białej, czarnej i azjatyckiej. Zastosuj aliasy white, black i asian. Ogranicz rezultaty jedynie do dzielnicy The Bronx
SELECT n1.name, ROUND((SUM(p1.popn_white)/SUM(p1.popn_total))::numeric*100,2) AS white, ROUND((SUM(p1.popn_black)/SUM(p1.popn_total))::numeric*100,2) AS black, ROUND((SUM(p1.popn_asian)/SUM(p1.popn_total))::numeric*100,2) AS asian
FROM nyc_census_blocks AS p1
JOIN nyc_neighborhoods AS n1
ON ST_Intersects(n1.geom, p1.geom)
WHERE p1.boroname LIKE 'The Bronx' AND p1.popn_total > 0
GROUP BY n1.name;

--11. Dla każdego osiedla wyświetl jego nazwę oraz wyrażoną w osobach na kilometr kwadratowy gęstość zaludnienia. Ogranicz rezultaty jedynie do dwóch osiedli o najwyższej gęstości zaludnienia. Dane posortuj malejąco według gęstości zaludnienia.
SELECT n.name AS neighborhood, ROUND( CAST(( SUM(p.popn_total) / (ST_Area(n.geom)/1000000) ) AS numeric) , 2) AS density
FROM nyc_neighborhoods AS n
JOIN nyc_census_blocks AS p
ON ST_Contains(n.geom, p.geom)
GROUP BY n.name, n.geom
ORDER BY density DESC
FETCH FIRST 2 ROWS WITH TIES;