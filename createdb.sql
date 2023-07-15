CREATE TABLE teams (
id INTEGER PRIMARY KEY,
p1 TEXT,
p2 TEXT,
name TEXT);

CREATE TABLE points (
point_id INTEGER PRIMARY KEY,
team_id INTEGER,
jeu TEXT,
point_number INTEGER);