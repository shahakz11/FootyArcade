#!/usr/bin/env python3
"""
scripts/geo_manager.py

Playmaker Geolocation & Flight Path Engine for Video Generation.
Maps clubs to verified stadium/city coordinates, handles great-circle
geodesic trajectory calculation, 3D spherical projections, and distance calculations.
"""

import os
import math
import json
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCATIONS_FILE = os.path.join(BASE_DIR, "data", "club_locations.json")

# Verified coordinates and cities for football clubs
DEFAULT_CLUB_MAPPINGS = {
    # England
    "Manchester United": {"city": "Manchester", "country": "England", "code": "ENG", "flag": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "lat": 53.4631, "lon": -2.2913},
    "Manchester City": {"city": "Manchester", "country": "England", "code": "ENG", "flag": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "lat": 53.4831, "lon": -2.2004},
    "Liverpool": {"city": "Liverpool", "country": "England", "code": "ENG", "flag": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "lat": 53.4308, "lon": -2.9608},
    "Arsenal": {"city": "London", "country": "England", "code": "ENG", "flag": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "lat": 51.5549, "lon": -0.1084},
    "Chelsea": {"city": "London", "country": "England", "code": "ENG", "flag": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "lat": 51.4816, "lon": -0.1910},
    "Tottenham Hotspur": {"city": "London", "country": "England", "code": "ENG", "flag": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "lat": 51.6042, "lon": -0.0662},
    "Tottenham": {"city": "London", "country": "England", "code": "ENG", "flag": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "lat": 51.6042, "lon": -0.0662},
    "West Ham United": {"city": "London", "country": "England", "code": "ENG", "flag": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "lat": 51.5387, "lon": -0.0166},
    "Fulham": {"city": "London", "country": "England", "code": "ENG", "flag": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "lat": 51.4749, "lon": -0.2217},
    "Brentford": {"city": "London", "country": "England", "code": "ENG", "flag": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "lat": 51.4907, "lon": -0.2887},
    "Crystal Palace": {"city": "London", "country": "England", "code": "ENG", "flag": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "lat": 51.3983, "lon": -0.0855},
    "Aston Villa": {"city": "Birmingham", "country": "England", "code": "ENG", "flag": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "lat": 52.5091, "lon": -1.8848},
    "Newcastle United": {"city": "Newcastle", "country": "England", "code": "ENG", "flag": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "lat": 54.9756, "lon": -1.6216},
    "Leicester City": {"city": "Leicester", "country": "England", "code": "ENG", "flag": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "lat": 52.6204, "lon": -1.1422},
    "Everton": {"city": "Liverpool", "country": "England", "code": "ENG", "flag": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "lat": 53.4388, "lon": -2.9663},
    "Wolverhampton Wanderers": {"city": "Wolverhampton", "country": "England", "code": "ENG", "flag": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "lat": 52.5902, "lon": -2.1304},
    "Brighton & Hove Albion": {"city": "Brighton", "country": "England", "code": "ENG", "flag": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "lat": 50.8616, "lon": -0.0837},
    "Southampton": {"city": "Southampton", "country": "England", "code": "ENG", "flag": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "lat": 50.9058, "lon": -1.3910},
    "Bournemouth": {"city": "Bournemouth", "country": "England", "code": "ENG", "flag": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "lat": 50.7352, "lon": -1.8383},
    "Nottingham Forest": {"city": "Nottingham", "country": "England", "code": "ENG", "flag": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "lat": 52.9400, "lon": -1.1328},
    "Leeds United": {"city": "Leeds", "country": "England", "code": "ENG", "flag": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "lat": 53.7778, "lon": -1.5722},
    "Burnley": {"city": "Burnley", "country": "England", "code": "ENG", "flag": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "lat": 53.7890, "lon": -2.2302},
    "Sheffield United": {"city": "Sheffield", "country": "England", "code": "ENG", "flag": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "lat": 53.3703, "lon": -1.4709},
    "Watford": {"city": "Watford", "country": "England", "code": "ENG", "flag": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "lat": 51.6499, "lon": -0.4015},
    "Norwich": {"city": "Norwich", "country": "England", "code": "ENG", "flag": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "lat": 52.6221, "lon": 1.3087},
    "Stoke City": {"city": "Stoke", "country": "England", "code": "ENG", "flag": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "lat": 52.9884, "lon": -2.1755},
    "Swansea": {"city": "Swansea", "country": "Wales", "code": "WAL", "flag": "🏴󠁧󠁢󠁷󠁬󠁳󠁿", "lat": 51.6428, "lon": -3.9351},
    "Rangers": {"city": "Glasgow", "country": "Scotland", "code": "SCO", "flag": "🏴󠁧󠁢󠁳󠁣󠁴󠁿", "lat": 55.8532, "lon": -4.3093},
    "Celtic": {"city": "Glasgow", "country": "Scotland", "code": "SCO", "flag": "🏴󠁧󠁢󠁳󠁣󠁴󠁿", "lat": 55.8497, "lon": -4.2055},

    # Spain
    "Real Madrid": {"city": "Madrid", "country": "Spain", "code": "ESP", "flag": "🇪🇸", "lat": 40.4530, "lon": -3.6883},
    "Barcelona": {"city": "Barcelona", "country": "Spain", "code": "ESP", "flag": "🇪🇸", "lat": 41.3809, "lon": 2.1228},
    "FC Barcelona": {"city": "Barcelona", "country": "Spain", "code": "ESP", "flag": "🇪🇸", "lat": 41.3809, "lon": 2.1228},
    "Atletico Madrid": {"city": "Madrid", "country": "Spain", "code": "ESP", "flag": "🇪🇸", "lat": 40.4362, "lon": -3.5996},
    "Sevilla": {"city": "Seville", "country": "Spain", "code": "ESP", "flag": "🇪🇸", "lat": 37.3840, "lon": -5.9706},
    "Real Betis": {"city": "Seville", "country": "Spain", "code": "ESP", "flag": "🇪🇸", "lat": 37.3565, "lon": -5.9818},
    "Valencia": {"city": "Valencia", "country": "Spain", "code": "ESP", "flag": "🇪🇸", "lat": 39.4746, "lon": -0.3584},
    "Villarreal": {"city": "Villarreal", "country": "Spain", "code": "ESP", "flag": "🇪🇸", "lat": 39.9442, "lon": -0.1037},
    "Real Sociedad": {"city": "San Sebastián", "country": "Spain", "code": "ESP", "flag": "🇪🇸", "lat": 43.3015, "lon": -1.9736},
    "Athletic Bilbao": {"city": "Bilbao", "country": "Spain", "code": "ESP", "flag": "🇪🇸", "lat": 43.2641, "lon": -2.9493},
    "Athletic": {"city": "Bilbao", "country": "Spain", "code": "ESP", "flag": "🇪🇸", "lat": 43.2641, "lon": -2.9493},
    "Celta Vigo": {"city": "Vigo", "country": "Spain", "code": "ESP", "flag": "🇪🇸", "lat": 42.2118, "lon": -8.7397},
    "Girona": {"city": "Girona", "country": "Spain", "code": "ESP", "flag": "🇪🇸", "lat": 41.9610, "lon": 2.8286},
    "Mallorca": {"city": "Palma", "country": "Spain", "code": "ESP", "flag": "🇪🇸", "lat": 39.5900, "lon": 2.6300},
    "Almería": {"city": "Almería", "country": "Spain", "code": "ESP", "flag": "🇪🇸", "lat": 36.8400, "lon": -2.4356},
    "Granada": {"city": "Granada", "country": "Spain", "code": "ESP", "flag": "🇪🇸", "lat": 37.1528, "lon": -3.5956},
    "Espanyol": {"city": "Barcelona", "country": "Spain", "code": "ESP", "flag": "🇪🇸", "lat": 41.3478, "lon": 2.0756},
    "Getafe": {"city": "Getafe", "country": "Spain", "code": "ESP", "flag": "🇪🇸", "lat": 40.3256, "lon": -3.7149},
    "Rayo Vallecano": {"city": "Madrid", "country": "Spain", "code": "ESP", "flag": "🇪🇸", "lat": 40.3919, "lon": -3.6587},
    "Leganés": {"city": "Leganés", "country": "Spain", "code": "ESP", "flag": "🇪🇸", "lat": 40.3400, "lon": -3.7607},

    # Italy
    "Juventus": {"city": "Turin", "country": "Italy", "code": "ITA", "flag": "🇮🇹", "lat": 45.1096, "lon": 7.6413},
    "Torino": {"city": "Turin", "country": "Italy", "code": "ITA", "flag": "🇮🇹", "lat": 45.0418, "lon": 7.6501},
    "AC Milan": {"city": "Milan", "country": "Italy", "code": "ITA", "flag": "🇮🇹", "lat": 45.4781, "lon": 9.1240},
    "Inter": {"city": "Milan", "country": "Italy", "code": "ITA", "flag": "🇮🇹", "lat": 45.4781, "lon": 9.1240},
    "Inter Milan": {"city": "Milan", "country": "Italy", "code": "ITA", "flag": "🇮🇹", "lat": 45.4781, "lon": 9.1240},
    "Napoli": {"city": "Naples", "country": "Italy", "code": "ITA", "flag": "🇮🇹", "lat": 40.8279, "lon": 14.1930},
    "Roma": {"city": "Rome", "country": "Italy", "code": "ITA", "flag": "🇮🇹", "lat": 41.9341, "lon": 12.4547},
    "Lazio": {"city": "Rome", "country": "Italy", "code": "ITA", "flag": "🇮🇹", "lat": 41.9341, "lon": 12.4547},
    "Atalanta": {"city": "Bergamo", "country": "Italy", "code": "ITA", "flag": "🇮🇹", "lat": 45.7088, "lon": 9.6806},
    "Fiorentina": {"city": "Florence", "country": "Italy", "code": "ITA", "flag": "🇮🇹", "lat": 43.7808, "lon": 11.2825},
    "Bologna": {"city": "Bologna", "country": "Italy", "code": "ITA", "flag": "🇮🇹", "lat": 44.4922, "lon": 11.3097},
    "Genoa": {"city": "Genoa", "country": "Italy", "code": "ITA", "flag": "🇮🇹", "lat": 44.4165, "lon": 8.9526},
    "Sampdoria": {"city": "Genoa", "country": "Italy", "code": "ITA", "flag": "🇮🇹", "lat": 44.4165, "lon": 8.9526},
    "Sassuolo": {"city": "Reggio Emilia", "country": "Italy", "code": "ITA", "flag": "🇮🇹", "lat": 44.7147, "lon": 10.6492},
    "Udinese": {"city": "Udine", "country": "Italy", "code": "ITA", "flag": "🇮🇹", "lat": 46.0816, "lon": 13.2001},
    "Hellas Verona": {"city": "Verona", "country": "Italy", "code": "ITA", "flag": "🇮🇹", "lat": 45.4354, "lon": 10.9686},
    "Cagliari": {"city": "Cagliari", "country": "Italy", "code": "ITA", "flag": "🇮🇹", "lat": 39.2000, "lon": 9.1389},
    "Parma": {"city": "Parma", "country": "Italy", "code": "ITA", "flag": "🇮🇹", "lat": 44.8015, "lon": 10.3389},
    "Salernitana": {"city": "Salerno", "country": "Italy", "code": "ITA", "flag": "🇮🇹", "lat": 40.6472, "lon": 14.8239},
    "Como": {"city": "Como", "country": "Italy", "code": "ITA", "flag": "🇮🇹", "lat": 45.8130, "lon": 9.0744},

    # Germany
    "Bayern Munich": {"city": "Munich", "country": "Germany", "code": "GER", "flag": "🇩🇪", "lat": 48.2188, "lon": 11.6247},
    "Bayern": {"city": "Munich", "country": "Germany", "code": "GER", "flag": "🇩🇪", "lat": 48.2188, "lon": 11.6247},
    "Borussia Dortmund": {"city": "Dortmund", "country": "Germany", "code": "GER", "flag": "🇩🇪", "lat": 51.4926, "lon": 7.4518},
    "Bayer Leverkusen": {"city": "Leverkusen", "country": "Germany", "code": "GER", "flag": "🇩🇪", "lat": 51.0383, "lon": 7.0022},
    "RB Leipzig": {"city": "Leipzig", "country": "Germany", "code": "GER", "flag": "🇩🇪", "lat": 51.3458, "lon": 12.3483},
    "Eintracht Frankfurt": {"city": "Frankfurt", "country": "Germany", "code": "GER", "flag": "🇩🇪", "lat": 50.0686, "lon": 8.6455},
    "VfB Stuttgart": {"city": "Stuttgart", "country": "Germany", "code": "GER", "flag": "🇩🇪", "lat": 48.7922, "lon": 9.2320},
    "Stuttgart": {"city": "Stuttgart", "country": "Germany", "code": "GER", "flag": "🇩🇪", "lat": 48.7922, "lon": 9.2320},
    "Wolfsburg": {"city": "Wolfsburg", "country": "Germany", "code": "GER", "flag": "🇩🇪", "lat": 52.4326, "lon": 10.8037},
    "Borussia Mönchengladbach": {"city": "Mönchengladbach", "country": "Germany", "code": "GER", "flag": "🇩🇪", "lat": 51.1746, "lon": 6.3855},
    "Mönchengladbach": {"city": "Mönchengladbach", "country": "Germany", "code": "GER", "flag": "🇩🇪", "lat": 51.1746, "lon": 6.3855},
    "FC Schalke 04": {"city": "Gelsenkirchen", "country": "Germany", "code": "GER", "flag": "🇩🇪", "lat": 51.5544, "lon": 7.0675},
    "Hoffenheim": {"city": "Sinsheim", "country": "Germany", "code": "GER", "flag": "🇩🇪", "lat": 49.2381, "lon": 8.8872},
    "Werder Bremen": {"city": "Bremen", "country": "Germany", "code": "GER", "flag": "🇩🇪", "lat": 53.0664, "lon": 8.8375},
    "Union Berlin": {"city": "Berlin", "country": "Germany", "code": "GER", "flag": "🇩🇪", "lat": 52.4572, "lon": 13.5681},
    "Hertha Berlin": {"city": "Berlin", "country": "Germany", "code": "GER", "flag": "🇩🇪", "lat": 52.5147, "lon": 13.2394},

    # France
    "Paris Saint-Germain": {"city": "Paris", "country": "France", "code": "FRA", "flag": "🇫🇷", "lat": 48.8414, "lon": 2.2530},
    "Marseille": {"city": "Marseille", "country": "France", "code": "FRA", "flag": "🇫🇷", "lat": 43.2699, "lon": 5.3959},
    "Lyon": {"city": "Lyon", "country": "France", "code": "FRA", "flag": "🇫🇷", "lat": 45.7653, "lon": 4.9820},
    "Monaco": {"city": "Monaco", "country": "Monaco", "code": "MCO", "flag": "🇲🇨", "lat": 43.7276, "lon": 7.4156},
    "Lille": {"city": "Lille", "country": "France", "code": "FRA", "flag": "🇫🇷", "lat": 50.6119, "lon": 3.1305},
    "Rennes": {"city": "Rennes", "country": "France", "code": "FRA", "flag": "🇫🇷", "lat": 48.1075, "lon": -1.7128},
    "Nice": {"city": "Nice", "country": "France", "code": "FRA", "flag": "🇫🇷", "lat": 43.7053, "lon": 7.1926},
    "Lens": {"city": "Lens", "country": "France", "code": "FRA", "flag": "🇫🇷", "lat": 50.4328, "lon": 2.8150},
    "Nantes": {"city": "Nantes", "country": "France", "code": "FRA", "flag": "🇫🇷", "lat": 47.2560, "lon": -1.5247},
    "Bordeaux": {"city": "Bordeaux", "country": "France", "code": "FRA", "flag": "🇫🇷", "lat": 44.8969, "lon": -0.5631},
    "Toulouse": {"city": "Toulouse", "country": "France", "code": "FRA", "flag": "🇫🇷", "lat": 43.5833, "lon": 1.4342},
    "Stade Reims": {"city": "Reims", "country": "France", "code": "FRA", "flag": "🇫🇷", "lat": 49.2464, "lon": 4.0250},
    "Brest": {"city": "Brest", "country": "France", "code": "FRA", "flag": "🇫🇷", "lat": 48.4031, "lon": -4.4981},
    "Lorient": {"city": "Lorient", "country": "France", "code": "FRA", "flag": "🇫🇷", "lat": 47.7486, "lon": -3.3697},
    "Saint-Étienne": {"city": "Saint-Étienne", "country": "France", "code": "FRA", "flag": "🇫🇷", "lat": 45.4608, "lon": 4.3900},
    "St-Étienne": {"city": "Saint-Étienne", "country": "France", "code": "FRA", "flag": "🇫🇷", "lat": 45.4608, "lon": 4.3900},
    "AJ Auxerre": {"city": "Auxerre", "country": "France", "code": "FRA", "flag": "🇫🇷", "lat": 47.7867, "lon": 3.5881},
    "Metz": {"city": "Metz", "country": "France", "code": "FRA", "flag": "🇫🇷", "lat": 49.1097, "lon": 6.1528},

    # Portugal
    "Benfica": {"city": "Lisbon", "country": "Portugal", "code": "POR", "flag": "🇵🇹", "lat": 38.7527, "lon": -9.1847},
    "Sporting CP": {"city": "Lisbon", "country": "Portugal", "code": "POR", "flag": "🇵🇹", "lat": 38.7612, "lon": -9.1608},
    "Porto": {"city": "Porto", "country": "Portugal", "code": "POR", "flag": "🇵🇹", "lat": 41.1618, "lon": -8.5836},
    "Braga": {"city": "Braga", "country": "Portugal", "code": "POR", "flag": "🇵🇹", "lat": 41.5624, "lon": -8.4297},
    "Vitória Setúbal": {"city": "Setúbal", "country": "Portugal", "code": "POR", "flag": "🇵🇹", "lat": 38.5244, "lon": -8.8882},
    "Portimonense": {"city": "Portimão", "country": "Portugal", "code": "POR", "flag": "🇵🇹", "lat": 37.1363, "lon": -8.5375},
    "Famalicão": {"city": "Famalicão", "country": "Portugal", "code": "POR", "flag": "🇵🇹", "lat": 41.4082, "lon": -8.5196},

    # Netherlands & Belgium
    "Ajax": {"city": "Amsterdam", "country": "Netherlands", "code": "NED", "flag": "🇳🇱", "lat": 52.3144, "lon": 4.9426},
    "PSV Eindhoven": {"city": "Eindhoven", "country": "Netherlands", "code": "NED", "flag": "🇳🇱", "lat": 51.4418, "lon": 5.4678},
    "Feyenoord": {"city": "Rotterdam", "country": "Netherlands", "code": "NED", "flag": "🇳🇱", "lat": 51.8939, "lon": 4.5231},
    "AZ Alkmaar": {"city": "Alkmaar", "country": "Netherlands", "code": "NED", "flag": "🇳🇱", "lat": 52.6125, "lon": 4.7422},
    "AZ": {"city": "Alkmaar", "country": "Netherlands", "code": "NED", "flag": "🇳🇱", "lat": 52.6125, "lon": 4.7422},
    "Anderlecht": {"city": "Brussels", "country": "Belgium", "code": "BEL", "flag": "🇧🇪", "lat": 50.8344, "lon": 4.2983},
    "RSC Anderlecht": {"city": "Brussels", "country": "Belgium", "code": "BEL", "flag": "🇧🇪", "lat": 50.8344, "lon": 4.2983},
    "Brugge": {"city": "Bruges", "country": "Belgium", "code": "BEL", "flag": "🇧🇪", "lat": 51.1931, "lon": 3.1806},
    "KRC Genk": {"city": "Genk", "country": "Belgium", "code": "BEL", "flag": "🇧🇪", "lat": 50.9908, "lon": 5.5331},
    "Standard Liège": {"city": "Liège", "country": "Belgium", "code": "BEL", "flag": "🇧🇪", "lat": 50.6100, "lon": 5.5433},

    # Turkey & Greece
    "Galatasaray": {"city": "Istanbul", "country": "Turkey", "code": "TUR", "flag": "🇹🇷", "lat": 41.1033, "lon": 28.9911},
    "Fenerbahce": {"city": "Istanbul", "country": "Turkey", "code": "TUR", "flag": "🇹🇷", "lat": 40.9878, "lon": 29.0369},
    "Besiktas": {"city": "Istanbul", "country": "Turkey", "code": "TUR", "flag": "🇹🇷", "lat": 41.0392, "lon": 28.9947},
    "Antalyaspor": {"city": "Antalya", "country": "Turkey", "code": "TUR", "flag": "🇹🇷", "lat": 36.8872, "lon": 30.6592},
    "Olympiacos": {"city": "Piraeus", "country": "Greece", "code": "GRE", "flag": "🇬🇷", "lat": 37.9464, "lon": 23.6644},
    "PAOK": {"city": "Thessaloniki", "country": "Greece", "code": "GRE", "flag": "🇬🇷", "lat": 40.6139, "lon": 22.9725},
    "AEK Athens": {"city": "Athens", "country": "Greece", "code": "GRE", "flag": "🇬🇷", "lat": 38.0378, "lon": 23.7422},

    # Saudi Arabia & Middle East
    "Al-Hilal": {"city": "Riyadh", "country": "Saudi Arabia", "code": "KSA", "flag": "🇸🇦", "lat": 24.6869, "lon": 46.6853},
    "Al-Nassr": {"city": "Riyadh", "country": "Saudi Arabia", "code": "KSA", "flag": "🇸🇦", "lat": 24.7292, "lon": 46.6236},
    "Al-Ittihad": {"city": "Jeddah", "country": "Saudi Arabia", "code": "KSA", "flag": "🇸🇦", "lat": 21.6167, "lon": 39.1583},
    "Al-Ahli": {"city": "Jeddah", "country": "Saudi Arabia", "code": "KSA", "flag": "🇸🇦", "lat": 21.5433, "lon": 39.1728},
    "Al-Qadsiah": {"city": "Khobar", "country": "Saudi Arabia", "code": "KSA", "flag": "🇸🇦", "lat": 26.2819, "lon": 50.2083},
    "Al-Duhail": {"city": "Doha", "country": "Qatar", "code": "QAT", "flag": "🇶🇦", "lat": 25.3789, "lon": 51.4883},
    "Al-Ain": {"city": "Al Ain", "country": "UAE", "code": "UAE", "flag": "🇦🇪", "lat": 24.2075, "lon": 55.7139},

    # South America
    "Colo-Colo": {"city": "Santiago", "country": "Chile", "code": "CHI", "flag": "🇨🇱", "lat": -33.5064, "lon": -70.6058},
    "Flamengo": {"city": "Rio de Janeiro", "country": "Brazil", "code": "BRA", "flag": "🇧🇷", "lat": -22.9122, "lon": -43.2302},
    "Fluminense": {"city": "Rio de Janeiro", "country": "Brazil", "code": "BRA", "flag": "🇧🇷", "lat": -22.9122, "lon": -43.2302},
    "Vasco da Gama": {"city": "Rio de Janeiro", "country": "Brazil", "code": "BRA", "flag": "🇧🇷", "lat": -22.8906, "lon": -43.2281},
    "Palmeiras": {"city": "São Paulo", "country": "Brazil", "code": "BRA", "flag": "🇧🇷", "lat": -23.5275, "lon": -46.6783},
    "São Paulo": {"city": "São Paulo", "country": "Brazil", "code": "BRA", "flag": "🇧🇷", "lat": -23.6000, "lon": -46.7200},
    "Santos": {"city": "Santos", "country": "Brazil", "code": "BRA", "flag": "🇧🇷", "lat": -23.9511, "lon": -46.3389},
    "Grêmio": {"city": "Porto Alegre", "country": "Brazil", "code": "BRA", "flag": "🇧🇷", "lat": -29.9742, "lon": -51.1947},
    "Internacional": {"city": "Porto Alegre", "country": "Brazil", "code": "BRA", "flag": "🇧🇷", "lat": -30.0656, "lon": -51.2361},
    "Athletico-PR": {"city": "Curitiba", "country": "Brazil", "code": "BRA", "flag": "🇧🇷", "lat": -25.4483, "lon": -49.2769},
    "Boca Juniors": {"city": "Buenos Aires", "country": "Argentina", "code": "ARG", "flag": "🇦🇷", "lat": -34.6356, "lon": -58.3647},
    "River Plate": {"city": "Buenos Aires", "country": "Argentina", "code": "ARG", "flag": "🇦🇷", "lat": -34.5453, "lon": -58.4497},
    "Racing": {"city": "Avellaneda", "country": "Argentina", "code": "ARG", "flag": "🇦🇷", "lat": -34.6672, "lon": -58.3686},
    "Peñarol": {"city": "Montevideo", "country": "Uruguay", "code": "URU", "flag": "🇺🇾", "lat": -34.8258, "lon": -56.0717},
    "Nacional": {"city": "Montevideo", "country": "Uruguay", "code": "URU", "flag": "🇺🇾", "lat": -34.8856, "lon": -56.1558},

    # Rest of Europe & World
    "Red Bull Salzburg": {"city": "Salzburg", "country": "Austria", "code": "AUT", "flag": "🇦🇹", "lat": 47.8156, "lon": 12.9981},
    "Basel": {"city": "Basel", "country": "Switzerland", "code": "SUI", "flag": "🇨🇭", "lat": 47.5414, "lon": 7.6200},
    "Shakhtar Donetsk": {"city": "Donetsk", "country": "Ukraine", "code": "UKR", "flag": "🇺🇦", "lat": 48.0211, "lon": 37.8042},
    "Shakhtar": {"city": "Donetsk", "country": "Ukraine", "code": "UKR", "flag": "🇺🇦", "lat": 48.0211, "lon": 37.8042},
    "Dynamo Kyiv": {"city": "Kyiv", "country": "Ukraine", "code": "UKR", "flag": "🇺🇦", "lat": 50.4501, "lon": 30.5234},
    "Dinamo Zagreb": {"city": "Zagreb", "country": "Croatia", "code": "CRO", "flag": "🇭🇷", "lat": 45.8189, "lon": 16.0181},
    "Sparta Prague": {"city": "Prague", "country": "Czech Republic", "code": "CZE", "flag": "🇨🇿", "lat": 50.1000, "lon": 14.4158},
    "Tokyo": {"city": "Tokyo", "country": "Japan", "code": "JPN", "flag": "🇯🇵", "lat": 35.6636, "lon": 139.5272},
    "Vissel Kobe": {"city": "Kobe", "country": "Japan", "code": "JPN", "flag": "🇯🇵", "lat": 34.6567, "lon": 135.1692},
    "Urawa Reds": {"city": "Saitama", "country": "Japan", "code": "JPN", "flag": "🇯🇵", "lat": 35.9031, "lon": 139.7172},
}

_LOCATIONS_CACHE = None

def _load_locations():
    global _LOCATIONS_CACHE
    if _LOCATIONS_CACHE is not None:
        return _LOCATIONS_CACHE
    data = dict(DEFAULT_CLUB_MAPPINGS)
    if os.path.exists(LOCATIONS_FILE):
        try:
            with open(LOCATIONS_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                data.update(saved)
        except Exception:
            pass
    _LOCATIONS_CACHE = data
    return _LOCATIONS_CACHE

def get_club_location(club_name: str) -> dict:
    """
    Returns geographical metadata for any club name.
    """
    locations = _load_locations()
    cleaned = str(club_name or "").strip()
    
    if cleaned in locations:
        return locations[cleaned]
    
    # Fuzzy keyword matching
    cleaned_lower = cleaned.lower()
    for name, loc in locations.items():
        if name.lower() == cleaned_lower or (len(name) > 4 and name.lower() in cleaned_lower):
            return loc

    # Sensible fallback based on country or city name in string
    if any(k in cleaned_lower for k in ["london", "city", "united", "town", "albion"]):
        return {"city": cleaned, "country": "United Kingdom", "code": "ENG", "flag": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "lat": 52.4862, "lon": -1.8904}
    if any(k in cleaned_lower for k in ["real", "atletico", "deportivo", "valencia", "espanyol"]):
        return {"city": cleaned, "country": "Spain", "code": "ESP", "flag": "🇪🇸", "lat": 40.4168, "lon": -3.7038}
    if any(k in cleaned_lower for k in ["milan", "inter", "juve", "roma", "napoli", "calcio"]):
        return {"city": cleaned, "country": "Italy", "code": "ITA", "flag": "🇮🇹", "lat": 43.7696, "lon": 11.2558}
    if any(k in cleaned_lower for k in ["borussia", "bayern", "bayer", "sv", "vfb"]):
        return {"city": cleaned, "country": "Germany", "code": "GER", "flag": "🇩🇪", "lat": 51.1657, "lon": 10.4515}
    if any(k in cleaned_lower for k in ["saint", "olympique", "stade", "as"]):
        return {"city": cleaned, "country": "France", "code": "FRA", "flag": "🇫🇷", "lat": 46.2276, "lon": 2.2137}

    # Default to Central Europe
    return {"city": cleaned, "country": "Europe", "code": "EUR", "flag": "🌍", "lat": 48.8566, "lon": 2.3522}

def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates great-circle distance between two points in km."""
    R = 6371.0 # Earth radius in km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2.0)**2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c

def latlon_to_vec3(lat_deg: float, lon_deg: float) -> np.ndarray:
    """Converts lat/lon to 3D unit vector on sphere."""
    phi = math.radians(lat_deg)
    lam = math.radians(lon_deg)
    return np.array([math.cos(phi) * math.cos(lam), math.cos(phi) * math.sin(lam), math.sin(phi)], dtype=np.float32)

def vec3_to_latlon(v: np.ndarray):
    """Converts 3D unit vector to (lat_deg, lon_deg)."""
    v_norm = v / (np.linalg.norm(v) + 1e-9)
    lat_rad = math.asin(np.clip(v_norm[2], -1.0, 1.0))
    lon_rad = math.atan2(v_norm[1], v_norm[0])
    return math.degrees(lat_rad), math.degrees(lon_rad)

def slerp(p1: np.ndarray, p2: np.ndarray, t: float) -> np.ndarray:
    """Spherical linear interpolation between two 3D vectors."""
    dot = float(np.clip(np.dot(p1, p2), -1.0, 1.0))
    theta = math.acos(dot)
    if theta < 1e-6:
        return p1
    sin_t = math.sin(theta)
    return (math.sin((1.0 - t) * theta) / sin_t) * p1 + (math.sin(t * theta) / sin_t) * p2

def project_point_to_screen(lat_deg: float, lon_deg: float,
                            cam_lat_deg: float, cam_lon_deg: float,
                            cx: int, cy: int, radius: float,
                            altitude: float = 1.0):
    """
    Orthographic spherical forward projection of (lat, lon) to screen (x, y).
    altitude=1.0 is on the sphere surface. altitude > 1.0 is in the air.
    Returns (screen_x, screen_y, is_visible_front).
    """
    lat = math.radians(lat_deg)
    lon = math.radians(lon_deg)
    cam_lat = math.radians(cam_lat_deg)
    cam_lon = math.radians(cam_lon_deg)

    # Standard forward orthographic equations
    cos_c = math.sin(cam_lat) * math.sin(lat) + math.cos(cam_lat) * math.cos(lat) * math.cos(lon - cam_lon)
    x_proj = math.cos(lat) * math.sin(lon - cam_lon)
    y_proj = math.cos(cam_lat) * math.sin(lat) - math.sin(cam_lat) * math.cos(lat) * math.cos(lon - cam_lon)

    screen_x = int(cx + radius * altitude * x_proj)
    screen_y = int(cy - radius * altitude * y_proj)
    is_visible = cos_c > -0.05 # allow slightly past horizon for atmosphere
    return screen_x, screen_y, is_visible
