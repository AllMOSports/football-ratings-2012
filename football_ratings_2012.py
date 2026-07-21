import requests
from bs4 import BeautifulSoup
import json
import csv
import re
import pandas as pd
from datetime import datetime, date, timedelta
import time
 
# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------
 
SEASON_YEAR   = 2011
SEASON_START  = date(2011, 8, 1)
SEASON_END    = date(2011, 12, 15)
BASE_URL      = "https://www.mshsaa.org/activities/scoreboard.aspx?alg=19&date={}"
MAX_POINTS    = 100
OUTPUT_PATH   = f"football_ratings_{SEASON_YEAR}.json"
CSV_PATH      = f"football_scoreboard_{SEASON_YEAR}.csv"
CLASSIFICATIONS_PATH  = "classifications.json"
SCHOOLS_CSV           = "mshsaa_schools.csv"
ITERATIONS            = 1000
LEARNING_RATE         = 0.1
 
# --- v2 rating engine settings (soft weighting + shrinkage, replaces the
#     old hard Phase-2 cutoff) ---
COMPETITIVE_THRESHOLD = 40    # now the "half-weight" point of a smooth decay curve
REGULARIZATION_K      = 3.0   # pseudo-games added to every team's denominator (shrinkage)
MOV_CAP               = 28    # max points of "error" any single game can contribute
 
# ---------------------------------------------------------------------------
# MANUAL GAMES (not listed on MSHSAA Scoreboard)
# ---------------------------------------------------------------------------
# Add any games missing from the MSHSAA scoreboard here.
# Format: ("YYYY-MM-DD", "Team 1 Name", score1, "Team 2 Name", score2)
# Team names must match exactly the names in classifications.json.
 
MANUAL_GAMES = [
    ("2012-08-24", "Grandview (Hillsboro)", 14, "Chaffee", 36),
    ("2012-09-07", "Chaffee", 8, "Hayti", 32),
    ("2012-09-14", "Chaffee", 6, "Portageville", 21),
    ("2012-10-19", "Grandview (Hillsboro)", 47, "Crystal City", 20),
    ("2012-08-24", "Thayer", 21, "Hayti", 6),
    ("2012-08-31", "Hayti", 14, "Charleston", 20),
    ("2012-09-14", "Hayti", 72, "East Prairie", 6),
    ("2012-09-21", "Hayti", 22, "Portageville", 35),
    ("2012-09-28", "Hayti", 26, "Malden", 40),
    ("2012-08-24", "St. Pius X (Festus)", 14, "Portageville", 34),
    ("2012-08-31", "Portageville", 27, "Kennett", 7),
    ("2012-09-07", "Portageville", 22, "Malden", 13),
    ("2012-10-05", "East Prairie", 0, "Portageville", 48),
    ("2012-10-18", "Portageville", 0, "Central (New Madrid County)", 46),
    ("2012-08-24", "St. Vincent", 45, "Sumner", 22),
    ("2012-10-12", "St. Vincent", 56, "Grandview (Hillsboro)", 26),
    ("2012-09-07", "Liberty (Mountain View)", 30, "Thayer", 0),
    ("2012-09-14", "Thayer", 6, "Salem", 21),
    ("2012-09-21", "Houston", 7, "Thayer", 50),
    ("2012-09-28", "Thayer", 36, "Cabool", 6),
    ("2012-10-05", "Thayer", 29, "Ava", 22),
    ("2012-10-12", "Willow Springs", 3, "Thayer", 7),
    ("2012-10-19", "Thayer", 14, "Mountain Grove", 34),
    ("2012-09-21", "Valle Catholic", 39, "Grandview (Hillsboro)", 12),
    ("2012-08-24", "Greenfield", 20, "Lockwood with Golden City", 14),
    ("2012-09-28", "Greenfield", 8, "Sarcoxie", 46),
    ("2012-10-05", "Diamond", 20, "Greenfield", 7),
    ("2012-10-12", "Greenfield", 0, "Miller", 26),
    ("2012-09-14", "Lockwood with Golden City", 51, "Jasper", 34),
    ("2012-08-24", "Marionville", 10, "Miller", 53),
    ("2012-08-31", "Pleasant Hope", 30, "Marionville", 15),
    ("2012-09-07", "Marionville", 8, "Strafford", 44),
    ("2012-09-14", "Ash Grove", 46, "Marionville", 15),
    ("2012-09-28", "Stockton", 21, "Marionville", 44),
    ("2012-10-05", "Marionville", 6, "Fair Grove", 14),
    ("2012-10-12", "Marionville", 7, "Skyline", 38),
    ("2012-09-21", "McAuley Catholic", 28, "Ash Grove", 21),
    ("2012-10-05", "McAuley Catholic", 54, "Lockwood with Golden City", 30),
    ("2012-09-14", "Diamond", 6, "Miller", 39),
    ("2012-10-05", "Osceola", 20, "Adrian", 0),
    ("2012-09-28", "Archie", 12, "Osceola", 53),
    ("2012-08-24", "Midway", 20, "Osceola", 6),
    ("2012-08-31", "Appleton City with Montrose", 31, "Osceola", 36),
    ("2012-09-07", "Lexington", 26, "Osceola", 7),
    ("2012-09-14", "Osceola", 14, "Drexel with Miami (Amoret)", 49),
    ("2012-09-21", "Osceola", 42, "Rich Hill with Hume", 14),
    ("2012-10-12", "Osceola", 21, "Cole Camp", 22),
    ("2012-10-19", "Pleasant Hope", 14, "Osceola", 38),
    ("2012-09-07", "Skyline", 67, "Stockton", 6),
    ("2012-09-28", "Skyline", 66, "Ash Grove", 7),
    ("2012-10-05", "Strafford", 41, "Skyline", 32),
    ("2012-09-08", "Cole Camp", 34, "Sacred Heart", 12),
    ("2012-09-28", "Concordia", 15, "Wellington-Napoleon", 42),
    ("2012-10-19", "Concordia", 7, "Trenton", 34),
    ("2012-08-24", "East Buchanan", 36, "Crest Ridge", 21),
    ("2012-09-14", "Crest Ridge", 51, "Orrick", 8),
    ("2012-09-21", "Wellington-Napoleon", 48, "Crest Ridge", 8),
    ("2012-08-24", "Sacred Heart", 8, "Tipton", 50),
    ("2012-09-15", "Sacred Heart", 46, "St. Mary's (Independence)", 14),
    ("2012-09-21", "Sacred Heart", 34, "Windsor", 36),
    ("2012-09-28", "Sacred Heart", 25, "University Academy Charter", 14),
    ("2012-10-06", "Sacred Heart", 27, "Derrick Thomas Academy", 14),
    ("2012-10-20", "Father Tolton with Calvary Lutheran", 6, "Sacred Heart", 42),
    ("2012-09-07", "Santa Fe", 27, "Wellington-Napoleon", 42),
    ("2012-10-19", "Santa Fe", 6, "Van Horn", 49),
    ("2012-08-24", "Knox County", 0, "Marceline", 35),
    ("2012-08-31", "Scotland County", 8, "Knox County", 14),
    ("2012-09-07", "Knox County", 14, "Fayette", 6),
    ("2012-09-14", "Paris", 12, "Knox County", 45),
    ("2012-09-21", "Milan", 37, "Knox County", 18),
    ("2012-09-28", "Knox County", 60, "Putnam County", 30),
    ("2012-10-19", "Knox County", 60, "North Shelby", 8),
    ("2012-08-24", "Louisiana", 21, "South Shelby", 53),
    ("2012-09-28", "Louisiana", 15, "Macon", 45),
    ("2012-10-12", "Centralia", 49, "Louisiana", 0),
    ("2012-08-24", "Westran", 60, "North Shelby", 6),
    ("2012-08-31", "Fayette", 20, "North Shelby", 6),
    ("2012-09-07", "North Shelby", 13, "Paris", 34),
    ("2012-09-14", "North Shelby", 0, "Salisbury", 42),
    ("2012-09-21", "North Shelby", 0, "Scotland County", 6),
    ("2012-09-28", "Schuyler County", 47, "North Shelby", 6),
    ("2012-10-05", "Putnam County", 32, "North Shelby", 26),
    ("2012-10-12", "North Shelby", 6, "Milan", 70),
    ("2012-08-31", "Marceline", 6, "Schuyler County", 7),
    ("2012-09-21", "Putnam County", 0, "Schuyler County", 35),
    ("2012-10-05", "Milan", 34, "Schuyler County", 6),
    ("2012-10-19", "Scotland County", 0, "Schuyler County", 34),
    ("2012-09-28", "Scotland County", 14, "Milan", 50),
    ("2012-10-12", "Putnam County", 14, "Scotland County", 32),
    ("2012-08-31", "South Shelby", 14, "Macon", 0),
    ("2012-09-07", "Palmyra", 21, "South Shelby", 12),
    ("2012-09-14", "South Shelby", 8, "Centralia", 26),
    ("2012-09-21", "Monroe City", 14, "South Shelby", 26),
    ("2012-09-28", "Brookfield", 30, "South Shelby", 20),
    ("2012-10-05", "South Shelby", 32, "Highland", 0),
    ("2012-10-12", "South Shelby", 32, "Clark County", 41),
    ("2012-10-19", "Mark Twain", 8, "South Shelby", 48),
    ("2012-09-21", "Albany", 33, "Braymer", 22),
    ("2012-09-28", "South Harrison", 58, "Braymer", 0),
    ("2012-09-07", "Marceline", 0, "Brookfield", 20),
    ("2012-08-24", "Princeton with Mercer", 15, "Milan", 34),
    ("2012-08-31", "Milan", 54, "Albany", 0),
    ("2012-09-07", "Milan", 68, "Slater", 6),
    ("2012-10-19", "Milan", 51, "Putnam County", 12),
    ("2012-08-24", "Albany", 33, "Putnam County", 16),
    ("2012-08-31", "Putnam County", 8, "Princeton with Mercer", 30),
    ("2012-09-07", "Trenton", 56, "Putnam County", 18),
    ("2012-08-24", "Wellington-Napoleon", 48, "Lone Jack", 8),
    ("2012-08-24", "Orrick", 6, "Mid-Buchanan", 48),
    ("2012-09-07", "North Platte", 34, "Mid-Buchanan", 0),
    ("2012-09-21", "East Buchanan", 8, "Mid-Buchanan", 0),
    ("2012-09-28", "Mid-Buchanan", 20, "Plattsburg", 9),
    ("2012-10-05", "Mid-Buchanan", 0, "West Platte", 34),
    ("2012-10-19", "Lathrop", 56, "Mid-Buchanan", 0),
    ("2012-08-31", "North Platte", 35, "Derrick Thomas Academy", 6),
    ("2012-09-21", "West Platte", 42, "North Platte", 8),
    ("2012-09-28", "North Platte", 7, "Lathrop", 39),
    ("2012-10-05", "East Buchanan", 20, "North Platte", 22),
    ("2012-10-12", "Wellington-Napoleon", 60, "Orrick", 14),
    ("2012-08-31", "West Platte", 42, "Wellington-Napoleon", 34),
    ("2012-09-14", "Wellington-Napoleon", 44, "Lexington", 22),
    ("2012-10-05", "Wellington-Napoleon", 36, "St. Paul Lutheran (Concordia)", 14),
    ("2012-10-19", "Sweet Springs with Malta Bend", 8, "Wellington-Napoleon", 52),
    ("2012-08-24", "West Platte", 28, "Lincoln College Prep", 0),
    ("2012-09-07", "East Buchanan", 32, "West Platte", 14),
    ("2012-09-14", "Lathrop", 41, "West Platte", 12),
    ("2012-09-28", "Penney", 47, "West Platte", 12),
    ("2012-10-12", "West Platte", 45, "Plattsburg", 0),
    ("2012-10-19", "West Platte", 12, "Lawson", 29),
    ("2012-09-07", "Albany", 20, "King City with Pattonsburg", 41),
    ("2012-09-28", "Albany", 14, "Princeton with Mercer", 54),
    ("2012-10-05", "South Harrison", 78, "Albany", 0),
    ("2012-10-19", "Albany", 0, "Polo", 56),
    ("2012-08-31", "South Harrison", 27, "East Buchanan", 0),
    ("2012-09-14", "Plattsburg", 41, "East Buchanan", 42),
    ("2012-10-12", "Lathrop", 62, "East Buchanan", 18),
    ("2012-09-14", "Gallatin", 40, "Princeton with Mercer", 20),
    ("2012-10-19", "Princeton with Mercer", 49, "Maysville", 15),
    ("2012-09-07", "Penney", 32, "Lathrop", 14),
    ("2012-08-24", "Polo", 14, "Van Horn", 28),
    ("2012-08-31", "Lathrop", 14, "Polo", 0),
    ("2012-09-14", "Polo", 13, "South Harrison", 21),
    ("2012-09-07", "Princeton with Mercer", 18, "South Harrison", 49),
    ("2012-08-24", "Liberty (Mountain View)", 48, "Caruthersville", 12),
    ("2012-09-07", "Charleston", 12, "Caruthersville", 34),
    ("2012-09-21", "Caruthersville", 41, "Central (New Madrid County)", 14),
    ("2012-10-05", "Kennett", 0, "Caruthersville", 36),
    ("2012-08-24", "Sikeston", 27, "Charleston", 14),
    ("2012-09-28", "Kennett", 28, "Charleston", 48),
    ("2012-08-31", "East Prairie", 12, "Grandview (Hillsboro)", 44),
    ("2012-10-19", "East Prairie", 8, "Kennett", 42),
    ("2012-09-07", "St. Pius X (Festus)", 6, "Grandview (Hillsboro)", 12),
    ("2012-09-14", "Missouri Military Academy", 6, "Grandview (Hillsboro)", 49),
    ("2012-09-28", "Grandview (Hillsboro)", 6, "Herculaneum", 34),
    ("2012-10-05", "Grandview (Hillsboro)", 24, "Jefferson (Festus)", 53),
    ("2012-10-12", "Kennett", 22, "Malden", 67),
    ("2012-09-15", "Cleveland NJROTC", 6, "Brentwood", 53),
    ("2012-09-14", "Central (Park Hills)", 7, "Maplewood-Richmond Hts.", 0),
    ("2012-09-28", "Missouri Military Academy", 16, "Principia", 48),
    ("2012-08-24", "Cuba", 12, "St. James", 40),
    ("2012-09-07", "Houston", 6, "Cuba", 0),
    ("2012-09-14", "Springfield Catholic", 41, "Fair Grove", 7),
    ("2012-10-12", "Ash Grove", 42, "Fair Grove", 21),
    ("2012-10-19", "Hollister", 0, "Fair Grove", 49),
    ("2012-08-24", "Salem", 35, "Houston", 6),
    ("2012-09-14", "Houston", 27, "Cabool", 12),
    ("2012-09-28", "Ava", 35, "Houston", 0),
    ("2012-10-05", "Houston", 0, "Willow Springs", 37),
    ("2012-10-12", "Mountain Grove", 68, "Houston", 26),
    ("2012-08-31", "Springfield Catholic", 16, "Liberty (Mountain View)", 32),
    ("2012-09-14", "Ava", 27, "Liberty (Mountain View)", 26),
    ("2012-09-28", "Liberty (Mountain View)", 20, "Mountain Grove", 27),
    ("2012-10-05", "Liberty (Mountain View)", 47, "Cabool", 6),
    ("2012-08-24", "Mountain Grove", 39, "Logan-Rogersville", 21),
    ("2012-09-07", "Ava", 12, "Mountain Grove", 36),
    ("2012-09-21", "Cabool", 19, "Mountain Grove", 44),
    ("2012-10-05", "Mountain Grove", 48, "Salem", 7),
    ("2012-10-19", "Strafford", 43, "Ash Grove", 14),
    ("2012-10-19", "Ava", 17, "Willow Springs", 28),
    ("2012-08-24", "Ash Grove", 41, "Cabool", 0),
    ("2012-09-08", "St. Mary's (Independence)", 6, "Butler", 45),
    ("2012-09-14", "Van Horn", 34, "Butler", 43),
    ("2012-08-31", "Lamar", 6, "Seneca", 13),
    ("2012-10-05", "Lamar", 42, "Monett", 6),
    ("2012-10-18", "Lamar", 63, "East Newton", 0),
    ("2012-09-07", "Sarcoxie", 33, "Lockwood with Golden City", 20),
    ("2012-10-19", "Central (Park Hills)", 60, "Bowling Green", 7),
    ("2012-09-14", "Clark County", 42, "Macon", 21),
    ("2012-10-05", "Centralia", 15, "Clark County", 20),
    ("2012-10-19", "Clark County", 18, "Brookfield", 0),
    ("2012-08-24", "Highland", 6, "Centralia", 33),
    ("2012-08-31", "Brookfield", 12, "Highland", 3),
    ("2012-09-21", "Macon", 49, "Highland", 3),
    ("2012-08-24", "Mark Twain", 12, "Brookfield", 34),
    ("2012-08-31", "Monroe City", 7, "Mark Twain", 26),
    ("2012-09-07", "Centralia", 21, "Mark Twain", 0),
    ("2012-10-05", "Macon", 21, "Mark Twain", 0),
    ("2012-09-07", "Macon", 21, "Monroe City", 3),
    ("2012-09-14", "Brookfield", 40, "Monroe City", 10),
    ("2012-09-28", "Monroe City", 14, "Centralia", 39),
    ("2012-08-24", "Palmyra", 22, "Macon", 24),
    ("2012-08-31", "Centralia", 18, "Palmyra", 12),
    ("2012-10-05", "Palmyra", 14, "Brookfield", 31),
    ("2012-09-14", "Southern Boone", 18, "Blair Oaks", 43),
    ("2012-10-19", "Eldon", 6, "Blair Oaks", 35),
    ("2012-09-07", "St. James", 20, "Hermann", 28),
    ("2012-09-21", "Owensville", 14, "Hermann", 33),
    ("2012-10-05", "St. Clair", 69, "Hermann", 24),
    ("2012-09-21", "Lexington", 3, "Holden", 40),
    ("2012-09-07", "Knob Noster", 6, "O'Hara", 13),
    ("2012-09-14", "Knob Noster", 13, "Boonville", 35),
    ("2012-09-28", "Knob Noster", 27, "Lexington", 14),
    ("2012-10-12", "Knob Noster", 12, "Richmond", 41),
    ("2012-09-07", "Van Horn", 28, "Sherwood", 19),
    ("2012-09-22", "Van Horn", 61, "Southeast", 12),
    ("2012-10-05", "Southwest Early College", 12, "Southeast", 8),
    ("2012-10-12", "Southeast", 0, "Central (Kansas City)", 33),
    ("2012-10-20", "Hogan Prep Academy Charter", 60, "Southeast", 0),
    ("2012-08-24", "St. Paul Lutheran (Concordia)", 57, "Wentworth Military Academy", 17),
    ("2012-08-24", "Bishop LeBlond", 46, "St. Mary's (Independence)", 8),
    ("2012-09-21", "Centralia", 31, "Brookfield", 0),
    ("2012-10-12", "Brookfield", 7, "Macon", 12),
    ("2012-08-24", "Carrollton", 14, "Trenton", 18),
    ("2012-09-14", "East (Kansas City)", 48, "Carrollton", 12),
    ("2012-10-05", "Carrollton", 12, "Lexington", 20),
    ("2012-09-21", "Lathrop", 26, "Lawson", 21),
    ("2012-10-05", "Plattsburg", 7, "Lathrop", 56),
    ("2012-08-24", "Oak Grove", 50, "Lexington", 6),
    ("2012-08-31", "Trenton", 14, "Lexington", 21),
    ("2012-10-12", "Lexington", 7, "Lafayette County", 48),
    ("2012-10-19", "Lexington", 8, "Richmond", 42),
    ("2012-08-24", "Plattsburg", 62, "Northeast (Kansas City)", 26),
    ("2012-09-14", "Lafayette County", 42, "Trenton", 14),
    ("2012-09-21", "Trenton", 7, "Pembroke Hill", 39),
    ("2012-09-28", "Trenton", 56, "Lincoln College Prep", 16),
    ("2012-10-12", "Trenton", 24, "Kirksville", 7),
    ("2012-09-07", "Central (New Madrid County)", 31, "Kennett", 7),
    ("2012-08-24", "Central (Park Hills)", 6, "Sullivan", 34),
    ("2012-08-31", "Central (Park Hills)", 35, "North County", 13),
    ("2012-09-07", "Fredericktown", 14, "Central (Park Hills)", 20),
    ("2012-09-21", "Central (Park Hills)", 21, "Ste. Genevieve", 22),
    ("2012-09-28", "Potosi", 6, "Central (Park Hills)", 33),
    ("2012-10-05", "Perryville", 0, "Central (Park Hills)", 35),
    ("2012-10-12", "Dexter", 7, "Central (Park Hills)", 27),
    ("2012-09-21", "Dexter", 26, "Kennett", 7),
    ("2012-08-24", "Kennett", 18, "Fredericktown", 40),
    ("2012-08-31", "Fredericktown", 42, "Hillsboro", 14),
    ("2012-10-19", "Fredericktown", 34, "North County", 35),
    ("2012-08-24", "Potosi", 55, "Confluence Prep Academy Charter", 6),
    ("2012-10-12", "North County", 41, "Potosi", 7),
    ("2012-10-19", "Potosi", 28, "DeSoto with Kingston", 42),
    ("2012-10-12", "Ste. Genevieve", 45, "DeSoto with Kingston", 7),
    ("2012-08-24", "St. Francis Borgia", 57, "Owensville", 7),
    ("2012-09-14", "Owensville", 7, "St. James", 14),
    ("2012-09-28", "Pacific", 49, "Owensville", 14),
    ("2012-10-05", "Owensville", 14, "Union", 49),
    ("2012-10-19", "St. Clair", 72, "Owensville", 0),
    ("2012-09-21", "St. James", 14, "Moberly", 52),
    ("2012-09-28", "St. James", 19, "St. Clair", 45),
    ("2012-10-12", "Union", 46, "St. James", 21),
    ("2012-10-19", "Pacific", 40, "St. James", 7),
    ("2012-08-24", "Ava", 6, "Aurora", 27),
    ("2012-08-31", "Logan-Rogersville", 12, "Ava", 14),
    ("2012-10-12", "Cabool", 7, "Ava", 47),
    ("2012-10-05", "Buffalo", 12, "Springfield Catholic", 24),
    ("2012-10-19", "Buffalo", 7, "Logan-Rogersville", 40),
    ("2012-09-07", "Logan-Rogersville", 10, "Springfield Catholic", 14),
    ("2012-09-14", "Marshfield", 34, "Logan-Rogersville", 42),
    ("2012-09-21", "Logan-Rogersville", 24, "Reeds Spring", 44),
    ("2012-09-28", "Aurora", 28, "Logan-Rogersville", 39),
    ("2012-10-05", "Logan-Rogersville", 14, "Bolivar", 56),
    ("2012-10-12", "Hollister", 34, "Logan-Rogersville", 54),
    ("2012-10-19", "Salem", 41, "Cabool", 21),
    ("2012-08-24", "East Newton", 12, "Springfield Catholic", 21),
    ("2012-09-21", "Springfield Catholic", 38, "Hollister", 6),
    ("2012-09-28", "Springfield Catholic", 21, "Reeds Spring", 18),
    ("2012-10-12", "Bolivar", 53, "Springfield Catholic", 0),
    ("2012-10-19", "Springfield Catholic", 35, "Marshfield", 34),
    ("2012-09-07", "Aurora", 27, "Seneca", 15),
    ("2012-09-21", "Aurora", 0, "Monett", 21),
    ("2012-09-14", "Seneca", 14, "Cassville", 18),
    ("2012-09-28", "Monett", 20, "Cassville", 30),
    ("2012-10-05", "Cassville", 42, "East Newton", 0),
    ("2012-10-19", "Mt. Vernon", 12, "Cassville", 21),
    ("2012-09-14", "Monett", 42, "East Newton", 14),
    ("2012-10-12", "East Newton", 7, "Lamar", 49),
    ("2012-10-19", "Seneca", 55, "East Newton", 16),
    ("2012-09-14", "Hollister", 0, "Bolivar", 38),
    ("2012-09-28", "Marshfield", 51, "Hollister", 16),
    ("2012-10-05", "Reeds Spring", 43, "Hollister", 14),
    ("2012-08-24", "Mt. Vernon", 26, "Monett", 10),
    ("2012-08-31", "Monett", 29, "Neosho", 7),
    ("2012-09-07", "McDonald County", 0, "Monett", 40),
    ("2012-10-12", "Monett", 34, "Seneca", 26),
    ("2012-10-19", "Carl Junction", 7, "Monett", 32),
    ("2012-09-28", "Seneca", 48, "Mt. Vernon", 20),
    ("2012-09-07", "Reeds Spring", 26, "Marshfield", 27),
    ("2012-10-19", "Reeds Spring", 16, "Bolivar", 37),
    ("2012-08-24", "Hillsboro", 28, "Duchesne", 15),
    ("2012-10-19", "Macon", 7, "Centralia", 20),
    ("2012-09-07", "Maryville", 49, "Chillicothe", 7),
    ("2012-09-14", "Chillicothe", 21, "Cameron", 10),
    ("2012-10-19", "Benton", 0, "Chillicothe", 21),
    ("2012-09-29", "Missouri Military Academy", 2, "Central (Kansas City)", 30),
    ("2012-09-07", "Center", 0, "Hogan Prep Academy Charter", 7),
    ("2012-09-28", "Warrensburg", 7, "Center", 35),
    ("2012-10-05", "Center", 54, "O'Hara", 14),
    ("2012-10-12", "Clinton", 27, "Warrensburg", 6),
    ("2012-09-13", "Hogan Prep Academy Charter", 33, "O'Hara", 14),
    ("2012-10-05", "Van Horn", 12, "Hogan Prep Academy Charter", 35),
    ("2012-10-13", "Hogan Prep Academy Charter", 64, "Southwest Early College", 0),
    ("2012-10-12", "Grain Valley", 7, "Oak Grove", 54),
    ("2012-10-19", "Odessa", 42, "Grain Valley", 26),
    ("2012-09-28", "Pembroke Hill", 62, "Southwest Early College", 8),
    ("2012-10-19", "East (Kansas City)", 6, "Pembroke Hill", 66),
    ("2012-08-31", "Cameron", 7, "Excelsior Springs", 31),
    ("2012-09-21", "Cameron", 0, "Maryville", 63),
    ("2012-10-12", "Benton", 21, "Cameron", 28),
    ("2012-09-07", "East (Kansas City)", 32, "Central (Kansas City)", 6),
    ("2012-09-14", "Richmond", 51, "Central (Kansas City)", 0),
    ("2012-09-20", "Central (Kansas City)", 0, "Derrick Thomas Academy", 8),
    ("2012-09-21", "Southwest Early College", 12, "East (Kansas City)", 48),
    ("2012-08-31", "Maryville", 43, "St. Pius X (Kansas City)", 7),
    ("2012-09-28", "Maryville", 56, "Benton", 7),
    ("2012-08-24", "Richmond", 28, "O'Hara", 14),
    ("2012-09-07", "Excelsior Springs", 55, "Richmond", 21),
    ("2012-10-05", "St. Pius X (Kansas City)", 28, "Warrensburg", 10),
    ("2012-10-12", "O'Hara", 19, "St. Pius X (Kansas City)", 20),
    ("2012-09-21", "North County", 42, "Farmington", 6),
    ("2012-09-07", "Windsor (Imperial)", 6, "Festus", 49),
    ("2012-09-14", "Festus", 34, "DeSoto with Kingston", 0),
    ("2012-09-21", "Hillsboro", 17, "Festus", 14),
    ("2012-09-28", "Festus", 48, "North County", 31),
    ("2012-10-05", "Pacific", 0, "Festus", 21),
    ("2012-10-12", "St. Charles West", 28, "Festus", 14),
    ("2012-09-14", "Hillsboro", 20, "North County", 26),
    ("2012-09-28", "Windsor (Imperial)", 22, "Hillsboro", 53),
    ("2012-10-05", "DeSoto with Kingston", 14, "Hillsboro", 54),
    ("2012-10-12", "Hillsboro", 49, "Lutheran South", 19),
    ("2012-09-07", "North County", 38, "DeSoto with Kingston", 0),
    ("2012-10-05", "North County", 52, "Windsor (Imperial)", 41),
    ("2012-10-19", "Windsor (Imperial)", 15, "Lutheran South", 41),
    ("2012-10-12", "De Smet Jesuit", 83, "Roosevelt", 0),
    ("2012-10-20", "Roosevelt", 43, "Derrick Thomas Academy", 0),
    ("2012-09-21", "DeSoto with Kingston", 35, "Windsor (Imperial)", 14),
    ("2012-08-24", "Washington", 24, "St. Clair", 35),
    ("2012-08-31", "DeSoto with Kingston", 13, "St. Clair", 55),
    ("2012-09-14", "Sullivan", 35, "St. Clair", 21),
    ("2012-09-21", "Union", 0, "St. Clair", 42),
    ("2012-10-12", "St. Clair", 41, "St. Francis Borgia", 12),
    ("2012-09-28", "Union", 28, "DeSoto with Kingston", 14),
    ("2012-09-21", "Bolivar", 38, "Marshfield", 0),
    ("2012-10-12", "Webb City", 28, "Ozark", 7),
    ("2012-08-24", "Gateway", 27, "Riverview Gardens", 24),
    ("2012-09-01", "Riverview Gardens", 14, "Normandy Collaborative", 13),
    ("2012-10-12", "Poplar Bluff", 13, "Normandy Collaborative", 12),
    ("2012-09-14", "Hickman", 21, "Helias Catholic", 14),
    ("2012-10-12", "Christian Brothers College", 42, "Helias Catholic", 14),
    ("2012-08-24", "Grain Valley", 6, "Savannah", 13),
    ("2012-08-31", "Benton", 13, "Grain Valley", 12),
    ("2012-09-07", "Grain Valley", 16, "Warrensburg", 6),
    ("2012-09-14", "Smith-Cotton", 14, "Grain Valley", 25),
    ("2012-10-06", "Grain Valley", 19, "Excelsior Springs", 47),
    ("2012-08-31", "Grandview", 42, "William Chrisman", 14),
    ("2012-08-24", "Excelsior Springs", 42, "Warrensburg", 0),
    ("2012-09-21", "Warrensburg", 18, "Smith-Cotton", 21),
    ("2012-10-19", "Warrensburg", 6, "O'Hara", 10),
    ("2012-08-24", "William Chrisman", 14, "Platte County", 31),
    ("2012-10-12", "St. Mary's (Independence)", 22, "Van Horn", 61),
    ("2012-10-12", "Hickman", 27, "Jackson", 14),
    ("2012-09-07", "De Smet Jesuit", 47, "Vianney", 19),
    ("2012-09-21", "Vianney", 6, "Christian Brothers College", 54),
    ("2012-09-28", "Christian Brothers College", 42, "Chaminade College Preparatory", 3),
    ("2012-10-05", "Vianney", 26, "Chaminade College Preparatory", 28),
    ("2012-09-29", "Hazelwood East", 44, "McCluer North", 21),
    ("2012-11-22", "Webster Groves", 29, "Kirkwood", 21),
    ("2012-08-31", "Hickman", 18, "Holt", 7),
    ("2012-09-07", "Hickman", 56, "Smith-Cotton", 7),
    ("2012-09-28", "O'Hara", 12, "Smith-Cotton", 17),
    ("2012-10-19", "Ozark", 55, "Neosho", 21),
    ("2012-10-05", "Ozark", 41, "Nixa", 21),
    ("2012-09-07", "Republic", 6, "Ozark", 48),
    ("2012-09-21", "Staley", 48, "Belton", 6),
    ("2012-09-29", "William Chrisman", 48, "Belton", 20),
    ("2012-09-28", "Fort Osage", 28, "Staley", 31),
    ("2012-10-05", "William Chrisman", 0, "Fort Osage", 36),
    ("2012-09-20", "North Kansas City", 21, "William Chrisman", 18),
    ("2012-08-31", "Staley", 48, "Raytown", 27),
    ("2012-09-14", "Raytown", 30, "William Chrisman", 6),
    ("2012-10-12", "Truman", 25, "William Chrisman", 27),
    ("2012-09-07", "William Chrisman", 28, "Staley", 56),
    ("2012-10-19", "William Chrisman", 39, "Oak Park", 22),
    ("2012-10-12", "Park Hill", 29, "Central (St. Joseph)", 32),
    ("2012-10-05", "Kearney", 30, "Staley", 35),
    ("2012-10-12", "Staley", 47, "Oak Park", 6),
    ("2012-09-07", "Lee's Summit", 46, "Park Hill", 24),
    ("2012-09-14", "Staley", 33, "Blue Springs South", 44),
    ("2012-08-30", "Eureka", 6, "Christian Brothers College", 30),
    ("2012-09-07", "Oakville", 14, "Lindbergh", 13),
    ("2012-09-14", "Lindbergh", 0, "Christian Brothers College", 35),
    ("2012-08-24", "Christian Brothers College", 34, "Ft. Zumwalt West", 13),
    ("2012-10-05", "De Smet Jesuit", 12, "Christian Brothers College", 49),
    ("2012-10-19", "Christian Brothers College", 13, "Francis Howell", 10),
    ("2012-09-21", "De Smet Jesuit", 24, "Jefferson City", 42),
    ("2012-09-28", "Jefferson City", 9, "Hickman", 14),
    ("2012-10-19", "Rockhurst", 34, "Hickman", 7),
]
 
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://www.mshsaa.org/"
}
 
# ---------------------------------------------------------------------------
# HTTP SESSION (connection reuse + retry on transient failures)
# ---------------------------------------------------------------------------
# Days that timeout right at the 20s ceiling get one retry with a short
# backoff before we give up on them. A shared Session reuses the underlying
# TCP connection instead of opening a fresh one per request, which by
# itself often reduces the frequency of these near-ceiling timeouts.
 
def build_session():
    from requests.adapters import HTTPAdapter
    try:
        from urllib3.util.retry import Retry
    except ImportError:
        from requests.packages.urllib3.util.retry import Retry
 
    session = requests.Session()
    retry = Retry(
        total=1,                      # one retry after the first failure
        connect=1,
        read=1,
        backoff_factor=1.5,           # short pause before the retry
        status_forcelist=[500, 502, 503, 504],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=1, pool_maxsize=1)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session
 
# ---------------------------------------------------------------------------
# CLASSIFICATIONS
# ---------------------------------------------------------------------------
 
def load_classifications(path=CLASSIFICATIONS_PATH):
    """Return team_to_class and team_to_district dicts keyed by school name."""
    with open(path) as f:
        data = json.load(f)
    team_to_class    = {}
    team_to_district = {}
    for entry in data["teams"]:
        school = entry["school"]
        team_to_class[school]    = entry["classification"]
        team_to_district[school] = entry["district"]
    return team_to_class, team_to_district
 
 
# ---------------------------------------------------------------------------
# NAME RESOLUTION
# ---------------------------------------------------------------------------
 
def build_id_to_classname(team_to_class, schools_csv=SCHOOLS_CSV):
    """
    Build { school_id_str : classification_name } by exact-matching
    mshsaa_schools.csv names to classifications.json names after stripping
    the ' High School' suffix. No fuzzy matching used.
 
    MANUAL_OVERRIDES covers the 21 schools whose mshsaa_schools.csv name
    does not match their classifications.json name. IDs were looked up
    directly from the MSHSAA scoreboard pages.
    """
    MANUAL_OVERRIDES = {
        "271": "Clopton with Elsberry",
        "331": "King City with Pattonsburg",
        "126": "Lockwood with Golden City",
        "421": "Princeton with Mercer",
        "424": "Rich Hill with Hume",
        "431": "Salisbury",
        "435": "Scott City",
        "443": "Skyline",
        "193": "Slater",
        "194": "Smith-Cotton",
        "197": "South Callaway",
        "549": "St. Mary's South Side",
        "463": "Stockton",
        "207": "Sullivan",
        "208": "Sumner",
        "469": "Sweet Springs with Malta Bend",
        "198": "Truman",
        "479": "University Academy Charter",
        "204": "Van Horn",
        "206": "Vashon",
        "20": "Appleton City with Montrose",
        "275": "Drexel with Miami (Amoret)",
        "575": "Renaissance Academy Charter",
        "172": "St. James",
        "35": "DeSoto with Kingston",
        "917": "Father Tolton with Calvary Lutheran",
        "342": "Liberal with Bronaugh",
        "776": "Transportation and Law with Beaumont",
        "483": "Van-Far with Community",
    }
 
    df = pd.read_csv(schools_csv)
    known_class_names = set(team_to_class.keys())
 
    id_to_classname = {}
    for _, row in df.iterrows():
        full_name = row["school_name"]
        sid       = str(row["school_id"])
        stripped  = full_name.replace(" High School", "").strip()
 
        if stripped in known_class_names:
            id_to_classname[sid] = stripped
        elif full_name in known_class_names:
            id_to_classname[sid] = full_name
 
    # Apply manual overrides last so they always take priority
    id_to_classname.update(MANUAL_OVERRIDES)
 
    print(f"  [name-resolve] {len(id_to_classname)} schools mapped by ID "
          f"({len(MANUAL_OVERRIDES)} via manual overrides)")
    return id_to_classname
 
 
def resolve_name(cell, id_to_classname, known_teams):
    """
    Resolve a scoreboard table cell to a classification name.
 
    Step 1: Extract s= ID from href → look up in id_to_classname.
            Handles renamed/merged schools (e.g. 'Scott City with Chaffee'
            → 'Scott City') because the ID in the href never changes.
    Step 2: Exact match of display text against known_teams.
            Handles co-op names that exist in classifications as-is.
    Returns None if unresolvable — game will be skipped.
    """
    a = cell.find("a", href=lambda h: h and "/MySchool/Schedule.aspx" in h)
    if not a:
        return None
 
    # Step 1: ID-based lookup
    href  = a.get("href", "")
    match = re.search(r"[?&]s=(\d+)", href, re.IGNORECASE)
    if match:
        sid = match.group(1)
        if sid in id_to_classname:
            return id_to_classname[sid]
 
    # Step 2: Exact display text match
    display_text = a.get_text(strip=True)
    if display_text in known_teams:
        return display_text
 
    return None
 
 
# ---------------------------------------------------------------------------
# SCRAPING
# ---------------------------------------------------------------------------
 
def is_mshsaa_team(cell):
    return cell.find(
        "a", href=lambda h: h and "/MySchool/Schedule.aspx" in h
    ) is not None
 
 
def parse_score(text):
    text = text.strip()
    if not text:
        return None
    try:
        score = int(text)
    except ValueError:
        return None
    return score if 0 <= score <= MAX_POINTS else None
 
 
def is_forfeit(c1, c2):
    return "forfeit" in (c1.get_text() + c2.get_text()).lower()
 
 
def scrape_date(target_date, id_to_classname, known_teams, session):
    url = BASE_URL.format(target_date.strftime("%m%d%Y"))
    try:
        # (connect_timeout, read_timeout) -- 10s to connect, 25s to read.
        # 25s (vs. the old flat 20s) gives borderline-slow responses (the
        # ~20.6-20.9s ones you saw) a real chance to finish instead of
        # being cut off right before they would have succeeded.
        resp = session.get(url, timeout=(10, 25), headers=HEADERS)
        resp.raise_for_status()
    except requests.exceptions.Timeout as e:
        print(f"  TIMEOUT {target_date}: {e}")
        return [], "timeout"
    except requests.RequestException as e:
        print(f"  Failed {target_date}: {e}")
        return [], "error"
 
    soup  = BeautifulSoup(resp.text, "html.parser")
    games = []
 
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if len(rows) < 3:
            continue
        if "final" not in rows[-1].get_text().lower():
            continue
 
        t1c = rows[1].find_all("td")
        t2c = rows[2].find_all("td")
        if len(t1c) < 3 or len(t2c) < 3:
            continue
        if not is_mshsaa_team(t1c[1]) or not is_mshsaa_team(t2c[1]):
            continue
        if is_forfeit(t1c[1], t2c[1]):
            continue
 
        name1 = resolve_name(t1c[1], id_to_classname, known_teams)
        name2 = resolve_name(t2c[1], id_to_classname, known_teams)
 
        if name1 is None or name2 is None:
            continue
 
        s1 = parse_score(t1c[2].get_text())
        s2 = parse_score(t2c[2].get_text())
        if s1 is None or s2 is None:
            continue
 
        games.append((
            target_date.strftime("%Y-%m-%d"),
            name1, s1,
            name2, s2
        ))
 
    return games, None
 
 
def scrape_full_season(id_to_classname, known_teams):
    all_games     = []
    current       = SEASON_START
    scrape_t0     = time.perf_counter()
    slow_days     = []   # (date, seconds) for anything taking > 3s
    failed_days   = []   # (date, reason) for anything that never succeeded
    session       = build_session()
 
    while current <= min(SEASON_END, date.today()):
        day_t0 = time.perf_counter()
        print(f"  Scraping {current}...", end=" ", flush=True)
        day_games, fail_reason = scrape_date(current, id_to_classname, known_teams, session)
        all_games.extend(day_games)
        day_elapsed = time.perf_counter() - day_t0
        print(f"{len(day_games)} games ({day_elapsed:.1f}s)")
        if day_elapsed > 3.0:
            slow_days.append((current, day_elapsed))
        if fail_reason is not None:
            failed_days.append((current, fail_reason))
        current += timedelta(days=1)
        time.sleep(0.5)
 
    scrape_elapsed = time.perf_counter() - scrape_t0
    print(f"\n  [TIMING] Scraping took {scrape_elapsed:.1f}s total "
          f"for {len(all_games)} games.")
    if slow_days:
        print(f"  [TIMING] {len(slow_days)} slow day(s) (>3s each):")
        for d, secs in slow_days:
            print(f"    {d}: {secs:.1f}s")
    if failed_days:
        print(f"\n  *** {len(failed_days)} date(s) NEVER returned data, "
              f"even after retry -- these dates may be missing real "
              f"games. Check them manually against MSHSAA and add via "
              f"MANUAL_GAMES if needed: ***")
        for d, reason in failed_days:
            print(f"    {d} ({reason})")
    else:
        print("  All dates returned successfully -- no known data gaps "
              "from scraping failures.")
    return all_games
 
 
def deduplicate_games(all_games):
    """
    Remove duplicate games where the same two teams played on the same date
    with the same scores, regardless of which team is listed as home or away.
 
    A game is considered a duplicate if another game exists with:
      - The same date
      - The same two team names (in either order)
      - The same two scores (in either order)
 
    The key is built from a frozenset of (team, score) pairs so that
    (Date, Team A, 54, Team B, 13) and (Date, Team B, 13, Team A, 54)
    produce the same key and only one is kept.
    """
    seen         = set()
    unique_games = []
    duplicates   = 0
 
    for game in all_games:
        date_str, t1, s1, t2, s2 = game
        # Key is date + frozenset of team names only — order independent.
        # Scores are intentionally excluded so that (Team A home, Team B away)
        # and (Team B home, Team A away) on the same date are always treated
        # as the same game regardless of which score appears first.
        key = (date_str, frozenset([t1, t2]))
        if key in seen:
            duplicates += 1
            continue
        seen.add(key)
        unique_games.append(game)
 
    if duplicates:
        print(f"  Removed {duplicates} duplicate game(s). "
              f"{len(unique_games)} unique games remain.")
    else:
        print(f"  No duplicates found. {len(unique_games)} games.")
 
    return unique_games
 
 
def report_missing_teams(all_games, team_to_class):
    """
    After scraping is complete, compare every team in classifications.json
    against the teams that actually appeared in scraped games.
    Print only the teams that have zero games — these are the ones that
    genuinely need attention (either their ID needs adding or their
    classifications.json name needs correcting).
    """
    teams_with_games = set()
    for _, t1, _, t2, _ in all_games:
        teams_with_games.add(t1)
        teams_with_games.add(t2)
 
    missing = sorted(
        t for t in team_to_class if t not in teams_with_games
    )
 
    if missing:
        print(f"\n  MISSING TEAMS: {len(missing)} classification schools have "
              f"no games in the scraped data.")
        print(f"  These teams need attention — either their MSHSAA page shows")
        print(f"  a different name than classifications.json, or they did not")
        print(f"  play any games this season.")
        print(f"  Missing: {missing}\n")
    else:
        print("\n  All classification schools have at least one game. \n")
 
 
# ---------------------------------------------------------------------------
# CSV OUTPUT
# ---------------------------------------------------------------------------
 
def save_csv(all_games):
    with open(CSV_PATH, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Date", "Home Team", "Home Score", "Away Team", "Away Score"])
        for date_str, t1, s1, t2, s2 in all_games:
            writer.writerow([date_str, t1, s1, t2, s2])
    print(f"Saved {len(all_games)} games to {CSV_PATH}")
 
 
# ---------------------------------------------------------------------------
# RATING ENGINE (v2 -- soft competitiveness weighting + shrinkage regularization)
# ---------------------------------------------------------------------------
#
# Replaces the old two-phase (all games, then hard <=40pt cutoff) approach.
# A dominant team no longer has its rating fully decided by 1-2 close games:
#   1. competitiveness_weight() gives every game a smooth weight based on
#      the current rating gap, instead of an all-or-nothing 40-point cutoff.
#   2. REGULARIZATION_K shrinks updates for teams with little competitive
#      signal, instead of letting a tiny sample fully drive their rating.
#   3. MOV_CAP bounds how much error any single game -- even a fully-weighted
#      one -- can contribute, so no one result can swing a rating too hard.
 
def competitiveness_weight(gap, scale=COMPETITIVE_THRESHOLD):
    """
    Smooth weight in (0, 1] based on the current OVR gap between two teams.
    gap=0            -> weight 1.0 (fully counted)
    gap=scale (40)   -> weight 0.5 (half counted)
    gap=2*scale (80) -> weight 0.2 (mostly discounted, never fully zero)
    """
    return 1.0 / (1.0 + (gap / scale) ** 2)
 
 
def run_iterations(games, teams, off_rating, def_rating, league_avg,
                   iterations, phase_label="Fit"):
    for iteration in range(iterations):
        off_error  = {t: 0.0 for t in teams}
        def_error  = {t: 0.0 for t in teams}
        weight_sum = {t: 0.0 for t in teams}
 
        for t1, t2, actual_s1, actual_s2 in games:
            gap = abs((off_rating[t1] + def_rating[t1]) -
                      (off_rating[t2] + def_rating[t2]))
            w = competitiveness_weight(gap)
 
            predicted_s1 = off_rating[t1] - def_rating[t2] + league_avg
            predicted_s2 = off_rating[t2] - def_rating[t1] + league_avg
 
            error_s1 = actual_s1 - predicted_s1
            error_s2 = actual_s2 - predicted_s2
 
            # MOV cap: bound the raw error before it's weighted/accumulated
            error_s1 = max(-MOV_CAP, min(MOV_CAP, error_s1))
            error_s2 = max(-MOV_CAP, min(MOV_CAP, error_s2))
 
            off_error[t1] += w * error_s1
            off_error[t2] += w * error_s2
            def_error[t1] += -w * error_s2
            def_error[t2] += -w * error_s1
 
            weight_sum[t1] += w
            weight_sum[t2] += w
 
        for team in teams:
            # Shrinkage: denominator is (weighted games) + K, not just raw
            # games played. Teams with low competitive weight get smaller,
            # more conservative updates instead of being fully driven by
            # 1-2 games.
            denom = weight_sum[team] + REGULARIZATION_K
            off_rating[team] += (off_error[team] / denom) * LEARNING_RATE
            def_rating[team] += (def_error[team] / denom) * LEARNING_RATE
 
        if (iteration + 1) % 100 == 0:
            print(f"  [{phase_label}] Iteration {iteration + 1}/{iterations} complete")
 
 
def calculate_ratings(all_games, iterations=ITERATIONS):
    games = [(t1, t2, s1, s2) for _, t1, s1, t2, s2 in all_games]
 
    teams = list({t for t1, t2, _, _ in games for t in (t1, t2)})
    if not teams:
        return {}, {}, {}, 0
 
    all_scores = [s for _, _, s1, s2 in games for s in (s1, s2)]
    league_avg = sum(all_scores) / len(all_scores)
    print(f"  League average: {league_avg:.2f} points per game")
 
    off_rating = {t: 0.0 for t in teams}
    def_rating = {t: 0.0 for t in teams}
 
    print(f"\n  Running rating fit ({iterations} iterations, soft-weighted "
          f"by competitiveness [scale={COMPETITIVE_THRESHOLD}], "
          f"shrinkage K={REGULARIZATION_K}, MOV cap={MOV_CAP})...")
    print(f"  [TIMING] {len(teams)} teams, {len(games)} games going into the fit.")
    engine_t0 = time.perf_counter()
    run_iterations(games, teams, off_rating, def_rating, league_avg,
                   iterations=iterations, phase_label="Fit")
    print(f"  [TIMING] Rating fit took {time.perf_counter() - engine_t0:.1f}s.")
 
    ovr_rating = {t: round(off_rating[t] + def_rating[t], 2) for t in teams}
    return off_rating, def_rating, ovr_rating, league_avg
# ---------------------------------------------------------------------------
# JSON OUTPUT
# ---------------------------------------------------------------------------
 
def build_team_entries(off_rating, def_rating, ovr_rating,
                       team_to_class, team_to_district,
                       class_filter=None):
    all_teams = list(ovr_rating.keys())
 
    pool = (
        [t for t in all_teams if team_to_class.get(t) == class_filter]
        if class_filter is not None
        else all_teams
    )
 
    ovr_sorted = sorted(pool, key=lambda t: ovr_rating[t], reverse=True)
    off_sorted = sorted(pool, key=lambda t: off_rating[t], reverse=True)
    def_sorted = sorted(pool, key=lambda t: def_rating[t], reverse=True)
 
    ovr_rank = {t: i + 1 for i, t in enumerate(ovr_sorted)}
    off_rank = {t: i + 1 for i, t in enumerate(off_sorted)}
    def_rank = {t: i + 1 for i, t in enumerate(def_sorted)}
 
    return [
        {
            "ovr_rank":       ovr_rank[t],
            "school":         t,
            "classification": team_to_class.get(t),
            "district":       team_to_district.get(t),
            "ovr_rating":     ovr_rating[t],
            "off_rating":     round(off_rating[t], 2),
            "off_rank":       off_rank[t],
            "def_rating":     round(def_rating[t], 2),
            "def_rank":       def_rank[t],
        }
        for t in ovr_sorted
    ]
 
 
def save_overall_json(off_rating, def_rating, ovr_rating, league_avg,
                      team_to_class, team_to_district):
    entries = build_team_entries(off_rating, def_rating, ovr_rating,
                                 team_to_class, team_to_district)
    output = {
        "last_updated":   datetime.now().strftime("%B %d, %Y at %I:%M %p"),
        "league_average": round(league_avg, 2),
        "teams": entries,
    }
    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2)
 
    print(f"Saved {len(entries)} teams to {OUTPUT_PATH}")
    print("Top 5 overall:")
    for e in entries[:5]:
        print(f"  {e['ovr_rank']}. {e['school']} (Class {e['classification']}) "
              f"| OVR: {e['ovr_rating']:+.2f} "
              f"| OFF: {e['off_rating']:+.2f} "
              f"| DEF: {e['def_rating']:+.2f}")
 
 
def save_class_jsons(off_rating, def_rating, ovr_rating, league_avg,
                     team_to_class, team_to_district):
    for cls in range(1, 7):
        entries = build_team_entries(off_rating, def_rating, ovr_rating,
                                     team_to_class, team_to_district,
                                     class_filter=cls)
        if not entries:
            print(f"  Class {cls}: no teams found — skipping.")
            continue
 
        path = f"football_ratings_{SEASON_YEAR}_class{cls}.json"
        output = {
            "last_updated":   datetime.now().strftime("%B %d, %Y at %I:%M %p"),
            "league_average": round(league_avg, 2),
            "classification": cls,
            "teams": entries,
        }
        with open(path, "w") as f:
            json.dump(output, f, indent=2)
 
        print(f"  Class {cls}: {len(entries)} teams → {path}")
        print("    Top 3: " + " | ".join(
            f"{e['ovr_rank']}. {e['school']} ({e['ovr_rating']:+.2f})"
            for e in entries[:3]
        ))
 
 
 
# ---------------------------------------------------------------------------
# CSV RANKINGS OUTPUT
# ---------------------------------------------------------------------------
 
def save_rankings_csv(off_rating, def_rating, ovr_rating,
                      team_to_class, team_to_district,
                      class_filter=None):
    """
    Save a rankings CSV for either all teams (class_filter=None) or a
    specific class.  Rankings (OFF Rank, DEF Rank, OVR Rank) are computed
    within the pool so class CSVs show class-specific ranks.
 
    Columns: School, OFF Rating, DEF Rating, OVR Rating,
             OFF Rank, DEF Rank, OVR Rank
    """
    all_teams = list(ovr_rating.keys())
 
    pool = (
        [t for t in all_teams if team_to_class.get(t) == class_filter]
        if class_filter is not None
        else all_teams
    )
 
    if not pool:
        label = f"Class {class_filter}" if class_filter else "Overall"
        print(f"  {label}: no teams — skipping CSV.")
        return
 
    ovr_sorted = sorted(pool, key=lambda t: ovr_rating[t], reverse=True)
    off_sorted = sorted(pool, key=lambda t: off_rating[t], reverse=True)
    def_sorted = sorted(pool, key=lambda t: def_rating[t], reverse=True)
 
    ovr_rank = {t: i + 1 for i, t in enumerate(ovr_sorted)}
    off_rank = {t: i + 1 for i, t in enumerate(off_sorted)}
    def_rank = {t: i + 1 for i, t in enumerate(def_sorted)}
 
    rows = [
        {
            "School":      t,
            "OFF Rating":  round(off_rating[t], 2),
            "DEF Rating":  round(def_rating[t], 2),
            "OVR Rating":  round(ovr_rating[t], 2),
            "OFF Rank":    off_rank[t],
            "DEF Rank":    def_rank[t],
            "OVR Rank":    ovr_rank[t],
        }
        for t in ovr_sorted
    ]
 
    df = pd.DataFrame(rows, columns=[
        "School", "OFF Rating", "DEF Rating", "OVR Rating",
        "OFF Rank", "DEF Rank", "OVR Rank"
    ])
 
    if class_filter is None:
        path  = f"football_rankings_{SEASON_YEAR}_all.csv"
        label = "All teams"
    else:
        path  = f"football_rankings_{SEASON_YEAR}_class{class_filter}.csv"
        label = f"Class {class_filter}"
 
    df.to_csv(path, index=False)
    print(f"  {label}: {len(df)} teams — {path}")
 
 
def save_all_rankings_csvs(off_rating, def_rating, ovr_rating,
                           team_to_class, team_to_district):
    """Save overall + one CSV per class (1-6)."""
    save_rankings_csv(off_rating, def_rating, ovr_rating,
                      team_to_class, team_to_district,
                      class_filter=None)
    for cls in range(1, 7):
        save_rankings_csv(off_rating, def_rating, ovr_rating,
                          team_to_class, team_to_district,
                          class_filter=cls)
 
# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
 
if __name__ == "__main__":
    print(f"=== MSHSAA Football Ratings {SEASON_YEAR} ===")
 
    print("\nLoading classifications...")
    team_to_class, team_to_district = load_classifications()
    known_teams = set(team_to_class.keys())
    print(f"  Loaded {len(team_to_class)} teams from {CLASSIFICATIONS_PATH}")
 
    print("\nBuilding school ID → classification name lookup...")
    id_to_classname = build_id_to_classname(team_to_class, SCHOOLS_CSV)
 
    print("\nScraping season scoreboard...")
    all_games = scrape_full_season(id_to_classname, known_teams)
    print(f"\nTotal valid games (before deduplication): {len(all_games)}")
    if not all_games:
        print("No games found — exiting.")
        exit(1)
 
    if MANUAL_GAMES:
        print(f"\nAdding {len(MANUAL_GAMES)} manual game(s)...")
        all_games.extend(MANUAL_GAMES)
 
    print("\nDeduplicating games...")
    all_games = deduplicate_games(all_games)
 
    print("\nChecking for missing teams...")
    report_missing_teams(all_games, team_to_class)
 
    print("Saving scoreboard CSV...")
    save_csv(all_games)
 
    print(f"\nRunning ratings engine "
          f"({ITERATIONS} Phase 1 + {ITERATIONS} Phase 2 iterations)...")
    off_rating, def_rating, ovr_rating, league_avg = calculate_ratings(all_games)
 
    print("\nSaving overall ratings JSON...")
    save_overall_json(off_rating, def_rating, ovr_rating, league_avg,
                      team_to_class, team_to_district)
 
    print("\nSaving per-class ratings JSONs...")
    save_class_jsons(off_rating, def_rating, ovr_rating, league_avg,
                     team_to_class, team_to_district)
 
    print("\nSaving rankings CSVs...")
    save_all_rankings_csvs(off_rating, def_rating, ovr_rating,
                           team_to_class, team_to_district)
 
    print("\n=== Done ===")
