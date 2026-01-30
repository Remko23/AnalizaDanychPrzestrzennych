-- Maciej Miazek
-- Kacper Romek
-- Remigiusz Tomecki


-- 1. Dla każdej dzielnicy wyświetl jej nazwę oraz liczbę znajdujących się tam osiedli. Wyniki posortuj alfabetycznie.
SELECT boroname, COUNT(name) as liczba
FROM nyc_neighborhoods
GROUP BY boroname
ORDER BY boroname;

-- 2. Dla każdej dzielnicy wyświetl jej nazwę oraz liczbę zamieszkujących ją osób. Wyniki posortuj malejąco według liczby mieszkańców.
SELECT c.boroname, SUM(c.popn_total) as liczba_osob
FROM nyc_census_blocks as c
GROUP BY c.boroname
ORDER BY SUM(c.popn_total) DESC;

-- 3. Dla każdej dzielnicy wyświetl jej nazwę oraz procentowy udział w całkowitej liczbie mieszkańców osób rasy białej, czarnej i żółtej. Zastosuj aliasy white, black oraz asian.
SELECT
    boroname,
    ROUND((SUM(popn_white) * 100 / SUM(popn_total))::NUMERIC,2) AS white,
    ROUND((SUM(popn_black) * 100 / SUM(popn_total))::NUMERIC,2) AS black,
    ROUND((SUM(popn_asian) * 100 / SUM(popn_total))::NUMERIC,2) AS asian
FROM nyc_census_blocks
GROUP BY boroname;

-- 4. Dla każdego typu drogi wyświetl jego nazwę oraz liczbę dróg tego typu.
SELECT regexp_split_to_table(type,'; ') as street_type, COUNT(*) AS number
FROM nyc_streets
GROUP BY street_type;

-- 5.Dla każdej dzielnicy wyświetl jej nazwę oraz liczbę znajdujących się tam stacji metra.
SELECT s.borough, COUNT(*) as liczba_stacji
FROM nyc_subway_stations as s
GROUP BY s.borough;

-- 6. Wyświetl, przez ile stacji metra przebiega linia ekspresowa, a przez ile nie.
SELECT coalesce(express, 'not_express'), COUNT(*)
FROM nyc_subway_stations
GROUP BY express;

-- 7. Wyświetl liczbę zamkniętych stacji metra.
SELECT COUNT(name) AS closed_stations
FROM nyc_subway_stations
WHERE closed IS NOT NULL;

-- 8. Wyświetl nazwy stacji metra, przez które przebiega linia czerwona.
SELECT DISTINCT s.name
FROM nyc_subway_stations as s
WHERE s.color LIKE '%RED%';

-- 9. Dla każdej dzielnicy wyświetl jej nazwę oraz liczbę popełnionych tam zabójstw.
SELECT
    boroname,
    COUNT(*) AS num_of_homicides
FROM
    nyc_homicides
WHERE
    boroname IS NOT NULL
GROUP BY
    boroname;

-- 10. Dla każdego rodzaju broni wyświetl jego nazwę oraz liczbę zabójstw popełnionych przy użyciu broni tego rodzaju.
SELECT coalesce(weapon, 'unknown'), COUNT(num_victim) AS killed
FROM nyc_homicides
GROUP BY weapon;

-- 11. Wyświetl, ile zabójstw popełniono w każdym roku.
SELECT h.year, COUNT(*) as liczba_zabojstw
FROM nyc_homicides as h
GROUP BY h.year
ORDER BY h.year;

-- 12. Wyświetl, ile zabójstw popełniono w każdym miesiącu.
SELECT TO_CHAR(incident_d, 'month') AS miesiac, COUNT(num_victim) AS killed
FROM nyc_homicides
GROUP BY miesiac;

-- 13. Wyświetl, ile zabójstw popełniono w każdym dniu tygodnia.
SELECT TO_CHAR(incident_d, 'FMday') AS dzien_tygodnia, COUNT(num_victim) AS killed
FROM nyc_homicides
GROUP BY dzien_tygodnia;

-- 14. Wyświetl zabójstwa, w których ofiar było więcej niż jedna.
SELECT *
FROM nyc_homicides as h
WHERE h.num_victim NOT LIKE '1';

-- 15. Wyświetl, ile zabójstw popełniono w ciągu dnia, a ile w nocy. Pomiń rekordy, w których brakuje tej informacji.
SELECT light_dark, COUNT(*) AS num_of_homicides
FROM nyc_homicides
WHERE light_dark IN ('L', 'D')
GROUP BY light_dark;