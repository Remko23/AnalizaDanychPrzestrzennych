-- Sklad zespolu:
-- Maciej Miazek
-- Kacper Romek
-- Remigiusz Tomecki

--projekcja danych do SRID 2271
ALTER TABLE public.cities
ALTER COLUMN geom
TYPE geometry(Point, 2271)
USING ST_Transform(geom, 2271);

ALTER TABLE public.counties
ALTER COLUMN geom
TYPE geometry(MultiPolygon, 2271)
USING ST_Transform(geom, 2271);

ALTER TABLE public.interstates
ALTER COLUMN geom
TYPE geometry(MultiLineString, 2271)
USING ST_Transform(geom, 2271);

ALTER TABLE public.recareas
ALTER COLUMN geom
TYPE geometry(MultiPolygon, 2271)
USING ST_Transform(geom, 2271);

-- ZAPYTANIA:
--1. 
CREATE OR REPLACE VIEW hrabstwa AS
SELECT *
FROM counties
WHERE no_farms87 > 500 AND age_18_64 > 25000 AND pop_sqmile < 150;

--2.
CREATE OR REPLACE VIEW miasta AS
SELECT c.*
FROM cities as c JOIN hrabstwa as h ON ST_Intersects(c.geom, h.geom)
WHERE c.crime_inde <= 0.02 AND c.university >= 1;

--3.
CREATE OR REPLACE VIEW miasta_z_uw_drogi AS
SELECT DISTINCT m.*
FROM miasta as m JOIN interstates as i ON ST_DWithin(m.geom,i.geom, 20*5280);

--4.
CREATE OR REPLACE VIEW miasta_ter_rek AS
SELECT DISTINCT m.*
FROM miasta_z_uw_drogi as m JOIN recareas as r ON ST_DWithin(m.geom,r.geom, 10*5280);
