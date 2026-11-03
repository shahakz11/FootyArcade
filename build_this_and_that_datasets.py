#!/usr/bin/env python3
"""
build_this_and_that_datasets.py — Dataset Generator for "This & That"
======================================================================
Generates 180 daily challenges for the 'This & That' game mode in Playmaker.
Each daily challenge features two simultaneous criteria (Statement A + Statement B)
and the player must name ALL footballers belonging to the intersection A ∩ B.

Criteria Archetypes:
  1. Club ∩ Club       (~40%): e.g. "Played for Real Madrid AND Bayern Munich"
  2. Club ∩ Nation     (~30%): e.g. "Played for Arsenal AND represented Germany"
  3. Club ∩ League     (~15%): e.g. "Played for Barcelona AND played in the Premier League"
  4. Trophy ∩ Club/League (~15%): e.g. "Won the Champions League AND played in MLS"

Constraints:
  - Answer pool: 4–9 players (the "Goldilocks" range)
  - All answers must appear in all_players.json (autocomplete whitelist)
  - Minimum MarketValue: €5M to avoid obscure benchwarmers
  - At least 1 player with MarketValue ≥ €30M per puzzle (star anchor)
  - No repeated puzzle scenarios across 180 days

Outputs: daily_this_and_that_games.csv
"""

import os
import sys
import json
import csv
import re
import random
import pickle
import unicodedata
from collections import defaultdict
from itertools import combinations

import pandas as pd
from scripts.alias_utils import load_aliases_config, get_player_alias_map

KNOWN_MANUAL_ALIASES = {
    "Rafa Márquez": "Rafael Márquez",
    "Daniel Carvajal": "Dani Carvajal",
    "Luís Figo": "Luis Figo",
    "Alexis Sanchez": "Alexis Sánchez",
    "Cesc Fabregas": "Cesc Fàbregas",
    "Neymar Jr": "Neymar",
    "Kaka": "Kaká",
}

# ─────────────────────────────────────────────────────────────
# Config & Constants
# ─────────────────────────────────────────────────────────────
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_CSV = os.path.join(ROOT_DIR, "daily_this_and_that_games.csv")
CYCLE_LENGTH = 180
MIN_ANSWERS = 4
MAX_ANSWERS = 9
MIN_MV = 5_000_000        # Minimum market value to count as a valid answer
STAR_MV = 30_000_000      # At least 1 player must exceed this in every puzzle
RANDOM_SEED = 42

# Davidcariboo dataset path
DC_DIR = os.path.expanduser("~/.cache/kagglehub/datasets/davidcariboo/player-scores/versions")

# ─────────────────────────────────────────────────────────────
# Canonical Club Names (must match club_to_entities keys in .player_career_db.pkl)
# ─────────────────────────────────────────────────────────────
# Elite clubs we reference across all archetypes
ELITE_CLUBS = [
    "Real Madrid", "Barcelona", "Atlético Madrid", "Sevilla", "Valencia", "Villarreal", "Athletic Bilbao",
    "Manchester United", "Manchester City", "Liverpool", "Chelsea", "Arsenal", "Tottenham Hotspur",
    "Newcastle United", "Everton", "Aston Villa", "Leeds United", "Leicester City", "West Ham United",
    "Bayern Munich", "Borussia Dortmund", "Bayer Leverkusen", "RB Leipzig", "Schalke 04",
    "Eintracht Frankfurt", "VfB Stuttgart", "Werder Bremen", "Hamburger SV",
    "Juventus", "Inter", "AC Milan", "AS Roma", "Napoli", "SS Lazio", "Atalanta", "Fiorentina", "Sampdoria",
    "Paris Saint-Germain", "Olympique de Marseille", "Olympique Lyonnais", "Monaco", "Lille",
    "Benfica", "Porto", "Sporting CP",
    "Ajax", "PSV Eindhoven", "Feyenoord",
    "Galatasaray", "Fenerbahçe", "Beşiktaş",
    "Celtic", "Rangers",
    "Zenit St. Petersburg", "CSKA Moscow",
]

# Statement A template -> Statement B template mapping and display labels
# (club_club archetype uses two clubs)
CLUB_STATEMENTS_EN = {
    "played_for": lambda club: f"Played for {club}",
}

NATION_STATEMENTS_EN = {
    "represented": lambda nat: f"Represented {nat} internationally",
}

# Spanish translations
CLUB_STATEMENTS_ES = {
    "played_for": lambda club: f"Jugó en el {club}",
}

NATION_STATEMENTS_ES = {
    "represented": lambda nat: f"Representó a {nat} a nivel internacional",
}

# Nationality display-name overrides for Spanish
NAT_ES = {
    "Argentina":    "Argentina",
    "Brazil":       "Brasil",
    "France":       "Francia",
    "Germany":      "Alemania",
    "Spain":        "España",
    "Italy":        "Italia",
    "England":      "Inglaterra",
    "Netherlands":  "Países Bajos",
    "Portugal":     "Portugal",
    "Uruguay":      "Uruguay",
    "Belgium":      "Bélgica",
    "Croatia":      "Croacia",
    "Colombia":     "Colombia",
    "Chile":        "Chile",
    "Mexico":       "México",
    "United States": "Estados Unidos",
    "Denmark":      "Dinamarca",
    "Sweden":       "Suecia",
    "Norway":       "Noruega",
    "Senegal":      "Senegal",
    "Ghana":        "Ghana",
    "Ivory Coast":  "Costa de Marfil",
    "Morocco":      "Marruecos",
    "Nigeria":      "Nigeria",
    "Cameroon":     "Camerún",
    "Japan":        "Japón",
    "South Korea":  "Corea del Sur",
    "Switzerland":  "Suiza",
    "Greece":       "Grecia",
    "Czech Republic": "República Checa",
    "Serbia":       "Serbia",
    "Poland":       "Polonia",
    "Romania":      "Rumanía",
    "Turkey":       "Turquía",
    "Russia":       "Rusia",
    "Ukraine":      "Ucrania",
    "Austria":      "Austria",
    "Slovakia":     "Eslovaquia",
    "Hungary":      "Hungría",
    "Paraguay":     "Paraguay",
    "Ecuador":      "Ecuador",
    "Bolivia":      "Bolivia",
    "Venezuela":    "Venezuela",
    "Peru":         "Perú",
    "Costa Rica":   "Costa Rica",
    "Honduras":     "Honduras",
    "Jamaica":      "Jamaica",
    "Scotland":     "Escocia",
    "Wales":        "Gales",
    "Republic of Ireland": "República de Irlanda",
    "Finland":      "Finlandia",
    "Iceland":      "Islandia",
    "Algeria":      "Argelia",
    "Tunisia":      "Túnez",
    "Egypt":        "Egipto",
    "Cameroon":     "Camerún",
    "Zimbabwe":     "Zimbabue",
    "Togo":         "Togo",
    "Bosnia & Herzegovina": "Bosnia y Herzegovina",
    "Slovakia":     "Eslovaquia",
}

# League archetypes: comp_id -> display name + canonical club names in that league
LEAGUES = {
    "Premier League": {
        "comp_ids": ["GB1"],
        "en": "Played in the Premier League",
        "es": "Jugó en la Premier League",
        # Key clubs used in club ∩ league puzzles:
        "clubs": [
            "Manchester United", "Manchester City", "Liverpool", "Chelsea", "Arsenal",
            "Tottenham Hotspur", "Newcastle United", "Everton", "Aston Villa",
            "Leicester City", "Leeds United", "West Ham United",
        ],
    },
    "La Liga": {
        "comp_ids": ["ES1"],
        "en": "Played in La Liga",
        "es": "Jugó en La Liga",
        "clubs": [
            "Real Madrid", "Barcelona", "Atlético Madrid", "Sevilla", "Valencia",
            "Villarreal", "Athletic Bilbao", "Real Betis", "Real Sociedad",
        ],
    },
    "Bundesliga": {
        "comp_ids": ["L1"],
        "en": "Played in the Bundesliga",
        "es": "Jugó en la Bundesliga",
        "clubs": [
            "Bayern Munich", "Borussia Dortmund", "Bayer Leverkusen", "RB Leipzig",
            "Schalke 04", "Eintracht Frankfurt", "VfB Stuttgart", "Werder Bremen", "Hamburger SV",
        ],
    },
    "Serie A": {
        "comp_ids": ["IT1"],
        "en": "Played in Serie A",
        "es": "Jugó en la Serie A",
        "clubs": [
            "Juventus", "Inter", "AC Milan", "AS Roma", "Napoli",
            "SS Lazio", "Atalanta", "Fiorentina", "Sampdoria",
        ],
    },
    "Ligue 1": {
        "comp_ids": ["FR1"],
        "en": "Played in Ligue 1",
        "es": "Jugó en la Ligue 1",
        "clubs": [
            "Paris Saint-Germain", "Olympique de Marseille", "Olympique Lyonnais", "Monaco", "Lille",
        ],
    },
    "MLS": {
        "comp_ids": ["MLS1"],
        "en": "Played in Major League Soccer (MLS)",
        "es": "Jugó en la Major League Soccer (MLS)",
        "clubs": [],
    },
    "Saudi Pro League": {
        "comp_ids": ["SA1"],
        "en": "Played in the Saudi Pro League",
        "es": "Jugó en la Liga Pro Saudí",
        "clubs": [],
    },
}

DISALLOWED_PLAYER_CLUBS = {
    ("Marcus Rashford", "Barcelona"),
    ("Marcus Rashford", "Aston Villa"),
    ("Paul Pogba", "Monaco"),
    ("Erling Haaland", "Barcelona"),
    ("Erling Haaland", "Real Madrid"),
    ("Kylian Mbappé", "Arsenal"),
    ("Lionel Messi", "Manchester City"),
    ("Cristiano Ronaldo", "Manchester City"),
    ("Neymar", "Real Madrid"),
    ("Harry Kane", "Manchester City"),
    ("Bruno Fernandes", "Barcelona"),
    ("Pedri", "Paris Saint-Germain"),
    ("Luis García", "Inter"),
    ("Emiliano Martínez", "Inter"),
    ("Juan Cruz", "Inter"),
}

# Trophy / Accolade criteria (strictly audited sets of verified winners)
# Each is a dict: en/es strings + a set of canonical player names
TROPHIES = [
    {
        "id": "ucl_winner",
        "en": "Won the UEFA Champions League",
        "es": "Ganó la UEFA Champions League",
        "players": {
            # Real Madrid era
            "Cristiano Ronaldo", "Karim Benzema", "Luka Modrić", "Toni Kroos", "Gareth Bale",
            "Sergio Ramos", "Marcelo", "Casemiro", "Dani Carvajal", "Isco", "Keylor Navas",
            "Raphaël Varane", "Lucas Vázquez", "Nacho Fernández", "Marco Asensio", "Vinicius Junior",
            "Rodrygo", "Thibaut Courtois", "Éder Militão", "David Alaba", "Federico Valverde",
            "Iker Casillas", "Raúl", "Fernando Hierro", "Roberto Carlos", "Fernando Morientes",
            "Steve McManaman", "Zinedine Zidane", "Luis Figo", "Claude Makélélé", "Clarence Seedorf",
            "Christian Panucci", "Guti", "Alvaro Arbeloa", "Álvaro Morata",
            # Barcelona era
            "Lionel Messi", "Andrés Iniesta", "Xavi", "Carles Puyol", "Gerard Piqué",
            "Sergio Busquets", "Dani Alves", "Javier Mascherano", "Jordi Alba", "Neymar",
            "Luis Suárez", "Ivan Rakitić", "Marc-André ter Stegen", "Pedro", "David Villa",
            "Thierry Henry", "Samuel Eto'o", "Ronaldinho", "Deco", "Ludovic Giuly",
            "Juliano Belletti", "Rafael Márquez", "Giovanni van Bronckhorst", "Mark van Bommel",
            "Víctor Valdés", "Éric Abidal", "Seydou Keita", "Bojan Krkić", "Yaya Touré",
            # Bayern Munich era
            "Manuel Neuer", "Thomas Müller", "Robert Lewandowski", "Joshua Kimmich", "Kingsley Coman",
            "Alphonso Davies", "Jérôme Boateng", "Thiago Alcántara", "Leon Goretzka",
            "Serge Gnabry", "Philipp Lahm", "Bastian Schweinsteiger", "Franck Ribéry", "Arjen Robben",
            "Mario Mandžukić", "Javi Martínez", "Dante", "Claudio Pizarro",
            "Oliver Kahn", "Stefan Effenberg", "Giovane Élber", "Hasan Salihamidžić", "Samuel Kuffour",
            # Chelsea era
            "Didier Drogba", "Frank Lampard", "John Terry", "Petr Čech", "Petr Cech",
            "Ashley Cole", "Gary Cahill", "David Luiz", "Ramires", "John Obi Mikel",
            "Salomon Kalou", "Fernando Torres", "Juan Mata", "N'Golo Kanté", "Mason Mount",
            "Kai Havertz", "Jorginho", "Antonio Rüdiger", "César Azpilicueta", "Thiago Silva",
            "Reece James", "Ben Chilwell", "Hakim Ziyech", "Christian Pulisic", "Édouard Mendy",
            # Liverpool era
            "Mohamed Salah", "Sadio Mané", "Roberto Firmino", "Virgil van Dijk", "Alisson",
            "Jordan Henderson", "James Milner", "Georginio Wijnaldum", "Fabinho",
            "Trent Alexander-Arnold", "Andrew Robertson", "Divock Origi", "Xherdan Shaqiri",
            "Steven Gerrard", "Xabi Alonso", "Jamie Carragher", "Sami Hyypiä", "Jerzy Dudek",
            "Milan Baroš", "Luis García", "Dietmar Hamann", "Harry Kewell", "John Arne Riise",
            "Djibril Cissé", "Vladimir Šmicer",
            # Man City era
            "Erling Haaland", "Kevin De Bruyne", "İlkay Gündoğan", "Bernardo Silva", "Rodri",
            "Jack Grealish", "Phil Foden", "John Stones", "Rúben Dias", "Kyle Walker",
            "Manuel Akanji", "Ederson", "Riyad Mahrez", "Julián Álvarez", "Nathan Aké",
            # Inter 2010
            "Javier Zanetti", "Diego Milito", "Wesley Sneijder", "Esteban Cambiasso",
            "Walter Samuel", "Lúcio", "Maicon", "Júlio César", "Goran Pandev", "Cristian Chivu",
            "Dejan Stanković", "Marco Materazzi",
            # AC Milan era
            "Paolo Maldini", "Alessandro Nesta", "Andrea Pirlo", "Gennaro Gattuso", "Kaká",
            "Filippo Inzaghi", "Andriy Shevchenko", "Massimo Ambrosini", "Dida", "Cafu",
            "Alessandro Costacurta", "Rivaldo", "Jaap Stam",
            # Man Utd era
            "Wayne Rooney", "Carlos Tevez", "Ryan Giggs", "Paul Scholes",
            "Rio Ferdinand", "Nemanja Vidić", "Patrice Evra", "Edwin van der Sar", "Michael Carrick",
            "Wes Brown", "John O'Shea", "Darren Fletcher", "Park Ji-sung", "Nani",
            "Peter Schmeichel", "Roy Keane", "David Beckham", "Andy Cole", "Dwight Yorke",
            "Teddy Sheringham", "Ole Gunnar Solskjaer", "Nicky Butt", "Denis Irwin",
            "Gary Neville", "Phil Neville",
        },
    },
    {
        "id": "world_cup_winner",
        "en": "Won the FIFA World Cup",
        "es": "Ganó la Copa del Mundo",
        "players": {
            # 2022: Argentina
            "Lionel Messi", "Ángel Di María", "Julián Álvarez", "Alexis Mac Allister",
            "Rodrigo De Paul", "Enzo Fernández", "Cristian Romero", "Nicolás Otamendi",
            "Nahuel Molina", "Nicolás Tagliafico", "Emiliano Martínez", "Lautaro Martínez",
            "Leandro Paredes", "Lisandro Martínez", "Gonzalo Montiel", "Marcos Acuña",
            "Paulo Dybala", "Papu Gómez", "Germán Pezzella", "Exequiel Palacios", "Ángel Correa",
            # 2018: France
            "Kylian Mbappé", "Antoine Griezmann", "Olivier Giroud", "Paul Pogba",
            "N'Golo Kanté", "Blaise Matuidi", "Raphaël Varane", "Samuel Umtiti",
            "Lucas Hernández", "Benjamin Pavard", "Hugo Lloris", "Nabil Fekir",
            "Ousmane Dembélé", "Corentin Tolisso", "Steven Nzonzi", "Presnel Kimpembe",
            "Steve Mandanda", "Alphonse Areola", "Djibril Sidibé", "Adil Rami", "Benjamin Mendy",
            # 2014: Germany
            "Manuel Neuer", "Philipp Lahm", "Jérôme Boateng", "Mats Hummels",
            "Benedikt Höwedes", "Bastian Schweinsteiger", "Sami Khedira", "Toni Kroos",
            "Mesut Özil", "Thomas Müller", "Miroslav Klose", "Mario Götze",
            "André Schürrle", "Per Mertesacker", "Lukas Podolski", "Julian Draxler",
            "Matthias Ginter", "Shkodran Mustafi", "Roman Weidenfeller",
            # 2010: Spain
            "Iker Casillas", "Sergio Ramos", "Gerard Piqué", "Carles Puyol", "Joan Capdevila",
            "Sergio Busquets", "Xabi Alonso", "Xavi", "Andrés Iniesta", "Pedro",
            "David Villa", "Fernando Torres", "Cesc Fàbregas", "Jesús Navas", "Carlos Marchena",
            "Juan Mata", "Fernando Llorente", "Javi Martínez", "Álvaro Arbeloa", "Pepe Reina",
            "Víctor Valdés", "Raúl Albiol", "David Silva",
            # 2006: Italy
            "Gianluigi Buffon", "Gianluca Zambrotta", "Fabio Cannavaro", "Marco Materazzi",
            "Fabio Grosso", "Gennaro Gattuso", "Andrea Pirlo", "Mauro Camoranesi",
            "Simone Perrotta", "Francesco Totti", "Luca Toni", "Alessandro Del Piero",
            "Daniele De Rossi", "Vincenzo Iaquinta", "Alberto Gilardino", "Filippo Inzaghi",
            "Alessandro Nesta", "Andrea Barzagli", "Massimo Oddo",
            # 2002: Brazil
            "Marcos", "Cafu", "Lúcio", "Roque Júnior", "Edmílson", "Roberto Carlos",
            "Gilberto Silva", "Kléberson", "Ronaldinho", "Rivaldo", "Ronaldo",
            "Denílson", "Juninho Paulista", "Vampeta", "Luizão", "Kaká", "Juliano Belletti", "Dida",
            # 1998: France
            "Fabien Barthez", "Lilian Thuram", "Laurent Blanc", "Marcel Desailly", "Bixente Lizarazu",
            "Didier Deschamps", "Emmanuel Petit", "Christian Karembeu", "Zinedine Zidane",
            "Youri Djorkaeff", "Stéphane Guivarc'h", "Christophe Dugarry", "Thierry Henry",
            "David Trezeguet", "Patrick Vieira", "Robert Pires", "Frank Leboeuf",
            # 1994: Brazil
            "Romário", "Bebeto", "Mauro Silva", "Dunga", "Branco", "Aldair", "Márcio Santos",
            "Jorginho", "Taffarel", "Zinho", "Mazinho", "Raí", "Cafu", "Ronaldo",
            # 1990: Germany
            "Lothar Matthäus", "Jürgen Klinsmann", "Rudi Völler", "Andreas Brehme", "Thomas Hässler",
            "Guido Buchwald", "Jürgen Kohler", "Klaus Augenthaler", "Thomas Berthold", "Bodo Illgner",
        },
    },
    {
        "id": "mls_career",
        "en": "Played in Major League Soccer (MLS)",
        "es": "Jugó en la Major League Soccer (MLS)",
        "players": {
            "David Beckham", "Thierry Henry", "Steven Gerrard", "Frank Lampard",
            "Wayne Rooney", "Didier Drogba", "Andrea Pirlo", "Kaká", "David Villa",
            "Zlatan Ibrahimović", "Sebastian Giovinco", "Bastian Schweinsteiger",
            "Gareth Bale", "Gonzalo Higuaín", "Giorgio Chiellini", "Lorenzo Insigne",
            "Federico Bernardeschi", "Christian Benteke", "Xherdan Shaqiri", "Riqui Puig",
            "Carlos Vela", "Javier Hernández", "Denis Bouanga", "Hugo Lloris", "Olivier Giroud",
            "Luis Suárez", "Lionel Messi", "Sergio Busquets", "Jordi Alba", "Blaise Matuidi",
            "Robbie Keane", "Tim Howard", "Clint Dempsey", "Landon Donovan", "Nani",
            "Josef Martínez", "Carlos Valderrama", "Freddie Ljungberg", "Cuauhtémoc Blanco",
            "Giovani dos Santos", "Jonathan dos Santos", "Jermaine Jones",
        },
    },
    {
        "id": "ballon_dor",
        "en": "Won the Ballon d'Or",
        "es": "Ganó el Balón de Oro",
        "players": {
            "Lionel Messi", "Cristiano Ronaldo", "Karim Benzema", "Luka Modrić",
            "Kaká", "Fabio Cannavaro", "Ronaldinho", "Andriy Shevchenko", "Pavel Nedvěd",
            "Ronaldo", "Michael Owen", "Rivaldo", "Zinedine Zidane", "Matthias Sammer",
            "George Weah", "Hristo Stoichkov", "Roberto Baggio", "Marco van Basten",
            "Jean-Pierre Papin", "Lothar Matthäus", "Ruud Gullit", "Michel Platini",
            "Karl-Heinz Rummenigge", "Kevin Keegan", "Franz Beckenbauer", "Johan Cruyff",
            "Gerd Müller", "Bobby Charlton", "Eusébio", "George Best", "Luis Suárez",
            "Alfredo Di Stéfano",
        },
    },
    {
        "id": "saudi_career",
        "en": "Played in the Saudi Pro League",
        "es": "Jugó en la Liga Pro Saudí",
        "players": {
            "Cristiano Ronaldo", "Karim Benzema", "Neymar", "Sadio Mané",
            "Roberto Firmino", "Rúben Neves", "N'Golo Kanté", "Kalidou Koulibaly",
            "Allan Saint-Maximin", "Gabri Veiga", "Jordan Henderson",
            "Marcelo Brozović", "Ivan Rakitić", "Aleksandar Mitrović",
            "Moussa Diaby", "Aymeric Laporte", "Yassine Bounou", "Riyad Mahrez",
            "Franck Kessié", "Fabinho", "Alex Telles", "Otávio", "Luiz Gustavo",
            "Ever Banega", "David Ospina",
        },
    },
]

# Target top nations for Club ∩ Nation puzzles
TOP_NATIONS = [
    "Argentina", "Brazil", "France", "Germany", "Spain", "Italy", "England",
    "Netherlands", "Portugal", "Uruguay", "Belgium", "Croatia", "Colombia",
    "Chile", "Mexico", "United States", "Denmark", "Sweden", "Norway",
    "Senegal", "Ghana", "Ivory Coast", "Morocco", "Nigeria", "Cameroon",
    "Japan", "South Korea", "Switzerland", "Greece", "Czech Republic",
    "Serbia", "Poland", "Turkey", "Russia", "Scotland", "Wales",
    "Republic of Ireland", "Algeria", "Iceland",
]


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def normalize_name(s):
    if not isinstance(s, str):
        return ""
    s = re.sub(r'[\u200b-\u200f\u202a-\u202e\ufeff]', '', s)
    s = s.replace('ð', 'd').replace('Ð', 'D').replace('þ', 'th')
    return ''.join(c for c in unicodedata.normalize('NFD', s)
                   if unicodedata.category(c) != 'Mn').strip()


def _best_dc_path():
    if os.path.exists(DC_DIR):
        versions = sorted([v for v in os.listdir(DC_DIR) if v.isdigit()], key=int)
        return os.path.join(DC_DIR, versions[-1]) if versions else os.path.join(DC_DIR, "679")
    return os.path.join(DC_DIR, "679")


def load_career_db():
    cache = os.path.join(ROOT_DIR, ".player_career_db.pkl")
    if os.path.exists(cache):
        import pickle
        with open(cache, "rb") as f:
            return pickle.load(f)
    raise FileNotFoundError(".player_career_db.pkl not found. Run build_player_chain_datasets.py first.")


def load_player_whitelist():
    """Load all_players.json → {name: {MarketValue, Nationality, Position}}."""
    path = os.path.join(ROOT_DIR, "all_players.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    info = {}
    for p in data:
        n = p["Name"]
        if n not in info or p.get("MarketValue", 0) > info[n].get("MarketValue", 0):
            info[n] = p
    return info


def load_historical_legends():
    """Load historical_careers.json → set of canonical player names."""
    path = os.path.join(ROOT_DIR, "historical_careers.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return set(data.keys())


def load_player_appearances_by_league():
    """Build player_id -> set of competition_ids from appearances.csv (Davidcariboo)."""
    dc_path = _best_dc_path()
    app_file = os.path.join(dc_path, "appearances.csv")
    if not os.path.exists(app_file):
        print("  WARNING: appearances.csv not found — league archetype disabled.")
        return {}
    print("  Loading appearances.csv for league membership...")
    df = pd.read_csv(app_file, usecols=["player_id", "competition_id"], low_memory=False)
    result = defaultdict(set)
    for pid, comp in zip(df["player_id"], df["competition_id"]):
        if pd.notna(pid) and pd.notna(comp):
            result[int(pid)].add(str(comp))
    return result


def load_dc_player_name_map():
    """Build DC player_id -> canonical name from players.csv."""
    dc_path = _best_dc_path()
    pf = os.path.join(dc_path, "players.csv")
    if not os.path.exists(pf):
        return {}
    df = pd.read_csv(pf, usecols=["player_id", "name"], low_memory=False)
    return {int(r["player_id"]): re.sub(r'\s*\(\d+\)$', '', str(r["name"])).strip()
            for _, r in df.iterrows() if pd.notna(r["name"])}


# ─────────────────────────────────────────────────────────────
# Core intersection engine
# ─────────────────────────────────────────────────────────────

class ThisAndThatEngine:

    def __init__(self):
        print("Loading player career database...")
        self.p_clubs, self.player_metadata, self.club_to_entities, self.entity_name, self.entity_clubs = load_career_db()
        print(f"  ✓ {len(self.club_to_entities)} clubs | {len(self.entity_name)} entities")

        print("Loading player whitelist (all_players.json)...")
        self.player_info = load_player_whitelist()
        self.whitelist = set(self.player_info.keys())
        print(f"  ✓ {len(self.whitelist)} players whitelisted")

        print("Loading historical legends...")
        self.legends = load_historical_legends()
        print(f"  ✓ {len(self.legends)} legends")

        print("Loading DC player name map...")
        self.dc_name_map = load_dc_player_name_map()

        print("Loading player aliases config...")
        alias_cfg = load_aliases_config()
        self.alias_map = get_player_alias_map(alias_cfg)
        print(f"  ✓ {len(self.alias_map)} player alias mappings loaded")

        print("Loading appearances by league...")
        self.pid_leagues = load_player_appearances_by_league()
        print(f"  ✓ {len(self.pid_leagues)} players with league data")

        # Reverse: entity_id -> dc_player_id (best effort via name match)
        self._build_entity_to_dc_map()

    def _build_entity_to_dc_map(self):
        """Map entity_id -> dc_player_id using name normalization.
        Also builds name_to_dc_pid for O(1) league lookups."""
        dc_norm = {normalize_name(v).lower(): k for k, v in self.dc_name_map.items()}
        self.entity_to_dc = {}
        for eid in self.entity_name:
            n = self.entity_name[eid]
            key = normalize_name(n).lower()
            if key in dc_norm:
                self.entity_to_dc[eid] = dc_norm[key]

        # Pre-build canonical player name → dc_player_id (for league lookups)
        self.name_to_dc_pid = {}
        for name in self.whitelist:
            key = normalize_name(name).lower()
            if key in dc_norm:
                self.name_to_dc_pid[name] = dc_norm[key]
        print(f"  ✓ name_to_dc_pid: {len(self.name_to_dc_pid)} entries")

    def _resolve_entity_name(self, pid):
        n = self.entity_name.get(pid, "")
        if not n:
            n = self.player_metadata.get(pid, {}).get("name", "")
        # Canonicalize aliases
        if n in KNOWN_MANUAL_ALIASES:
            n = KNOWN_MANUAL_ALIASES[n]
        elif n in self.alias_map:
            n = self.alias_map[n]
        return n

    def _is_valid_answer(self, name, mv_threshold=MIN_MV):
        """Returns True if name is in whitelist with sufficient market value or is a legend."""
        if name not in self.whitelist:
            return False
        mv = self.player_info[name].get("MarketValue", 0)
        if mv >= mv_threshold:
            return True
        if name in self.legends:
            return True
        return False

    def get_club_members(self, club_name):
        """Return a {name: MarketValue} dict of valid players who played for club_name."""
        pids = self.club_to_entities.get(club_name, set())
        result = {}
        for pid in pids:
            name = self._resolve_entity_name(pid)
            if (name, club_name) in DISALLOWED_PLAYER_CLUBS:
                continue
            if name and self._is_valid_answer(name):
                mv = self.player_info[name].get("MarketValue", 0)
                if name not in result or mv > result[name]:
                    result[name] = mv
        return result

    def get_nation_members(self, club_name, nationality):
        """Return {name: MV} for players who played for club AND have given nationality."""
        members = self.get_club_members(club_name)
        return {n: mv for n, mv in members.items()
                if self.player_info[n].get("Nationality") == nationality}

    def get_league_members(self, club_name, league_id):
        """Return {name: MV} for players who played for club AND appeared in the given league."""
        comp_ids = set(LEAGUES[league_id]["comp_ids"])
        members = self.get_club_members(club_name)
        result = {}
        for name, mv in members.items():
            dc_pid = self.name_to_dc_pid.get(name)
            if dc_pid and self.pid_leagues.get(dc_pid, set()).intersection(comp_ids):
                result[name] = mv
        return result

    def get_trophy_club_members(self, trophy_id, club_name):
        """Intersect trophy winner set with club membership."""
        trophy = next((t for t in TROPHIES if t["id"] == trophy_id), None)
        if not trophy:
            return {}
        trophy_set = trophy["players"]
        club_members = self.get_club_members(club_name)
        return {n: mv for n, mv in club_members.items() if n in trophy_set}

    def _validate_pool(self, pool, scenario_key=""):
        """Validate pool meets Goldilocks criteria. Returns (is_valid, sorted_names)."""
        if not pool:
            return False, []
        n = len(pool)
        if not (MIN_ANSWERS <= n <= MAX_ANSWERS):
            return False, []
        top_mv = max(pool.values())
        if top_mv < STAR_MV:
            return False, []
        # Sort by market value descending (most famous first for evidence display)
        sorted_names = sorted(pool.keys(), key=lambda x: pool[x], reverse=True)
        return True, sorted_names

    def build_answer_details(self, player_names, statement_a, statement_b):
        """Build answer detail list with nationality + photo URL for each player."""
        details = []
        for name in player_names:
            p = self.player_info.get(name, {})
            details.append({
                "name": name,
                "nationality": p.get("Nationality", ""),
                "position": p.get("Position", ""),
                "market_value": p.get("MarketValue", 0),
            })
        return details

    # ─────────────────────────────────────────────────────────
    # Puzzle candidate generation by archetype
    # ─────────────────────────────────────────────────────────

    def generate_club_club_candidates(self):
        """Archetype 1: Club A ∩ Club B puzzles."""
        candidates = []
        print("  Generating Club ∩ Club candidates...")
        for c1, c2 in combinations(ELITE_CLUBS, 2):
            pool1 = self.get_club_members(c1)
            pool2 = self.get_club_members(c2)
            inter = {n: pool1[n] for n in pool1 if n in pool2}
            valid, sorted_names = self._validate_pool(inter)
            if valid:
                candidates.append({
                    "category": "club_club",
                    "statement_a": f"Played for {c1}",
                    "statement_b": f"Played for {c2}",
                    "statement_a_es": f"Jugó en el {c1}",
                    "statement_b_es": f"Jugó en el {c2}",
                    "total_answers": len(sorted_names),
                    "answer_names": sorted_names,
                    "pool": inter,
                    "score": max(inter.values()),  # used for quality sorting
                })
        print(f"    → {len(candidates)} valid Club ∩ Club candidates")
        return candidates

    def generate_club_nation_candidates(self):
        """Archetype 2: Club A ∩ Nation B puzzles."""
        candidates = []
        print("  Generating Club ∩ Nation candidates...")
        for club in ELITE_CLUBS:
            for nation in TOP_NATIONS:
                pool = self.get_nation_members(club, nation)
                valid, sorted_names = self._validate_pool(pool)
                if valid:
                    nat_es = NAT_ES.get(nation, nation)
                    candidates.append({
                        "category": "club_nation",
                        "statement_a": f"Played for {club}",
                        "statement_b": f"Represented {nation} internationally",
                        "statement_a_es": f"Jugó en el {club}",
                        "statement_b_es": f"Representó a {nat_es} a nivel internacional",
                        "total_answers": len(sorted_names),
                        "answer_names": sorted_names,
                        "pool": pool,
                        "score": max(pool.values()),
                    })
        print(f"    → {len(candidates)} valid Club ∩ Nation candidates")
        return candidates

    def generate_club_league_candidates(self):
        """Archetype 3: Club A ∩ League B puzzles."""
        candidates = []
        print("  Generating Club ∩ League candidates...")
        for league_id, league_info in LEAGUES.items():
            # Only include cross-league (club not from the league itself)
            league_clubs = set(league_info.get("clubs", []))
            for club in ELITE_CLUBS:
                if club in league_clubs:
                    continue  # skip same-league trivial matches
                pool = self.get_league_members(club, league_id)
                valid, sorted_names = self._validate_pool(pool)
                if valid:
                    candidates.append({
                        "category": "club_league",
                        "statement_a": f"Played for {club}",
                        "statement_b": league_info["en"],
                        "statement_a_es": f"Jugó en el {club}",
                        "statement_b_es": league_info["es"],
                        "total_answers": len(sorted_names),
                        "answer_names": sorted_names,
                        "pool": pool,
                        "score": max(pool.values()),
                    })
        print(f"    → {len(candidates)} valid Club ∩ League candidates")
        return candidates

    def generate_trophy_club_candidates(self):
        """Archetype 4: Trophy/Accolade ∩ Club puzzles."""
        candidates = []
        print("  Generating Trophy ∩ Club candidates...")
        for trophy in TROPHIES:
            for club in ELITE_CLUBS:
                pool = self.get_trophy_club_members(trophy["id"], club)
                valid, sorted_names = self._validate_pool(pool)
                if valid:
                    candidates.append({
                        "category": "trophy_club",
                        "statement_a": trophy["en"],
                        "statement_b": f"Played for {club}",
                        "statement_a_es": trophy["es"],
                        "statement_b_es": f"Jugó en el {club}",
                        "total_answers": len(sorted_names),
                        "answer_names": sorted_names,
                        "pool": pool,
                        "score": max(pool.values()),
                    })
        print(f"    → {len(candidates)} valid Trophy ∩ Club candidates")
        return candidates

    def generate_all_candidates(self):
        """Generate all candidate puzzles across all archetypes."""
        print("\n=== Generating all This & That candidate puzzles ===\n")
        all_candidates = []
        all_candidates.extend(self.generate_club_club_candidates())
        all_candidates.extend(self.generate_club_nation_candidates())
        all_candidates.extend(self.generate_trophy_club_candidates())
        all_candidates.extend(self.generate_club_league_candidates())
        print(f"\nTotal candidate puzzles: {len(all_candidates)}")
        return all_candidates

    def select_180_puzzles(self, all_candidates):
        """
        Select 180 diverse, high-quality puzzles from the candidate pool.

        Strategy:
        1. Deduplicate by scenario key (same pair of statements = same puzzle)
        2. Sort by "icon score" (max market value in pool)
        3. Apply archetype quotas:
           - club_club:    ~70 puzzles  (39%)
           - club_nation:  ~55 puzzles  (31%)
           - club_league:  ~30 puzzles  (17%)
           - trophy_club:  ~25 puzzles  (14%)
        4. Ensure no club appears more than 12 times total across both statements
        5. Shuffle with fixed seed for reproducible ordering
        """
        random.seed(RANDOM_SEED)

        # Deduplicate
        seen = set()
        deduped = []
        for c in all_candidates:
            key = tuple(sorted([c["statement_a"], c["statement_b"]]))
            if key not in seen:
                seen.add(key)
                deduped.append(c)

        print(f"\nAfter dedup: {len(deduped)} unique candidates")

        # Separate by archetype and sort by score desc
        by_type = defaultdict(list)
        for c in deduped:
            by_type[c["category"]].append(c)

        for k in by_type:
            by_type[k].sort(key=lambda x: x["score"], reverse=True)

        QUOTA = {
            "club_club":   85,
            "club_nation": 65,
            "trophy_club": 23,
            "club_league": 7,
        }

        # Club usage counter (avoid repetition)
        club_usage = defaultdict(int)
        MAX_CLUB_USES = 18

        def extract_clubs(candidate):
            """Extract all club references from statements."""
            clubs = []
            for stmt in [candidate["statement_a"], candidate["statement_b"]]:
                for ec in ELITE_CLUBS:
                    if ec in stmt:
                        clubs.append(ec)
            return clubs

        selected = []
        selected_keys = set()
        for archetype, quota in QUOTA.items():
            pool = by_type.get(archetype, [])
            added = 0
            for candidate in pool:
                if added >= quota:
                    break
                key = tuple(sorted([candidate["statement_a"], candidate["statement_b"]]))
                if key in selected_keys:
                    continue
                clubs_in = extract_clubs(candidate)
                if any(club_usage[c] >= MAX_CLUB_USES for c in clubs_in):
                    continue
                selected.append(candidate)
                selected_keys.add(key)
                for c in clubs_in:
                    club_usage[c] += 1
                added += 1
            print(f"  {archetype}: selected {added}/{quota} requested")

        # If still under CYCLE_LENGTH (180), fill remaining from top unused candidates
        if len(selected) < CYCLE_LENGTH:
            remaining_needed = CYCLE_LENGTH - len(selected)
            print(f"  Filling remaining {remaining_needed} puzzles from top unused candidates...")
            for candidate in deduped:
                if len(selected) >= CYCLE_LENGTH:
                    break
                key = tuple(sorted([candidate["statement_a"], candidate["statement_b"]]))
                if key in selected_keys:
                    continue
                clubs_in = extract_clubs(candidate)
                if any(club_usage[c] >= MAX_CLUB_USES + 5 for c in clubs_in):
                    continue
                selected.append(candidate)
                selected_keys.add(key)
                for c in clubs_in:
                    club_usage[c] += 1

        total = len(selected)
        print(f"\nTotal selected: {total} puzzles")

        # If we have more than 180, trim to exactly 180
        if total > CYCLE_LENGTH:
            selected = selected[:CYCLE_LENGTH]

        # Shuffle for varied daily delivery
        random.shuffle(selected)

        # Assign game_day 1..N
        for i, puzzle in enumerate(selected):
            puzzle["game_day"] = i + 1

        return selected


# ─────────────────────────────────────────────────────────────
# CSV output
# ─────────────────────────────────────────────────────────────

def write_csv(puzzles, output_path):
    """Write puzzles to daily_this_and_that_games.csv."""
    fieldnames = [
        "game_day",
        "category",
        "statement_a",
        "statement_b",
        "statement_a_es",
        "statement_b_es",
        "total_answers",
        "answer_names",
        "answer_details",
    ]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for p in puzzles:
            # Build detail list
            details = []
            for name in p["answer_names"]:
                pi = {}
                if "player_info" in dir(p):
                    pass
                details.append({"name": name})
            writer.writerow({
                "game_day":       p["game_day"],
                "category":       p["category"],
                "statement_a":    p["statement_a"],
                "statement_b":    p["statement_b"],
                "statement_a_es": p["statement_a_es"],
                "statement_b_es": p["statement_b_es"],
                "total_answers":  p["total_answers"],
                "answer_names":   json.dumps(p["answer_names"], ensure_ascii=False),
                "answer_details": json.dumps(details, ensure_ascii=False),
            })
    print(f"\n✅ Written {len(puzzles)} puzzles → {output_path}")


# ─────────────────────────────────────────────────────────────
# Quick Verification
# ─────────────────────────────────────────────────────────────

def verify_output(output_path):
    """Run post-generation sanity checks."""
    print("\n=== Verifying generated CSV ===")
    errors = []
    with open(output_path, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    print(f"  Rows: {len(rows)}")
    game_days = set()
    for r in rows:
        gd = int(r["game_day"])
        if gd in game_days:
            errors.append(f"Duplicate game_day: {gd}")
        game_days.add(gd)

        n = int(r["total_answers"])
        if not (MIN_ANSWERS <= n <= MAX_ANSWERS):
            errors.append(f"game_day {gd}: total_answers={n} out of [{MIN_ANSWERS},{MAX_ANSWERS}]")

        names = json.loads(r["answer_names"])
        if len(names) != n:
            errors.append(f"game_day {gd}: answer_names len mismatch ({len(names)} vs {n})")

        if not r["statement_a"] or not r["statement_b"]:
            errors.append(f"game_day {gd}: missing statement")

    # Category distribution
    from collections import Counter
    cat_counts = Counter(r["category"] for r in rows)
    print(f"  Category distribution: {dict(cat_counts)}")
    print(f"  Answer pool sizes: min={min(int(r['total_answers']) for r in rows)}, "
          f"max={max(int(r['total_answers']) for r in rows)}, "
          f"avg={sum(int(r['total_answers']) for r in rows)/len(rows):.1f}")

    if errors:
        print(f"\n  ❌ {len(errors)} errors found:")
        for e in errors:
            print(f"    - {e}")
        return False
    else:
        print(f"\n  ✅ All {len(rows)} puzzles pass validation")
        return True


# ─────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────

def main():
    print("=" * 65)
    print("  Playmaker — This & That Dataset Generator")
    print("=" * 65)

    engine = ThisAndThatEngine()
    all_candidates = engine.generate_all_candidates()

    if not all_candidates:
        print("ERROR: No candidates generated. Check data sources.")
        sys.exit(1)

    puzzles = engine.select_180_puzzles(all_candidates)

    # Inject player_info into write step so answer_details can be enriched
    for p in puzzles:
        details = []
        for name in p["answer_names"]:
            pi = engine.player_info.get(name, {})
            details.append({
                "name": name,
                "nationality": pi.get("Nationality", ""),
                "position": pi.get("Position", ""),
                "market_value": pi.get("MarketValue", 0),
                "detail_a": p["statement_a"],
                "detail_b": p["statement_b"],
                "detail_a_es": p["statement_a_es"],
                "detail_b_es": p["statement_b_es"],
            })
        p["answer_details_data"] = details

    # Write CSV (override write_csv to use enriched details)
    fieldnames = [
        "game_day", "category",
        "statement_a", "statement_b",
        "statement_a_es", "statement_b_es",
        "total_answers", "answer_names", "answer_details",
    ]
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for p in puzzles:
            writer.writerow({
                "game_day":       p["game_day"],
                "category":       p["category"],
                "statement_a":    p["statement_a"],
                "statement_b":    p["statement_b"],
                "statement_a_es": p["statement_a_es"],
                "statement_b_es": p["statement_b_es"],
                "total_answers":  p["total_answers"],
                "answer_names":   json.dumps(p["answer_names"], ensure_ascii=False),
                "answer_details": json.dumps(p.get("answer_details_data", []), ensure_ascii=False),
            })
    print(f"\n✅ Written {len(puzzles)} puzzles → {OUTPUT_CSV}")

    verify_output(OUTPUT_CSV)

    # Print sample puzzles
    print("\n=== Sample Puzzles (Days 1-5) ===")
    with open(OUTPUT_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i >= 5:
                break
            print(f"\n  Day {row['game_day']} [{row['category']}]")
            print(f"  A: {row['statement_a']}")
            print(f"  B: {row['statement_b']}")
            names = json.loads(row["answer_names"])
            print(f"  Answers ({row['total_answers']}): {names}")


if __name__ == "__main__":
    main()
