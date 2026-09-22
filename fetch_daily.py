"""
fetch_daily.py — Playmaker Game Compiler
==========================================
Reads games.json to discover all registered games and compiles
each game's HTML for today and past N days (back-in-time).

Usage
-----
  python fetch_daily.py                        # today's puzzles (all games)
  python fetch_daily.py --offset -1            # yesterday's puzzles (all games)
  python fetch_daily.py --puzzle 42            # force a specific puzzle number
  python fetch_daily.py --random               # random puzzle number
  python fetch_daily.py --max-back-days 7      # also compile last 7 days (default)
  python fetch_daily.py --game top_transfers   # compile only one game

Adding a new game
-----------------
1. Add an entry to games.json with all required fields.
2. Create a template in templates/<templateFile>.
3. Add the game's CSV data file (for fetch_daily.py to read).
4. Add a loader section in the GAME DATA LOADERS dict below.
5. Run this script — all output files are auto-generated.
"""

import os
import sys
import re
import json
import csv
import argparse
import unicodedata
import random as rand_mod
from datetime import datetime, timedelta
from scripts.alias_utils import (
    load_aliases_config,
    get_club_alias_map,
    filter_and_canonicalize_clubs,
    filter_and_canonicalize_players,
    filter_hidden_players,
    clean_career_transfers
)

# Increase CSV field size limit for large JSON arrays
csv.field_size_limit(sys.maxsize)

# ─────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────
TOTAL_DAYS   = 180   # puzzle cycle length
GAMES_JSON   = "games.json"
TEMPLATES_DIR = "templates"
OUTPUT_DIR   = "games"
ES_OUTPUT_DIR = os.path.join("es", "games")
LEDGER_FILE  = os.path.join("data", "puzzle_schedule_ledger.json")


def localize_for_spanish(html, game_cfg, puzzle_num, is_back_in_time):
    """
    Transforms English compiled HTML into a fully localized Spanish game page:
    - lang="es"
    - Updated hreflang and canonical URLs pointing to /es/games/
    - Assets and scripts mapped to ../../ relative depth
    - Localized game headers, rules, instructions, placeholders, and buttons
    - Localized table headers, player positions, dynamic JS strings, and bottom cards
    - Sets active state on the ES switcher button
    - Injects Spanish game note and FootyI18n language trigger
    """
    game_id = game_cfg["id"]
    es_html = html

    # 1. Update lang attribute and canonical/og URLs
    es_html = re.sub(r'<html\b([^>]*?)\blang="en"([^>]*?)>', r'<html\1lang="es"\2>', es_html)
    es_html = es_html.replace(
        f'<link rel="canonical" href="https://playmaker.best/games/{game_id}.html"',
        f'<link rel="canonical" href="https://playmaker.best/es/games/{game_id}.html"'
    )
    es_html = es_html.replace(
        f'<meta property="og:url" content="https://playmaker.best/games/{game_id}.html"',
        f'<meta property="og:url" content="https://playmaker.best/es/games/{game_id}.html"'
    )

    # 1b. Localize JSON-LD Schema (inLanguage, URLs, Breadcrumbs)
    es_html = es_html.replace('"inLanguage": "en"', '"inLanguage": "es"')
    es_html = es_html.replace(
        f'"url": "https://playmaker.best/games/{game_id}.html"',
        f'"url": "https://playmaker.best/es/games/{game_id}.html"'
    )
    es_html = es_html.replace(
        '"item": "https://playmaker.best/"',
        '"item": "https://playmaker.best/es/"'
    )
    es_html = es_html.replace(
        f'"item": "https://playmaker.best/games/{game_id}.html"',
        f'"item": "https://playmaker.best/es/games/{game_id}.html"'
    )
    es_html = re.sub(r'("name":\s*"Home",\s*"item":\s*"https://playmaker.best/es/")', r'"name": "Inicio",\n              "item": "https://playmaker.best/es/"', es_html)

    # 2. Update relative asset paths for 2-level depth (es/games/)
    es_html = es_html.replace('href="../assets/', 'href="../../assets/')
    es_html = es_html.replace('src="../assets/', 'src="../../assets/')
    es_html = es_html.replace('href="../games/', 'href="../../games/')
    es_html = es_html.replace('src="../games/', 'src="../../games/')
    es_html = es_html.replace('href="../manifest.json"', 'href="../../manifest.json"')
    es_html = es_html.replace('href="../favicon.ico"', 'href="../../favicon.ico"')
    es_html = es_html.replace('href="../index.html"', 'href="../index.html"')

    # 3. Swap active switcher button state
    es_html = es_html.replace(
        'class="px-2 py-0.5 rounded transition-all bg-accent/20 text-accent font-bold shadow-sm" title="Switch to English">EN</a>',
        'class="px-2 py-0.5 rounded transition-all text-on-surface-variant hover:text-white" title="Switch to English">EN</a>'
    ).replace(
        'class="px-2 py-0.5 rounded transition-all text-on-surface-variant hover:text-white" title="Cambiar a Español">ES</a>',
        'class="px-2 py-0.5 rounded transition-all bg-accent/20 text-accent font-bold shadow-sm" title="Cambiar a Español">ES</a>'
    )

    # 4. Global UI, Navigation, Counter, and Button replacements
    global_replacements = [
        # How to Play Modal content (Placed first to avoid single-token collisions like 'Lives:' -> 'Vidas:')
        # Passport FC
        ('<p><strong class="text-on-background font-title">Goal:</strong> Fill today\'s club passport by collecting all 4 nationality stamps for the featured <strong class="text-on-background font-title">Anchor Club</strong>.</p>',
         '<p><strong class="text-on-background font-title">Objetivo:</strong> Completa el pasaporte del club reuniendo los 4 sellos de nacionalidad para el <strong class="text-on-background font-title">Club Ancla</strong> destacado.</p>'),
        ('<p><strong class="text-on-background font-title">1. Progressive Stamps:</strong> Name any qualifying footballer who played for today\'s anchor club and represented the designated nationality. Each destination unlocks once you solve the previous one!</p>',
         '<p><strong class="text-on-background font-title">1. Sellos Progresivos:</strong> Nombra a cualquier futbolista válido que haya jugado en el club ancla representando a la nacionalidad indicada. ¡Cada país se desbloquea al acertar el anterior!</p>'),
        ('<p><strong class="text-on-background font-title">2. Escalating Difficulty:</strong> The passport starts with major footballing nations (large talent pool) and ascends to <em>The Unicorn</em> — a rare nation with only 1 or 2 eligible legends in club history.</p>',
         '<p><strong class="text-on-background font-title">2. Dificultad Creciente:</strong> El pasaporte empieza con grandes potencias futbolísticas y asciende hasta <em>El Unicornio</em> — un país insólito con solo 1 o 2 leyendas en la historia del club.</p>'),
        ('<p><strong class="text-on-background font-title">3. Any Valid Player Works:</strong> If Barcelona &amp; France is active, you can name any French player who wore the Blaugrana shirt (e.g. Henry, Griezmann, Dembélé, Thuram, Umtiti, or Koundé).</p>',
         '<p><strong class="text-on-background font-title">3. Cualquier Jugador Válido Sirve:</strong> Si el reto es Barcelona y Francia, puedes nombrar a cualquier francés que haya vestido la camiseta blaugrana (ej. Henry, Griezmann, Dembélé, Thuram, Umtiti o Koundé).</p>'),
        ('<p><strong class="text-on-background font-title">4. Lives &amp; VAR:</strong> Incorrect guesses deduct 1 life. If you believe your player qualifies, appeal the decision via official VAR review.</p>',
         '<p><strong class="text-on-background font-title">4. Vidas y VAR:</strong> Los fallos restan 1 vida. Si crees que tu jugador es válido, apela la decisión mediante la revisión oficial del VAR.</p>'),
        ('<p><strong class="text-on-background font-title">5. Hints &amp; Skip:</strong> Reveal position clues if you need guidance, or skip ahead to the next destination without losing a life.</p>',
         '<p><strong class="text-on-background font-title">5. Pistas y Saltar:</strong> Revela pistas de posición si necesitas ayuda, o salta al siguiente país sin perder vidas.</p>'),
        ('<p><strong class="text-on-background font-title">6. Database Scope:</strong> Includes official senior club appearances and transfers since 1990 alongside verified historic legends throughout club history (updated to June 2026).</p>',
         '<p><strong class="text-on-background font-title">6. Base de Datos:</strong> Incluye partidos y fichajes oficiales del primer equipo desde 1990 más leyendas históricas verificadas (actualizado a junio de 2026).</p>'),

        # Top Transfers
        ('<p><strong class="text-on-background font-title">Goal:</strong> Uncover the top 10 most expensive transfer signings for today\'s featured club or nationality.</p>',
         '<p><strong class="text-on-background font-title">Objetivo:</strong> Descubre el top 10 de fichajes más caros del club o país destacado de hoy.</p>'),
        ('<p><strong class="text-on-background font-title">1. Search &amp; Guess:</strong> Type and select any footballer from the search bar. If they are among the top 10 record signings, their row is revealed and your score increases!</p>',
         '<p><strong class="text-on-background font-title">1. Buscar y Adivinar:</strong> Escribe y selecciona cualquier futbolista en el buscador. Si está entre los 10 fichajes récord, ¡su fila se revelará y sumará a tu puntuación!</p>'),
        ('<p><strong class="text-on-background font-title">2. Free Clues &amp; Reveals:</strong> Click the lightbulb icon on any row to reveal transfer fee, year, and previous club clues. Click the eye icon to reveal the player if you are stuck.</p>',
         '<p><strong class="text-on-background font-title">2. Pistas y Revelaciones:</strong> Pulsa la bombilla en cualquier fila para ver el coste, año y club de origen. Pulsa el icono del ojo si quieres revelar directamente al jugador.</p>'),
        ('<p><strong class="text-on-background font-title">3. Lives &amp; VAR:</strong> Incorrect guesses deduct 1 life. If you believe your player belongs in the top 10 rankings, submit a VAR appeal for automated review.</p>',
         '<p><strong class="text-on-background font-title">3. Vidas y VAR:</strong> Los fallos restan 1 vida. Si crees que tu jugador pertenece al top 10, envía una apelación al VAR para su revisión automática.</p>'),
        ('<p><strong class="text-on-background font-title">4. Winning:</strong> Discover all 10 record signings before running out of lives to achieve a Mastermind victory!</p>',
         '<p><strong class="text-on-background font-title">4. Victoria:</strong> ¡Descubre los 10 fichajes récord antes de quedarte sin vidas para lograr la victoria!</p>'),
        ('<p><strong class="text-on-background font-title">5. Database Scope:</strong> Covers confirmed senior incoming transfers in the modern era (2012–Present) sourced from official transfer records.</p>',
         '<p><strong class="text-on-background font-title">5. Base de Datos:</strong> Incluye transferencias oficiales confirmadas del primer equipo en la era moderna (2012–Presente).</p>'),

        # Top Scorers
        ('<p><strong class="text-on-background font-title">Goal:</strong> Name the top 10 goalscorers for today\'s featured league and season.</p>',
         '<p><strong class="text-on-background font-title">Objetivo:</strong> Nombra al top 10 de máximos goleadores de la liga y temporada destacada de hoy.</p>'),
        ('<p><strong class="text-on-background font-title">1. Search &amp; Guess:</strong> Type and select players from the search bar. Any correct player in the top 10 rankings instantly populates their leaderboard row!</p>',
         '<p><strong class="text-on-background font-title">1. Buscar y Adivinar:</strong> Escribe y selecciona futbolistas en el buscador. ¡Cualquier acierto en el top 10 completará al instante su fila en la tabla!</p>'),
        ('<p><strong class="text-on-background font-title">2. Free Clues &amp; Reveals:</strong> Click the lightbulb icon on any row to uncover nationality, club, and appearance hints. Click the eye icon to reveal the player if you are stuck.</p>',
         '<p><strong class="text-on-background font-title">2. Pistas y Revelaciones:</strong> Pulsa la bombilla en cualquier fila para desbloquear pistas de país, club y partidos. Pulsa el icono del ojo si quieres revelar directamente al jugador.</p>'),
        ('<p><strong class="text-on-background font-title">3. Lives &amp; VAR:</strong> Incorrect guesses deduct 1 life. If your player scored enough goals to qualify, appeal the decision via official VAR review.</p>',
         '<p><strong class="text-on-background font-title">3. Vidas y VAR:</strong> Los fallos restan 1 vida. Si tu jugador marcó suficientes goles para calificar, apela la decisión mediante el VAR.</p>'),
        ('<p><strong class="text-on-background font-title">4. Winning:</strong> Identify all 10 top goalscorers before running out of lives to clear the board!</p>',
         '<p><strong class="text-on-background font-title">4. Victoria:</strong> ¡Identifica a los 10 máximos goleadores antes de quedarte sin vidas para completar la tabla!</p>'),
        ('<p><strong class="text-on-background font-title">5. Database Scope:</strong> Includes official league goals scored across the designated season or tournament.</p>',
         '<p><strong class="text-on-background font-title">5. Base de Datos:</strong> Incluye goles oficiales anotados en liga durante la temporada o torneo designado.</p>'),

        # Transfer Destination
        ('<p><strong class="text-on-background font-title">Goal:</strong> Retrace the featured footballer\'s career path club-by-club back to where it all began!</p>',
         '<p><strong class="text-on-background font-title">Objetivo:</strong> ¡Recorre la trayectoria del futbolista destacado club a club hasta sus orígenes!</p>'),
        ('<p><strong class="text-on-background font-title">1. Reverse Chronology:</strong> Start at the player\'s most recent club and work backwards. For each step, identify the previous club they transferred from.</p>',
         '<p><strong class="text-on-background font-title">1. Orden Cronológico Inverso:</strong> Empieza en el club más reciente y retrocede en el tiempo. En cada paso, identifica el club de procedencia del traspaso.</p>'),
        ('<p><strong class="text-on-background font-title">2. Timeline Clues:</strong> Each card displays the transfer year and fee. The destination club is visible—your mission is to name the originating club.</p>',
         '<p><strong class="text-on-background font-title">2. Pistas de la Línea Temporal:</strong> Cada tarjeta muestra el año y coste del fichaje. El club de destino es visible: tu misión es acertar el club de origen.</p>'),
        ('<p><strong class="text-on-background font-title">3. Step Reveals:</strong> Stuck on a difficult club? Click the reveal icon to uncover the step and keep moving back in time.</p>',
         '<p><strong class="text-on-background font-title">3. Revelar Pasos:</strong> ¿Atascado en un club difícil? Pulsa el icono de revelar para desbloquear el paso y seguir retrocediendo en su carrera.</p>'),
        ('<p><strong class="text-on-background font-title">4. Lives:</strong> Incorrect club guesses deduct 1 life. The game ends if your lives reach 0.</p>',
         '<p><strong class="text-on-background font-title">4. Vidas:</strong> Los intentos erróneos de club restan 1 vida. La partida termina si las vidas llegan a 0.</p>'),
        ('<p><strong class="text-on-background font-title">5. Winning:</strong> Successfully navigate the player\'s entire career history from start to finish!</p>',
         '<p><strong class="text-on-background font-title">5. Victoria:</strong> ¡Recorre con éxito toda la trayectoria deportiva del jugador de principio a fin!</p>'),
        ('<p><strong class="text-on-background font-title">6. Database Scope:</strong> Includes all official senior transfers, loans, and career moves up to 2026.</p>',
         '<p><strong class="text-on-background font-title">6. Base de Datos:</strong> Incluye todos los traspasos oficiales, cesiones y movimientos del primer equipo hasta 2026.</p>'),

        # Player Chain
        ('<p><strong class="text-on-background font-title">Goal:</strong> Unmask the mystery <strong class="text-on-background font-title">Player of the Day</strong> by identifying footballers across an expanding chain of career clubs.</p>',
         '<p><strong class="text-on-background font-title">Objetivo:</strong> Descubre al misterioso <strong class="text-on-background font-title">Jugador del Día</strong> identificando futbolistas a lo largo de una cadena creciente de clubes.</p>'),
        ('<p><strong class="text-on-background font-title">1. Chain Progression:</strong> Start with 1 club. Each step adds another club to the chain—name any player who represented all active clubs in the chain to advance.</p>',
         '<p><strong class="text-on-background font-title">1. Progresión de la Cadena:</strong> Empieza con 1 club. Cada paso añade otro club a la cadena: nombra a cualquier jugador que haya vestido la camiseta de todos los clubes activos para avanzar.</p>'),
        ('<p><strong class="text-on-background font-title">2. 🎯 Instant Win:</strong> Guess the Player of the Day at <em>any</em> stage to end the game immediately in victory!</p>',
         '<p><strong class="text-on-background font-title">2. 🎯 Victoria Directa:</strong> ¡Adivina al Jugador del Día en <em>cualquier</em> paso para ganar la partida de inmediato!</p>'),
        ('<p><strong class="text-on-background font-title">3. Clues &amp; Skip:</strong> Reveal Nationality or Position hints for the mystery player, or skip a tricky club combination without penalty.</p>',
         '<p><strong class="text-on-background font-title">3. Pistas y Saltar:</strong> Revela pistas de Nacionalidad o Posición del jugador misterioso, o salta una combinación difícil sin penalización.</p>'),
        ('<p><strong class="text-on-background font-title">4. Lives &amp; VAR:</strong> Guessing an invalid player who does not match all active clubs deducts 1 life. Appeal disputed answers via official VAR review.</p>',
         '<p><strong class="text-on-background font-title">4. Vidas y VAR:</strong> Proponer un jugador no válido que no coincida con todos los clubes activos resta 1 vida. Apela decisiones dudosas mediante el VAR oficial.</p>'),
        ('<p><strong class="text-on-background font-title">5. No Repeat Guesses:</strong> Once a footballer is submitted, they cannot be reused in that session.</p>',
         '<p><strong class="text-on-background font-title">5. Sin Repetir Jugadores:</strong> Una vez enviado un futbolista, no se puede volver a utilizar en la misma partida.</p>'),
        ('<p><strong class="text-on-background font-title">6. Database Scope:</strong> Includes official senior club appearances and transfers since 1990 alongside verified historic legends throughout football history.</p>',
         '<p><strong class="text-on-background font-title">6. Base de Datos:</strong> Incluye partidos y traspasos oficiales del primer equipo desde 1990 junto a leyendas históricas verificadas de toda la historia del fútbol.</p>'),

        # Club Connect
        ('<p><strong class="text-on-background font-title">Goal:</strong> Identify the single mystery club that signed all 5 featured footballers.</p>',
         '<p><strong class="text-on-background font-title">Objetivo:</strong> Identifica el club misterioso que fichó a los 5 futbolistas destacados.</p>'),
        ('<p><strong class="text-on-background font-title">1. Sequential Clues:</strong> Players are revealed one by one in order of transfer fee, from the bargain signing up to the record transfer.</p>',
         '<p><strong class="text-on-background font-title">1. Pistas Secuenciales:</strong> Los jugadores se revelan uno a uno por orden de coste de traspaso, desde el fichaje más barato hasta el traspaso récord.</p>'),
        ('<p><strong class="text-on-background font-title">2. Guessing the Club:</strong> After each reveal, type and submit the club you believe signed all currently visible players.</p>',
         '<p><strong class="text-on-background font-title">2. Adivinar el Club:</strong> Tras cada pista, escribe y envía el club que crees que fichó a todos los jugadores actualmente visibles.</p>'),
        ('<p><strong class="text-on-background font-title">3. Card Hints:</strong> Click the lightbulb on any revealed player card to uncover the club they were signed from and their transfer fee.</p>',
         '<p><strong class="text-on-background font-title">3. Pistas de Tarjeta:</strong> Pulsa la bombilla en cualquier tarjeta visible para descubrir el club de origen y el coste de su traspaso.</p>'),
        ('<p><strong class="text-on-background font-title">4. Lives &amp; Penalties:</strong> Incorrect guesses deduct 1 life and automatically unlock the next player clue to help you connect the dots.</p>',
         '<p><strong class="text-on-background font-title">4. Vidas y Penalizaciones:</strong> Cada fallo resta 1 vida y desbloquea automáticamente la siguiente pista para ayudarte a conectar los puntos.</p>'),
        ('<p><strong class="text-on-background font-title">5. Winning:</strong> Correctly identify the mystery club at any stage before lives run out to claim victory!</p>',
         '<p><strong class="text-on-background font-title">5. Victoria:</strong> ¡Identifica correctamente el club misterioso en cualquier momento antes de quedarte sin vidas para ganar!</p>'),
        ('<p><strong class="text-on-background font-title">6. Database Scope:</strong> Covers official senior transfers and signings across European and international football.</p>',
         '<p><strong class="text-on-background font-title">6. Base de Datos:</strong> Cubre traspasos oficiales y fichajes del primer equipo en el fútbol europeo e internacional.</p>'),

        # Navigation & Badges
        ('>Prev<', '>Ant.<'),
        ('>Next<', '>Sig.<'),
        ('`PUZZLE #${puzzleNum} — PAST`', '`PUZZLE #${puzzleNum} — ANTERIOR`'),
        ('title="Play previous puzzle (back in time)"', 'title="Jugar puzzle anterior (modo retro)"'),
        ('title="Play newer/today\'s puzzle"', 'title="Jugar puzzle más reciente / de hoy"'),
        ('title="Daily puzzle number. Use arrows to play past puzzles!"', 'title="Número de puzzle diario. ¡Usa las flechas para jugar retos anteriores!"'),

        # Lives & Progress
        ('Lives:&nbsp;', 'Vidas:&nbsp;'),
        ('Lives:', 'Vidas:'),
        ('Guessed:&nbsp;', 'Adivinados:&nbsp;'),
        ('Guessed:', 'Adivinados:'),
        ('Progress:', 'Progreso:'),
        ('Progress: ', 'Progreso: '),
        ('Step:', 'Paso:'),
        ('Stamp:', 'Sello:'),
        ('+1 Life', '+1 Vida'),
        ('Give Up', 'Rendirse'),
        ('>GUESS<', '>ADIVINAR<'),
        ('>SUBMIT<', '>ENVIAR<'),
        ('>SKIP<', '>SALTAR<'),
        ('Skip</span>', 'Saltar</span>'),
        ('title="Skip this step if stuck"', 'title="Saltar este paso si te quedas atascado"'),
        ('title="Skip this nationality stamp"', 'title="Saltar este sello de nacionalidad"'),
        ('title="Reveal this step (costs 1 life)"', 'title="Revelar este paso (cuesta 1 vida)"'),
        ('title="Reveal this player"', 'title="Revelar este jugador"'),
        ('title="Reveal all hints for this row"', 'title="Revelar todas las pistas de esta fila"'),

        # Table Headers (Top Transfers & Top Scorers)
        ('<th class="py-3 px-3">Player</th>', '<th class="py-3 px-3">Jugador</th>'),
        ('<th id="th-club-header" class="py-3 px-3 hidden sm:table-cell">From Club</th>', '<th id="th-club-header" class="py-3 px-3 hidden sm:table-cell">Traspaso</th>'),
        ('<th class="py-3 px-3 text-right">Fee</th>', '<th class="py-3 px-3 text-right">Coste</th>'),
        ('<th class="py-3 px-3 text-center hidden md:table-cell">Year</th>', '<th class="py-3 px-3 text-center hidden md:table-cell">Año</th>'),
        ('<th class="py-3 px-3 text-right">Goals</th>', '<th class="py-3 px-3 text-right">Goles</th>'),
        ('<th class="py-3 px-3 hidden sm:table-cell">Club</th>', '<th class="py-3 px-3 hidden sm:table-cell">Club</th>'),
        ('<th class="py-3 px-3 text-center hidden md:table-cell">Apps</th>', '<th class="py-3 px-3 text-center hidden md:table-cell">Partidos</th>'),
        ('<th class="py-3 px-3 hidden lg:table-cell">Nationality</th>', '<th class="py-3 px-3 hidden lg:table-cell">Nacionalidad</th>'),
        ('<th class="py-3 px-3 w-24 text-center">Actions</th>', '<th class="py-3 px-3 w-24 text-center">Acciones</th>'),

        # Hero Banners & Section Labels (Static substrings)
        ('>RECORD SIGNINGS FOR<', '>FICHAJES RÉCORD DE<'),
        ('>MOST EXPENSIVE TRANSFERS FOR<', '>LOS FICHAJES MÁS CAROS DE<'),
        ('>TOP 10 SCORERS IN<', '>TOP 10 GOLEADORES DE<'),
        ('>ALL-TIME GOALSCORERS FOR<', '>MÁXIMOS GOLEADORES DE<'),
        ('>Player of the Day<', '>Jugador del Día<'),
        ('>Player of the Day</span>', '>Jugador del Día</span>'),
        ('>Mystery Player of the Day<', '>Jugador Misterioso del Día<'),
        ('>Mystery Player of the Day</span>', '>Jugador Misterioso del Día</span>'),
        ('>TODAY\'S CLUB PASSPORT<', '>PASAPORTE DEL CLUB DE HOY<'),
        ('>TODAY\'S CLUB PASSPORT</span>', '>PASAPORTE DEL CLUB DE HOY</span>'),
        ('>MYSTERY CLUB CONNECTION<', '>CONEXIÓN DE CLUB MISTERIOSO<'),
        ('>REVEAL NEXT CLUE<', '>REVELAR SIGUIENTE PISTA<'),
        ('>TEAMMATE CHAIN<', '>CADENA DE COMPAÑEROS<'),
        ('>STARTING PLAYER<', '>JUGADOR INICIAL<'),
        ('>TARGET PLAYER<', '>JUGADOR OBJETIVO<'),
        ('>CLUB PASSPORT<', '>PASAPORTE DE CLUB<'),
        ('>CAREER TIMELINE<', '>TRAYECTORIA DEPORTIVA<'),
        ('>INCORRECT GUESSES<', '>INTENTOS INCORRECTOS<'),
        ('>Career Chain Progression<', '>Progresión de la Cadena de Clubes<'),
        ('>No Repeat Guesses<', '>Sin Repetir Jugadores<'),
        ('>The Nationality Ladder<', '>La Escalera de Nacionalidades<'),
        ('>Large Pool &rarr; Rare Unicorn<', '>Gran Potencia &rarr; Unicornio Raro<'),
        ('>CAREER RECAP<', '>RESUMEN DE TRAYECTORIA<'),
        ('>Explore the complete club chain and all eligible footballers for each step.<', '>Explora la cadena completa de clubes y todos los futbolistas válidos de cada paso.<'),
        ('>Step-by-Step Breakdown<', '>Desglose Paso a Paso<'),
        ('>Click any step to view valid answers<', '>Haz clic en cualquier paso para ver las respuestas válidas<'),
        ('>View Results<', '>Ver Resultados<'),
        ('>GAME COMPLETED<', '>JUEGO COMPLETADO<'),
        ('>Explore all eligible footballers who played for the anchor club for each nation.<', '>Explora todos los futbolistas válidos que jugaron en el club ancla para cada país.<'),

        # Clues & Hints
        ('<span>Hint: Nationality</span>', '<span>Pista: Nacionalidad</span>'),
        ('<span>Hint: Position</span>', '<span>Pista: Posición</span>'),
        ('title="Reveal player nationality"', 'title="Revelar nacionalidad del jugador"'),
        ('title="Reveal player position"', 'title="Revelar posición del jugador"'),
        ('<span id="hint-btn-text">Hint</span>', '<span id="hint-btn-text">Pista</span>'),
        ('>Instant Win:</strong>', '>Victoria Directa:</strong>'),
        ('Guess this mystery player at <em>any</em> stage to win instantly!', '¡Adivina al jugador misterioso en <em>cualquier</em> paso para ganar directamente!'),

        # Placeholders
        ('placeholder="Type and select player name..."', 'placeholder="Escribe y selecciona el nombre del jugador..."'),
        ('placeholder="Type and select club name..."', 'placeholder="Escribe y selecciona el nombre del club..."'),
        ('placeholder="Type and select club..."', 'placeholder="Escribe y selecciona el club..."'),
        ('placeholder="Type club name..."', 'placeholder="Escribe el nombre del club..."'),
        ('placeholder="Type a footballer\'s name..."', 'placeholder="Escribe el nombre de un futbolista..."'),
        ('placeholder="Search player or guess direct win..."', 'placeholder="Buscar jugador o ganar directamente..."'),
        ('placeholder="Search eligible player..."', 'placeholder="Buscar jugador elegible..."'),

        # Error & Alert Messages
        ('Please select a player name from the dropdown.', 'Por favor selecciona un jugador de la lista desplegable.'),
        ('Please select a club from the autocomplete list.', 'Por favor selecciona un club de la lista desplegable.'),
        ('Please select a club from the dropdown.', 'Por favor selecciona un club de la lista desplegable.'),
        ('Please pick a footballer from the dropdown.', 'Por favor selecciona un futbolista de la lista desplegable.'),

        # Modal End-Game Strings
        ('>Guessed</span>', '>Adivinados</span>'),
        ('>Streak</span>', '>Racha</span>'),
        ('>Best</span>', '>Récord</span>'),
        ('>Score</span>', '>Puntuación</span>'),
        ('>Stamps</span>', '>Sellos</span>'),
        ('>Steps</span>', '>Pasos</span>'),
        ('>Step</span>', '>Paso</span>'),
        ('>Play Past Puzzles</p>', '>Jugar Puzzles Anteriores</p>'),
        ('>Play Past Puzzles<', '>Jugar Puzzles Anteriores<'),
        ('>SHARE</button>', '>COMPARTIR</button>'),
        ('>CLOSE</button>', '>CERRAR</button>'),
        ('>GOT IT</button>', '>ENTENDIDO</button>'),
        ('>THE MYSTERY PLAYER WAS<', '>EL JUGADOR MISTERIOSO ERA<'),
        ('>MYSTERY PLAYER OF THE DAY<', '>JUGADOR MISTERIOSO DEL DÍA<'),
        ('>THE MYSTERY CLUB WAS<', '>EL CLUB MISTERIOSO ERA<'),
        ('>THE MYSTERY CLUB<', '>EL CLUB MISTERIOSO<'),
        ('>COMPLETED</h3>', '>¡COMPLETADO!</h3>'),
        ('>COMPLETED<', '>¡COMPLETADO!<'),

        # SEO / Footer Section
        ('>HOW TO PLAY</h2>', '>CÓMO JUGAR</h2>'),
        ('>HOW TO PLAY</h3>', '>CÓMO JUGAR</h3>'),
        ('What is Passport FC?', '¿Qué es Pasaporte FC?'),
        ('>What is Passport FC?</h2>', '>¿Qué es Pasaporte FC?</h2>'),
        ('<strong>Database Coverage:</strong>', '<strong>Cobertura de la Base de Datos:</strong>'),
        ('Official senior appearances and transfers since 1990 plus verified historic legends throughout club history (updated to June 2026).', 'Partidos oficiales y fichajes del primer equipo desde 1990 más leyendas históricas verificadas (actualizado a junio de 2026).'),
        ('Official senior appearances and transfers since 1990 plus verified historic legends throughout club history (updated to September 2026).', 'Partidos oficiales y fichajes del primer equipo desde 1990 más leyendas históricas verificadas (actualizado a junio de 2026).'),
        ('<strong>VAR Verification:</strong>', '<strong>Verificación VAR:</strong>'),
        ('Players can submit any disputed answer to the automated VAR engine to appeal real-world transfer and appearance records.', 'Los jugadores pueden enviar cualquier respuesta disputada al motor automatizado del VAR para apelar registros reales de fichajes y partidos.'),
        ('>MORE DAILY CHALLENGES</h3>', '>MÁS RETOS DIARIOS</h3>'),
        ('>MORE DAILY CHALLENGES</h2>', '>MÁS RETOS DIARIOS</h2>'),
        ('>Transfer Destination</span>', '>Destino de Fichaje</span>'),
        ('<p class="text-on-surface-variant text-xs">Guess a player\'s career path</p>', '<p class="text-on-surface-variant text-xs">Adivina la trayectoria de un jugador</p>'),
        ('>Top Scorers</span>', '>Máximos Goleadores</span>'),
        ('<p class="text-on-surface-variant text-xs">Name the top goalscorers</p>', '<p class="text-on-surface-variant text-xs">Nombra a los máximos goleadores</p>'),
        ('<p class="text-on-surface-variant text-xs">Guess the top goalscorers</p>', '<p class="text-on-surface-variant text-xs">Nombra a los máximos goleadores</p>'),
        ('>Club Connect</span>', '>Conexión de Clubes</span>'),
        ('<p class="text-on-surface-variant text-xs">5 players, 1 club signed them all — spot the mystery connection</p>', '<p class="text-on-surface-variant text-xs">5 jugadores, 1 club los fichó a todos — descubre la conexión misteriosa</p>'),
        ('<p class="text-on-surface-variant text-xs">5 players, 1 club signed them all</p>', '<p class="text-on-surface-variant text-xs">5 jugadores, 1 club los fichó a todos</p>'),
        ('>Top Transfers</span>', '>Top Fichajes</span>'),
        ('<p class="text-on-surface-variant text-xs">Guess the record transfer signings</p>', '<p class="text-on-surface-variant text-xs">Adivina los fichajes récord de clubes y países</p>'),
        ('<p class="text-on-surface-variant text-xs">Guess the record signings</p>', '<p class="text-on-surface-variant text-xs">Adivina los fichajes récord de clubes y países</p>'),
        ('>Player Chain</span>', '>Cadena de Jugadores</span>'),
        ('<p class="text-on-surface-variant text-xs">Connect players across an expanding club chain</p>', '<p class="text-on-surface-variant text-xs">Conecta jugadores a lo largo de una cadena de clubes</p>'),
        ('<p class="text-on-surface-variant text-xs">Connect consecutive clubs through shared teammates</p>', '<p class="text-on-surface-variant text-xs">Conecta clubes consecutivos mediante compañeros de equipo</p>'),
        ('>Passport FC</span>', '>Pasaporte FC</span>'),
        ('<p class="text-on-surface-variant text-xs">Collect nationality stamps from major pools to unicorns</p>', '<p class="text-on-surface-variant text-xs">Consigue sellos de nacionalidad de potencias a unicornios</p>'),
        ('← Back to Playmaker Lobby', '← Volver al Lobby de Playmaker'),
        ('← BACK TO PLAYMAKER LOBBY', '← VOLVER AL LOBBY DE PLAYMAKER'),
        ('Back to Playmaker Lobby', 'Volver al Lobby de Playmaker'),
        ('BACK TO PLAYMAKER LOBBY', 'VOLVER AL LOBBY DE PLAYMAKER'),
        ('Playmaker Lobby', 'Lobby de Playmaker'),
        ('← Back to Playmaker', '← Volver a Playmaker'),
        ('← BACK TO PLAYMAKER', '← VOLVER A PLAYMAKER'),
        ('Privacy Policy', 'Política de Privacidad'),
        ('Terms & Conditions', 'Términos y Condiciones'),
        ('Terms &amp; Conditions', 'Términos y Condiciones'),
        ('All Games', 'Todos los Juegos'),
        ('Arcade Lobby', 'Lobby Arcade'),
        ('STEP 1 &mdash; NAME A QUALIFYING FOOTBALLER:', 'PASO 1 &mdash; NOMBRA A UN JUGADOR VÁLIDO:'),
        ('STEP 1 — NAME A QUALIFYING FOOTBALLER:', 'PASO 1 — NOMBRA A UN JUGADOR VÁLIDO:'),
        ('Type player name...', 'Escribe el nombre del jugador...'),
        ('>GUESS</button>', '>ADIVINAR</button>'),
        ('>GUESS\n                </button>', '>ADIVINAR\n                </button>'),
        ('Transfer data sourced from Transfermarkt. Updated to June 2026.', 'Datos de transferencias de Transfermarkt. Actualizados a junio de 2026.'),
        ('Transfer data sourced from Transfermarkt. Updated to July 2026.', 'Datos de transferencias de Transfermarkt. Actualizados a junio de 2026.'),
        ('Transfer data sourced from Transfermarkt. Updated to September 2026.', 'Datos de transferencias de Transfermarkt. Actualizados a junio de 2026.'),
        ('Connect consecutive clubs through shared teammates to uncover the mystery player of the day. Each step adds a new club or national team constraint. Guess an eligible teammate to advance, or identify the mystery player directly for an instant win!', 'Conecta clubes consecutivos mediante compañeros de equipo para descubrir al jugador misterioso del día. Cada paso añade una restricción de club o selección. ¡Adivina un compañero válido para avanzar o identifica al jugador misterioso directamente para ganar!'),
        ('Career & transfer data sourced from Transfermarkt. Updated to June 2026.', 'Datos de trayectoria y traspasos de Transfermarkt. Actualizados a junio de 2026.'),
        # Accessibility & Button titles
        ('aria-label="How to play instructions"', 'aria-label="Instrucciones de cómo jugar"'),
        ('title="How to play"', 'title="Cómo jugar"'),
        ('aria-label="Close how to play modal"', 'aria-label="Cerrar ventana de cómo jugar"'),
    ]

    for orig, rep in global_replacements:
        es_html = es_html.replace(orig, rep)

    # Multiline / Flexible whitespace heading replacements
    regex_headings = [
        (r'>\s*The Career Path Puzzle\s*<', '>El Puzzle de Trayectoria<'),
        (r'>\s*Stamp The Club Passport\s*<', '>Sella el Pasaporte del Club<'),
        (r'>\s*Which Club Signed All 5 Players\?\s*<', '>¿Qué Club Fichó a los 5 Jugadores?<'),
        (r'>\s*Career Path Challenge\s*<', '>Reto de Trayectoria Deportiva<'),
        (r'>\s*Full Career Path &amp; Answers\s*<', '>Trayectoria Completa y Respuestas<'),
        (r'>\s*Full Career Path & Answers\s*<', '>Trayectoria Completa y Respuestas<'),
        (r'>\s*Complete Ladder &amp; Answers\s*<', '>Escalera Completa y Respuestas<'),
        (r'>\s*Complete Ladder & Answers\s*<', '>Escalera Completa y Respuestas<'),
        (r'>\s*Top Modern Era Signings \(2012–Present\)\s*<', '>Fichajes Récord de la Era Moderna (2012–Presente)<'),
        (r'>\s*Top Scorers per League &amp; Season\s*<', '>Máximos Goleadores por Liga y Temporada<'),
        (r'>\s*Top Scorers per League & Season\s*<', '>Máximos Goleadores por Liga y Temporada<'),
        (r'>\s*All-Time Top Goalscorers\s*<', '>Máximos Goleadores Históricos<'),
        (r'>\s*Nationality Transfer Records\s*<', '>Récords de Fichajes por Nacionalidad<'),
        (r'>\s*Club Record Signings\s*<', '>Fichajes Récord del Club<'),
        (r'>\s*MORE DAILY CHALLENGES\s*<', '>MÁS RETOS DIARIOS<'),
        (r'>\s*GUESS\s*</button>', '>ADIVINAR</button>'),
        (r'>\s*SUBMIT\s*</button>', '>ENVIAR</button>'),
        (r'>\s*What is Passport FC\?\s*<', '>¿Qué es Pasaporte FC?<'),
        (r'>\s*CLOSE\s*</button>', '>CERRAR</button>'),
        (r'>\s*SHARE\s*</button>', '>COMPARTIR</button>'),
        (r'>\s*GOT IT\s*</button>', '>ENTENDIDO</button>'),
        (r'>\s*THE MYSTERY PLAYER WAS\s*<', '>EL JUGADOR MISTERIOSO ERA<'),
        (r'>\s*MYSTERY PLAYER OF THE DAY\s*<', '>JUGADOR MISTERIOSO DEL DÍA<'),
        (r'<span class="material-symbols-outlined text-md">share</span>\s*SHARE', '<span class="material-symbols-outlined text-md">share</span> COMPARTIR'),
    ]
    for pattern, rep in regex_headings:
        es_html = re.sub(pattern, rep, es_html)

    # 5. JavaScript Dynamic Logic Replacements
    js_replacements = [
        # Top Transfers JS dynamic labels
        ("document.getElementById('game-title').textContent    = 'Club Record Signings';", "document.getElementById('game-title').textContent = 'Fichajes Récord del Club';"),
        ("document.getElementById('target-label').textContent  = 'RECORD SIGNINGS FOR';", "document.getElementById('target-label').textContent = 'FICHAJES RÉCORD DE';"),
        ("document.getElementById('game-title').textContent    = 'Nationality Transfer Records';", "document.getElementById('game-title').textContent = 'Récords de Fichajes por Nacionalidad';"),
        ("document.getElementById('target-label').textContent  = 'MOST EXPENSIVE TRANSFERS FOR';", "document.getElementById('target-label').textContent = 'LOS FICHAJES MÁS CAROS DE';"),
        ("document.getElementById('th-club-header').textContent = 'Transfer';", "document.getElementById('th-club-header').textContent = 'Fichaje';"),
        ("title: 'REVEAL PLAYER?'", "title: '¿REVELAR JUGADOR?'"),
        ("message: 'Are you sure you want to reveal this player?'", "message: '¿Estás seguro de que quieres revelar este jugador?'"),
        ("confirmText: 'REVEAL'", "confirmText: 'REVELAR'"),
        ("cancelText: 'CANCEL'", "cancelText: 'CANCELAR'"),
        ("title: 'CORRECT!'", "title: '¡CORRECTO!'"),
        ("title: 'INCORRECT!'", "title: '¡INCORRECTO!'"),
        ("was already guessed!", "ya fue adivinado!"),
        ("is on the list!", "está en la lista!"),
        ("is not on the list. Lost 1 life.", "no está en la lista. Pierdes 1 vida."),

        # Transfer Destination JS dynamic labels
        ("document.getElementById('active-step-label').textContent =\n                    `GUESS CLUB BEFORE ${activeGameData.transfers[i].to_club_name.toUpperCase()}`;",
         "document.getElementById('active-step-label').textContent =\n                    `ADIVINA EL CLUB ANTES DE ${activeGameData.transfers[i].to_club_name.toUpperCase()}`;"),
        ("`GUESS CLUB BEFORE ${activeGameData.transfers[i].to_club_name.toUpperCase()}`",
         "`ADIVINA EL CLUB ANTES DE ${activeGameData.transfers[i].to_club_name.toUpperCase()}`"),
        ("<span>Season: ${year}</span>", "<span>Temporada: ${year}</span>"),
        ("title: won ? 'CAREER SOLVED!' : (isPartial ? 'CAREER SURVIVED!' : 'GAME OVER')",
         "title: won ? '¡TRAYECTORIA COMPLETADA!' : (isPartial ? '¡TRAYECTORIA SUPERADA!' : 'FIN DE LA PARTIDA')"),
        ("'Brilliant! You predicted the complete transfer trajectory.'",
         "'¡Excelente! Has acertado toda la trayectoria de fichajes.'"),
        ("`Resilient finish! You navigated the full career timeline, scoring ${score} of ${total} clubs.`",
         "`¡Gran resistencia! Completaste la trayectoria con ${score} de ${total} clubes.`"),
        ("'You couldn\\'t predict the entire career path.'",
         "'No pudiste predecir toda la trayectoria deportiva.'"),
        ("is not the previous club. Lost 1 life.", "no es el club anterior. Pierdes 1 vida."),
        ("is correct!", "es correcto!"),

        # Top Scorers JS dynamic labels
        ("document.getElementById('game-title').textContent    = 'All-Time Top Goalscorers';", "document.getElementById('game-title').textContent = 'Máximos Goleadores Históricos';"),
        ("document.getElementById('target-label').textContent  = 'ALL-TIME GOALSCORERS FOR';", "document.getElementById('target-label').textContent = 'MÁXIMOS GOLEADORES DE';"),
        ("document.getElementById('game-title').textContent    = 'Top Scorers per League & Season';", "document.getElementById('game-title').textContent = 'Máximos Goleadores por Liga y Temporada';"),
        ("document.getElementById('target-label').textContent  = 'TOP 10 SCORERS IN';", "document.getElementById('target-label').textContent = 'TOP 10 GOLEADORES DE';"),

        # Club Connect JS dynamic labels
        ("answerLabel.textContent = won ? 'THE MYSTERY CLUB' : 'THE MYSTERY CLUB WAS';",
         "answerLabel.textContent = won ? 'EL CLUB MISTERIOSO' : 'EL CLUB MISTERIOSO ERA';"),
        ("title:           won ? 'CONNECTED!' : 'GAME OVER',",
         "title: won ? '¡CONECTADO!' : 'FIN DE LA PARTIDA',"),
        ("title:     'WRONG CLUB!',", "title: '¡CLUB INCORRECTO!',"),
        ("`Not ${guessedName}. Here's another player hint.`", "`No es el ${guessedName}. Aquí tienes otra pista.`"),
        ("`Unbelievable! You spotted ${activeGameData.club} from just one player!`", "`¡Increíble! ¡Descubriste al ${activeGameData.club} con un solo jugador!`"),
        ("`Clutch! You connected all players to ${activeGameData.club} on the final reveal!`", "`¡En el último momento! Conectaste a todos los jugadores con el ${activeGameData.club} en la última pista.`"),
        ("`Brilliant! You connected all players to ${activeGameData.club} after ${score} reveals!`", "`¡Excelente! Conectaste a todos los jugadores con el ${activeGameData.club} tras ${score} pistas.`"),
        ("`Today's mystery club was ${activeGameData.club}. Better luck tomorrow!`", "`El club misterioso de hoy era el ${activeGameData.club}. ¡Mejor suerte mañana!`"),
        ("score === 1 ? '1 card' : `${score} cards`", "score === 1 ? '1 pista' : `${score} pistas`"),

        # Player Chain JS dynamic labels & step progression
        ("`STEP ${i + 1} — NAME ANY PLAYER WHO PLAYED FOR:`", "`PASO ${i + 1} — NOMBRA A UN JUGADOR QUE HAYA JUGADO EN:`"),
        ("STEP 1 — NAME ANY PLAYER WHO PLAYED FOR:", "PASO 1 — NOMBRA A UN JUGADOR QUE HAYA JUGADO EN:"),
        ("<span>Nationality: <strong id=\"revealed-target-nat\"", "<span>Nacionalidad: <strong id=\"revealed-target-nat\""),
        ("<span>Position: <strong id=\"revealed-target-pos\"", "<span>Posición: <strong id=\"revealed-target-pos\""),
        ("CURRENT STEP ${step.step_number}", "PASO ACTUAL ${step.step_number}"),
        ("<span class=\"text-[10px] sm:text-[11px] font-mono text-accent font-bold px-2 py-1 bg-accent/10 rounded-md border border-accent/20\">ACTIVE</span>",
         "<span class=\"text-[10px] sm:text-[11px] font-mono text-accent font-bold px-2 py-1 bg-accent/10 rounded-md border border-accent/20\">ACTIVO</span>"),
        ("<span>Must have played for all ${step.active_clubs.length} clubs / teams:</span>",
         "<span>Debe haber jugado en los ${step.active_clubs.length} clubes / selecciones:</span>"),
        ("<span>Must have played for all ${step.active_clubs.length} clubs:</span>",
         "<span>Debe haber jugado en los ${step.active_clubs.length} clubes:</span>"),
        ("badgeText   = 'SOLVED';", "badgeText = 'COMPLETADO';"),
        ("badgeText   = 'INSTANT WIN ⭐️';", "badgeText = 'VICTORIA DIRECTA ⭐️';"),
        ("badgeText   = 'SKIPPED';", "badgeText = 'SALTADO';"),
        ("Step ${step.step_number}: + ${step.club}", "Paso ${step.step_number}: + ${step.club}"),
        ("Step ${step.step_number} — Locked", "Paso ${step.step_number} — Bloqueado"),
        ("Complete Step ${step.step_number - 1} to reveal next constraint",
         "Completa el Paso ${step.step_number - 1} para desbloquear la siguiente pista"),
        ("<span class=\"text-[10px] font-mono uppercase text-on-surface-variant/60 mr-1\">Clubs:</span>",
         "<span class=\"text-[10px] font-mono uppercase text-on-surface-variant/60 mr-1\">Clubes:</span>"),
        ("Your pick: <strong class=\"font-bold\">${rec.guessed}</strong>",
         "Tu elección: <strong class=\"font-bold\">${rec.guessed}</strong>"),
        ("<span class=\"text-xs font-mono px-2.5 py-1 rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/25\">Skipped</span>",
         "<span class=\"text-xs font-mono px-2.5 py-1 rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/25\">Saltado</span>"),
        ("STEP ${step.step_number} · ${step.club}", "PASO ${step.step_number} · ${step.club}"),
        ("Played for: <span class=\"text-accent\">${constraintsStr}</span>",
         "Jugó en: <span class=\"text-accent\">${constraintsStr}</span>"),
        ("<span class=\"font-medium\">Show all ${validList.length} valid footballers</span>",
         "<span class=\"font-medium\">Mostrar los ${validList.length} futbolistas válidos</span>"),
        ("title: didInstantWin ? 'INSTANT WIN!' : (result.won ? 'CHAIN COMPLETED!' : (isPartial ? 'CHAIN SURVIVED!' : 'GAME OVER'))",
         "title: didInstantWin ? '¡VICTORIA DIRECTA!' : (result.won ? '¡CADENA COMPLETADA!' : (isPartial ? '¡CADENA SUPERADA!' : 'FIN DE LA PARTIDA'))"),
        ("let modalTitle = 'CHAIN COMPLETED!';", "let modalTitle = '¡CADENA COMPLETADA!';"),
        ("modalTitle = 'INSTANT WIN!';", "modalTitle = '¡VICTORIA DIRECTA!';"),
        ("modalTitle = 'CHAIN SURVIVED!';", "modalTitle = '¡CADENA SUPERADA!';"),
        ("modalTitle = 'GAME OVER';", "modalTitle = 'FIN DE LA PARTIDA';"),
        ("`Incredible football IQ! You identified ${activeGameData.target_player} directly and cracked the chain.`",
         "`¡Increíble IQ futbolístico! Identificaste a ${activeGameData.target_player} directamente y completaste la cadena.`"),
        ("`Masterclass! You connected every club in the chain to reveal ${activeGameData.target_player}.`",
         "`¡Magistral! Conectaste todos los clubes de la cadena para descubrir a ${activeGameData.target_player}.`"),
        ("`You navigated the teammate chain to ${activeGameData.target_player}! Solved ${result.score} of ${activeGameData.total_steps} links.`",
         "`¡Superaste la cadena de compañeros hasta ${activeGameData.target_player}! Acertaste ${result.score} de ${activeGameData.total_steps} enlaces.`"),
        ("`You navigated the teammate chain to ${activeGameData.target_player}! Solved ${finalScore} of ${totalSteps} links.`",
         "`¡Superaste la cadena de compañeros hasta ${activeGameData.target_player}! Acertaste ${finalScore} de ${totalSteps} enlaces.`"),
        ("`Tough luck! Today's mystery player was ${activeGameData.target_player}. Review the full chain below!`",
         "`¡Mala suerte! El jugador misterioso de hoy era ${activeGameData.target_player}. ¡Revisa la cadena completa abajo!`"),
        ("`STEP ${currStep.step_number} CRITERIA — NAME ANY PLAYER WHO PLAYED FOR:`",
         "`CRITERIO PASO ${currStep.step_number} — NOMBRA A UN JUGADOR QUE HAYA JUGADO EN:`"),

        # Passport FC JS dynamic labels
        ("Collect all 4 nationality stamps for", "¡Consigue los 4 sellos de nacionalidad de"),
        ("Position: Forward", "Posición: Delantero"),
        ("Position: Midfield", "Posición: Centrocampista"),
        ("Position: Defender", "Posición: Defensa"),
        ("Position: Goalkeeper", "Posición: Portero"),
        ("STAMP #${idx + 1}", "SELLO #${idx + 1}"),
        ("Stamp #${idx + 1}", "Sello #${idx + 1}"),
        ("'The Unicorn Stamp'", "'El Sello Unicornio'"),
        ('"The Unicorn Stamp"', '"El Sello Unicornio"'),
        (">LOCKED</span>", ">BLOQUEADO</span>"),
        ("Complete Stamp #${idx} to reveal destination", "Completa el Sello #${idx} para revelar el destino"),
        ("<span class=\"material-symbols-outlined text-sm\">lock</span> Locked</span>",
         "<span class=\"material-symbols-outlined text-sm\">lock</span> Bloqueado</span>"),
        ("Only 1 Qualifying Unicorn!", "¡Solo 1 Unicornio Elegible!"),
        ("${poolCount} Qualifying Players", "${poolCount} Futbolistas Elegibles"),
        ("<span class=\"material-symbols-outlined text-sm\">cancel</span> Skipped</span>",
         "<span class=\"material-symbols-outlined text-sm\">cancel</span> Saltado</span>"),
        ("<span class=\"material-symbols-outlined text-sm\">check_circle</span> Solved</span>",
         "<span class=\"material-symbols-outlined text-sm\">check_circle</span> Completado</span>"),
        ("<span class=\"material-symbols-outlined text-sm animate-spin\">sync</span> In Progress</span>",
         "<span class=\"material-symbols-outlined text-sm animate-spin\">sync</span> En Curso</span>"),
        ("Your answer: <strong class=\"text-white font-bold\">${rec.guessed}</strong>",
         "Tu respuesta: <strong class=\"text-white font-bold\">${rec.guessed}</strong>"),
        ("${poolCount} total qualifying", "${poolCount} total elegibles"),
        ("Valid: <strong class=\"text-white\">", "Válidos: <strong class=\"text-white\">"),
    ]

    for orig, rep in js_replacements:
        es_html = es_html.replace(orig, rep)

    # 6. Game Specific Titles, Descriptions & SEO Meta Tags
    game_titles = {
        "top_transfers": ("TOP TRANSFERS", "TOP FICHAJES"),
        "transfer_destination": ("TRANSFER DESTINATION", "DESTINO DE FICHAJE"),
        "top_scorers": ("TOP SCORERS", "MÁXIMOS GOLEADORES"),
        "club_connect": ("CLUB CONNECT", "CONEXIÓN DE CLUBES"),
        "player_chain": ("PLAYER CHAIN", "CADENA DE JUGADORES"),
        "passport_fc": ("PASSPORT FC", "PASAPORTE FC"),
    }
    if game_id in game_titles:
        en_t, es_t = game_titles[game_id]
        es_html = re.sub(rf'>\s*{re.escape(en_t)}\s*<', f'>{es_t}<', es_html)

    meta_titles = {
        "top_transfers": ("Top Transfers — Daily Football Transfer Quiz | Playmaker", "Top Fichajes — Quiz Diario de Fichajes de Fútbol | Playmaker"),
        "transfer_destination": ("Transfer Destination — Daily Football Career Quiz | Playmaker", "Destino de Fichaje — Quiz Diario de Trayectorias de Fútbol | Playmaker"),
        "top_scorers": ("Top Scorers — Daily Football Goalscorer Quiz | Playmaker", "Máximos Goleadores — Quiz Diario de Goleadores de Fútbol | Playmaker"),
        "club_connect": ("Club Connect — Daily Football Teammates Quiz | Playmaker", "Conexión de Clubes — Quiz Diario de Compañeros de Fútbol | Playmaker"),
        "player_chain": ("Player Chain — Daily Football Career Puzzle | Playmaker", "Cadena de Jugadores — Puzzle Diario de Trayectorias de Fútbol | Playmaker"),
        "passport_fc": ("Passport FC — Daily Football Nationality Puzzle | Playmaker", "Pasaporte FC — Puzzle Diario de Nacionalidades de Fútbol | Playmaker"),
    }
    if game_id in meta_titles:
        en_m, es_m = meta_titles[game_id]
        es_html = es_html.replace(en_m, es_m)

    game_descriptions = {
        "top_transfers": (
            "Fill the transfers table below for the given club or nationality. Use the search bar to guess players. Only players from the search dropdown can be guessed. Use the hints (<span class=\"material-symbols-outlined text-xs inline-block align-middle text-accent\">lightbulb</span>) or reveal individual players if you are stuck!",
            "Completa la tabla de fichajes para el club o nacionalidad indicada. Usa el buscador para adivinar los jugadores. Solo los jugadores de la lista desplegable son válidos. ¡Usa las pistas (<span class=\"material-symbols-outlined text-xs inline-block align-middle text-accent\">lightbulb</span>) o revela jugadores si te quedas atascado!"
        ),
        "transfer_destination": (
            "Guess each previous club in the player's career, starting from their most recent destination back to where it all began!",
            "¡Adivina cada club anterior en la carrera del jugador, empezando desde su destino más reciente hasta sus inicios!"
        ),
        "top_scorers": (
            "Fill the scorers table below for the given league and season. Use the search bar to guess players. Only players from the search dropdown can be guessed. Use the hints (<span class=\"material-symbols-outlined text-xs inline-block align-middle text-accent\">lightbulb</span>) or reveal individual players if you are stuck!",
            "Completa la tabla de goleadores para la liga o competición indicada. Usa el buscador para adivinar los jugadores. Solo los jugadores de la lista desplegable son válidos. ¡Usa las pistas (<span class=\"material-symbols-outlined text-xs inline-block align-middle text-accent\">lightbulb</span>) o revela jugadores si te quedas atascado!"
        ),
        "club_connect": (
            "Players are revealed one by one — cheapest signing first. Guess the mystery club after each reveal. Wrong answer = next player unlocks &amp; 1 life lost.",
            "Los jugadores se revelan uno a uno, del fichaje más barato al más caro. Adivina el club misterioso tras cada pista. Fallo = se desbloquea el siguiente jugador y pierdes 1 vida."
        ),
        "player_chain": (
            "Guess the mystery Player of the Day by identifying footballers across an expanding chain of career clubs.",
            "Adivina al Jugador Misterioso del Día identificando futbolistas a lo largo de una cadena de clubes."
        ),
        "passport_fc": (
            "Name qualifying footballers across 4 progressive nationality tiers to fill today's club passport — from major talent pools down to rare 1-player unicorns.",
            "Nombra futbolistas elegibles en 4 niveles progresivos de nacionalidad para completar el pasaporte del club de hoy — desde grandes potencias hasta unicornios de un solo jugador."
        ),
    }
    if game_id in game_descriptions:
        en_d, es_d = game_descriptions[game_id]
        es_html = es_html.replace(en_d, es_d)

    # SEO How to play paragraph replacements
    how_to_play_paragraphs = {
        "top_transfers": (
            "Top Transfers is a daily football transfer leaderboard quiz by Playmaker where fans guess the top 10 all-time record signings for a featured club or nationality. Each daily challenge presents ten hidden leaderboard slots ordered from the most expensive record transfer down to the tenth largest fee. Players input football player names to fill the transfer board before accumulating three strikes. Correct answers lock onto the board with their transfer fee in Euros, buying club, selling club, and signing year. Players can activate hints to reveal transfer fee amounts or signing years for locked slots. Top Transfers covers verified senior transfer records across global football from 1990 to present, with streak tracking, VAR appeals, and daily puzzle refreshes at midnight UTC.",
            "Top Transfers es un quiz diario de fichajes de fútbol de Playmaker donde los aficionados adivinan los 10 fichajes récord de un club o nacionalidad destacada. Cada reto diario presenta diez posiciones ocultas ordenadas desde el fichaje récord más caro hasta el décimo más alto. Los jugadores ingresan nombres de futbolistas para completar la tabla antes de acumular tres fallos. Las respuestas correctas se fijan en el tablero con su coste en euros, club comprador, club vendedor y año del fichaje. Los jugadores pueden activar pistas para revelar importes o años en las casillas bloqueadas. Adivina los 10 fichajes récord con seguimiento de racha, revisiones de VAR y nuevos retos diarios a medianoche UTC."
        ),
        "transfer_destination": (
            "Transfer Destination is a daily football career deduction game by Playmaker where players identify a star footballer from their career transfer trajectory in reverse chronological order. The puzzle begins with the player's most recent or current club. Each incorrect guess costs one life and unlocks the preceding club in the footballer's transfer history along with years active and transfer fee details. Players aim to deduce the footballer's identity with as few transfer clues as possible. Clues span senior club debuts, marquee European transfers, loan spells, and international caps. The game features interactive VAR review for contested career records, local streak tracking, and shareable Wordle-style results. Puzzles update every day at midnight UTC with a 7-day playable archive.",
            "Reto de Trayectoria Deportiva es un juego diario de deducción de carreras futbolísticas de Playmaker donde los jugadores identifican a un futbolista estrella a partir de su trayectoria de traspasos en orden cronológico inverso. El reto comienza con el club más reciente o actual del jugador. Cada fallo cuesta una vida y desbloquea el club anterior en la carrera del futbolista junto con los años y detalles del traspaso. Los jugadores intentan deducir la identidad del futbolista con la menor cantidad de pistas posible. ¡Juega a diario y mantén tu racha!"
        ),
        "top_scorers": (
            "Top Scorers is a daily football goalscoring trivia puzzle by Playmaker celebrating the most prolific strikers and golden boot winners across football history. Each day presents a specific goalscoring category — such as all-time top scorers for a club, a single Champions League season, or a World Cup tournament. Players must name qualifying goalscorers to uncover the top leaderboard positions before running out of lives. Correct guesses display official goal tallies, season years, and player nationalities. Players can trigger hints to reveal goal totals or national flags. The database covers verified senior official goal records across the Premier League, La Liga, Serie A, Bundesliga, Champions League, and international tournaments. New challenges launch every day at 00:00 UTC with full streak statistics.",
            "Máximos Goleadores es un juego diario de trivia de fútbol de Playmaker que rinde homenaje a los goleadores más prolíficos y botas de oro de la historia del fútbol. Cada día se presenta una categoría goleadora específica, como los máximos goleadores históricos de un club, una temporada de Champions League o un torneo de Copa del Mundo. Los jugadores deben nombrar a los goleadores para descubrir las posiciones del ranking antes de quedarse sin vidas. Adivina los máximos goleadores históricos con seguimiento de rachas y nuevos retos a las 00:00 UTC."
        ),
        "club_connect": (
            "Club Connect is a daily football connection puzzle by Playmaker that challenges fans to deduce the secret club linking five mystery footballer signings. At the start of each daily game, five player cards are presented face-down, ranked in order of their transfer fee. One initial player is revealed immediately as a starting clue. Players submit club guesses to identify the mystery buyer before running out of lives. Every incorrect guess flips over the next player card to reveal additional transfer history, nationality, and position hints. Once the connection is discovered, players earn an efficiency score based on how few player clues they needed to crack the puzzle. Club Connect covers senior domestic and international transfers from 1990 to present, resetting daily at midnight UTC with streak tracking and shareable emoji summaries.",
            "Conexión de Clubes es un puzzle diario de conexiones de fútbol de Playmaker donde los jugadores descubren el club misterioso que fichó a cinco estrellas del fútbol. En cada paso se revela un nuevo futbolista fichado por el club secreto con su coste, año y posición. Los jugadores deducen el club de destino común utilizando el menor número posible de compañeros revelados. ¿Qué Club Fichó a los 5 Jugadores? Un fallo cuesta una vida y revela al siguiente compañero. ¡Descubre el club misterioso antes de quedarte sin vidas!"
        ),
        "player_chain": (
            "Player Chain is a daily football teammate connection challenge by Playmaker where players deduce a mystery Player of the Day through a sequential career chain. Starting from an anchor club, players advance through the chain by naming footballers who shared senior squad appearances across consecutive clubs. Each validated teammate guess confirms a transfer link and reveals progressive clues regarding the mystery player's nationality, primary position, and shirt number. Players can methodically climb each link in the ladder or attempt an instant-win guess if they recognize the final footballer early. The game features interactive VAR review for contested teammate rosters, comprehensive hint options, and local streak tracking across the Premier League, La Liga, Serie A, Bundesliga, and UEFA competitions. New career chains release daily at midnight UTC with full back-in-time archives.",
            "Cadena de Jugadores es un reto diario de conexiones entre compañeros de fútbol de Playmaker donde los jugadores deducen al Jugador Misterioso del Día a través de una cadena secuencial de clubes. Empezando por un club ancla, los jugadores avanzan nombrando futbolistas que compartieron vestuario en clubes consecutivos. ¡Juega a diario y mantén tu racha!"
        ),
        "passport_fc": (
            'Passport FC is a daily football trivia puzzle by Playmaker where fans collect nationality stamps for a featured anchor club. Each day highlights one world-famous club alongside four progressive nationality tiers. Players must name any qualifying footballer who made senior appearances or signed for that club while representing the designated nation. The puzzle begins with major footballing countries that have extensive talent pools before ascending to "The Unicorn" — an unexpected country with only one or two eligible players across the club\'s entire transfer history.',
            'Pasaporte FC es un puzzle diario de trivia de fútbol de Playmaker donde los fanáticos consiguen sellos de nacionalidad para un club ancla destacado. Cada día se presenta un club de renombre mundial junto a cuatro niveles progresivos de nacionalidad. Los jugadores deben nombrar a cualquier futbolista elegible que haya jugado en el primer equipo o fichado por dicho club representando a la nación indicada. El reto comienza con grandes potencias futbolísticas antes de ascender a "El Unicornio", un país insólito con solo uno o dos jugadores en toda la historia del club.'
        ),
    }
    for gid, (en_h, es_h) in how_to_play_paragraphs.items():
        es_html = es_html.replace(en_h, es_h)

    what_is_replacements = {
        "What is Top Transfers?": "¿Qué es Top Transfers?",
        "What is Transfer Destination?": "¿Qué es Reto de Trayectoria Deportiva?",
        "What is Top Scorers?": "¿Qué es Máximos Goleadores?",
        "What is Club Connect?": "¿Qué es Conexión de Clubes?",
        "What is Player Chain?": "¿Qué es Cadena de Jugadores?",
        "What is Passport FC?": "¿Qué es Pasaporte FC?",
    }
    for en_w, es_w in what_is_replacements.items():
        es_html = es_html.replace(en_w, es_w)

    # 7. Inject Spanish game note and language setter in JS data
    safe_note_es = game_cfg.get("note_es", "").replace('\\', '\\\\').replace('"', '\\"')
    if safe_note_es:
        es_html = re.sub(r'const GAME_NOTE = ".*";', f'const GAME_NOTE = "{safe_note_es}";', es_html)
    
    es_html = es_html.replace(
        'const MAX_BACK_DAYS',
        "if (typeof FootyI18n !== 'undefined') FootyI18n.setLang('es');\n        const MAX_BACK_DAYS"
    )

    return es_html


def load_schedule_ledger(ledger_path=LEDGER_FILE):
    """Loads pre-computed contextual puzzle schedule ledger if present."""
    if os.path.exists(ledger_path):
        try:
            with open(ledger_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Warning: Could not read schedule ledger ({e}). Falling back to linear modulo.")
    return {}


_CACHED_PROCESSED_CLUBS = None
_CACHED_PROCESSED_PLAYERS = None

def get_processed_all_clubs():
    global _CACHED_PROCESSED_CLUBS
    if _CACHED_PROCESSED_CLUBS is not None:
        return _CACHED_PROCESSED_CLUBS
    if not os.path.exists("all_clubs.json"):
        print("  WARNING: all_clubs.json not found.")
        _CACHED_PROCESSED_CLUBS = "[]"
        return _CACHED_PROCESSED_CLUBS
    try:
        with open("all_clubs.json", "r", encoding="utf-8") as f:
            raw_clubs = json.load(f)
        alias_cfg = load_aliases_config()
        filtered = filter_and_canonicalize_clubs(raw_clubs, alias_cfg, as_objects=True)
        _CACHED_PROCESSED_CLUBS = json.dumps(filtered, ensure_ascii=False)
    except Exception as e:
        print(f"  WARNING: Error processing all_clubs.json: {e}")
        _CACHED_PROCESSED_CLUBS = "[]"
    return _CACHED_PROCESSED_CLUBS


def get_processed_all_players():
    global _CACHED_PROCESSED_PLAYERS
    if _CACHED_PROCESSED_PLAYERS is not None:
        return _CACHED_PROCESSED_PLAYERS
    if not os.path.exists("all_players.json"):
        print("  WARNING: all_players.json not found.")
        _CACHED_PROCESSED_PLAYERS = "[]"
        return _CACHED_PROCESSED_PLAYERS
    try:
        with open("all_players.json", "r", encoding="utf-8") as f:
            raw_players = json.load(f)
        alias_cfg = load_aliases_config()
        filtered = filter_and_canonicalize_players(raw_players, alias_cfg)
        _CACHED_PROCESSED_PLAYERS = json.dumps(filtered, ensure_ascii=False)
    except Exception as e:
        print(f"  WARNING: Error processing all_players.json: {e}")
        _CACHED_PROCESSED_PLAYERS = "[]"
    return _CACHED_PROCESSED_PLAYERS


# ─────────────────────────────────────────────────────────────
# Game data loaders  (one function per game id)
# ─────────────────────────────────────────────────────────────
def load_top_transfers(puzzle_num):
    """Returns (game_data_dict, extra_data_dict) for the top_transfers game."""
    game_mode = "nationality" if puzzle_num % 2 == 0 else "club"
    game_data = {"mode": game_mode, "name": "", "transfers": []}

    if game_mode == "club":
        csv_path = "daily_transfer_games.csv"
        if not os.path.exists(csv_path):
            print(f"  ERROR: {csv_path} not found.")
            return None, None
        with open(csv_path, "r", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if int(r.get("game_day", 1)) == puzzle_num:
                    if not game_data["name"]:
                        game_data["name"] = r.get("selected_club", "")
                    game_data["transfers"].append({
                        "player_name":    r.get("player_name", ""),
                        "from_club_name": r.get("from_club_name", ""),
                        "to_club_name":   r.get("to_club_name", ""),
                        "transfer_fee":   r.get("transfer_fee", "0"),
                        "transfer_date":  r.get("transfer_date", ""),
                    })
    else:
        csv_path = "daily_nationality_transfer_games.csv"
        if not os.path.exists(csv_path):
            print(f"  ERROR: {csv_path} not found.")
            return None, None
        with open(csv_path, "r", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if int(r.get("game_day", 1)) == puzzle_num:
                    if not game_data["name"]:
                        game_data["name"] = r.get("selected_nationality", "")
                    game_data["transfers"].append({
                        "player_name":    r.get("player_name", ""),
                        "from_club_name": r.get("from_club_name", ""),
                        "to_club_name":   r.get("to_club_name", ""),
                        "transfer_fee":   r.get("transfer_fee", "0"),
                        "transfer_date":  r.get("transfer_date", ""),
                    })

    if not game_data["name"]:
        print(f"  WARNING: No top_transfers data for puzzle #{puzzle_num}")
        return None, None

    extra = {
        "ALL_PLAYERS": get_processed_all_players(),
    }
    return game_data, extra


def load_transfer_destination(puzzle_num):
    """Returns (game_data_dict, extra_data_dict) for the transfer_destination game."""
    game_data = {"player_name": "", "nationality": "", "position": "", "transfers": []}

    csv_path = "daily_destination_games.csv"
    if not os.path.exists(csv_path):
        print(f"  WARNING: {csv_path} not found.")
        return None, None

    alias_map = get_club_alias_map(load_aliases_config())
    day_rows = []

    with open(csv_path, "r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if int(r.get("game_day", 1)) == puzzle_num:
                if not game_data["player_name"]:
                    game_data["player_name"] = r.get("player_name", "")
                    game_data["nationality"]  = r.get("country_of_citizenship", "")
                    game_data["position"]     = r.get("position", "")
                day_rows.append(r)

    if not day_rows or not game_data["player_name"]:
        print(f"  WARNING: No transfer_destination data for puzzle #{puzzle_num}")
        return None, None

    cleaned_transfers = clean_career_transfers(day_rows, alias_map)
    for tr in cleaned_transfers:
        game_data["transfers"].append({
            "transfer_date":       tr.get("transfer_date_str", tr.get("transfer_date", "")),
            "from_club_name":      tr.get("from_club_name", ""),
            "to_club_name":        tr.get("to_club_name", ""),
            "transfer_fee":        float(tr.get("transfer_fee", 0.0) or 0.0),
            "market_value_in_eur": float(tr.get("market_value_in_eur", 0.0) or 0.0),
            "transfer_type":       tr.get("transfer_type", ""),
        })

    # Reverse transfers so the game runs from most recent club/transfer back to the first
    game_data["transfers"].reverse()

    extra = {
        "ALL_CLUBS": get_processed_all_clubs(),
    }
    return game_data, extra


def load_top_scorers(puzzle_num):
    """Returns (game_data_dict, extra_data_dict) for the top_scorers game."""
    game_data = {"name": "", "scorers": []}

    csv_path = "daily_scorers_games.csv"
    if not os.path.exists(csv_path):
        print(f"  ERROR: {csv_path} not found.")
        return None, None

    with open(csv_path, "r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if int(r.get("game_day", 1)) == puzzle_num:
                if not game_data["name"]:
                    game_data["name"] = r.get("selected_target", "")
                game_data["scorers"].append({
                    "player_name":  r.get("player_name", ""),
                    "club_name":    r.get("club_name", ""),
                    "goals":        int(float(r.get("goals", "0"))),
                    "appearances":  int(float(r.get("appearances", "0"))),
                    "nationality":  r.get("nationality", ""),
                })

    if not game_data["name"]:
        print(f"  WARNING: No top_scorers data for puzzle #{puzzle_num}")
        return None, None

    extra = {
        "ALL_PLAYERS": get_processed_all_players(),
    }
    return game_data, extra


def load_club_connect(puzzle_num):
    """Returns (game_data_dict, extra_data_dict) for the club_connect game."""
    csv_path = "daily_transfer_games.csv"
    if not os.path.exists(csv_path):
        print(f"  ERROR: {csv_path} not found.")
        return None, None

    all_rows = []
    answer_clubs = set()
    with open(csv_path, "r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            answer_clubs.add(r.get("selected_club", ""))
            if int(r.get("game_day", 1)) == puzzle_num:
                all_rows.append(r)

    if not all_rows:
        print(f"  WARNING: No club_connect data for puzzle #{puzzle_num}")
        return None, None

    # Sort ascending by fee → cheapest (most obscure) signing revealed first
    all_rows.sort(key=lambda r: float(r.get("transfer_fee", 0) or 0))

    club = all_rows[0].get("selected_club", "")
    players = [{
        "player_name":    r.get("player_name", ""),
        "from_club_name": r.get("from_club_name", ""),
        "transfer_fee":   float(r.get("transfer_fee", 0) or 0),
        "transfer_date":  r.get("transfer_date", ""),
    } for r in all_rows[:5]]

    game_data = {"club": club, "players": players}
    sorted_clubs = sorted(answer_clubs - {""})
    extra = {
        "ALL_CLUBS": get_processed_all_clubs(),
        "ANSWER_CLUBS": json.dumps(sorted_clubs, ensure_ascii=False),
    }
    return game_data, extra


def load_player_chain(puzzle_num):
    """Returns (game_data_dict, extra_data_dict) for the player_chain game."""
    csv_path = "daily_player_chain_games.csv"
    if not os.path.exists(csv_path):
        print(f"  ERROR: {csv_path} not found.")
        return None, None

    rows = []
    with open(csv_path, "r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if int(r.get("game_day", 1)) == puzzle_num:
                rows.append(r)

    if not rows:
        print(f"  WARNING: No player_chain data for puzzle #{puzzle_num}")
        return None, None

    rows.sort(key=lambda x: int(x.get("step_number", 1)))
    first = rows[0]

    game_data = {
        "target_player":     first.get("target_player", ""),
        "target_nationality": first.get("target_nationality", ""),
        "target_position":    first.get("target_position", ""),
        "total_steps":        int(first.get("total_steps", len(rows))),
        "steps": []
    }

    for r in rows:
        game_data["steps"].append({
            "step_number":        int(r.get("step_number", 1)),
            "new_constraint":     r.get("new_constraint", ""),
            "club":               r.get("club", ""),
            "active_constraints": json.loads(r.get("active_constraints", "[]")),
            "active_clubs":       json.loads(r.get("active_clubs", "[]")),
            "valid_players":      json.loads(r.get("valid_players", "[]")),
        })

    # Extra data: all players list for dropdown autocomplete
    extra = {
        "ALL_PLAYERS": get_processed_all_players(),
    }
    return game_data, extra


def _dedupe_canonical_names(names):
    if not isinstance(names, list):
        return []
    seen = {}
    for name in names:
        if not name or not isinstance(name, str):
            continue
        clean_name = re.sub(r'[\u200b-\u200f\u202a-\u202e\ufeff]', '', name).strip()
        s = clean_name.replace('ð', 'd').replace('Ð', 'D').replace('þ', 'th').replace('Þ', 'Th')
        s = s.replace('ø', 'o').replace('Ø', 'O').replace('ł', 'l').replace('Ł', 'L')
        s = s.replace('đ', 'd').replace('Đ', 'D').replace('æ', 'ae').replace('Æ', 'Ae')
        s = s.replace('œ', 'oe').replace('Œ', 'Oe').replace('ß', 'ss')
        norm = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn').strip().lower()
        if norm not in seen:
            seen[norm] = clean_name
        else:
            if clean_name != norm and seen[norm] == norm:
                seen[norm] = clean_name
    return list(seen.values())


def load_passport_fc(puzzle_num):
    """Returns (game_data_dict, extra_data_dict) for the passport_fc game."""
    csv_path = "daily_passport_fc_games.csv"
    if not os.path.exists(csv_path):
        print(f"  ERROR: {csv_path} not found.")
        return None, None

    rows = []
    with open(csv_path, "r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if int(r.get("game_day", 1)) == puzzle_num:
                rows.append(r)

    if not rows:
        print(f"  WARNING: No passport_fc data for puzzle #{puzzle_num}")
        return None, None

    rows.sort(key=lambda x: int(x.get("step_number", 1)))
    first = rows[0]

    game_data = {
        "club": first.get("club", ""),
        "total_steps": int(first.get("total_steps", len(rows))),
        "steps": []
    }

    for r in rows:
        v_players = _dedupe_canonical_names(json.loads(r.get("valid_players", "[]")))
        s_players = _dedupe_canonical_names(json.loads(r.get("sample_players", "[]")))
        p_size = len(v_players) if v_players else int(r.get("pool_size", 0))
        game_data["steps"].append({
            "step_number":    int(r.get("step_number", 1)),
            "difficulty":     r.get("difficulty", ""),
            "nationality":    r.get("nationality", ""),
            "pool_size":      p_size,
            "sample_players": s_players,
            "valid_players":  v_players,
        })

    extra = {
        "ALL_PLAYERS": get_processed_all_players(),
    }
    return game_data, extra


# Map game id → loader function
GAME_LOADERS = {
    "top_transfers":        load_top_transfers,
    "transfer_destination": load_transfer_destination,
    "top_scorers":          load_top_scorers,
    "club_connect":         load_club_connect,
    "player_chain":         load_player_chain,
    "passport_fc":          load_passport_fc,
}

# Map game id → the JS variable name for the main data object
GAME_DATA_VAR = {
    "top_transfers":        "DAILY_TRANSFER_GAME",
    "transfer_destination": "DAILY_DESTINATION_GAME",
    "top_scorers":          "DAILY_SCORERS_GAME",
    "club_connect":         "DAILY_CLUBCONNECT_GAME",
    "player_chain":         "DAILY_CHAIN_GAME",
    "passport_fc":          "DAILY_PASSPORT_GAME",
}

# Patterns to strip from a template before injecting fresh data
STRIP_PATTERNS = {
    "top_transfers": [
        r'const\s+DAILY_TRANSFER_GAME\s*=\s*\{[\s\S]*?\};',
        r'const\s+ALL_PLAYERS\s*=\s*\[[\s\S]*?\];',
        r'const\s+PUZZLE_NUMBER\s*=\s*\d+;',
        r'const\s+IS_BACK_IN_TIME\s*=\s*(true|false);',
        r'const\s+MAX_BACK_DAYS\s*=\s*\d+;',
        r'const\s+GAME_NOTE\s*=\s*"[^"]*";',
    ],
    "transfer_destination": [
        r'const\s+DAILY_DESTINATION_GAME\s*=\s*\{[\s\S]*?\};',
        r'const\s+ALL_CLUBS\s*=\s*\[[\s\S]*?\];',
        r'const\s+PUZZLE_NUMBER\s*=\s*\d+;',
        r'const\s+IS_BACK_IN_TIME\s*=\s*(true|false);',
        r'const\s+MAX_BACK_DAYS\s*=\s*\d+;',
        r'const\s+GAME_NOTE\s*=\s*"[^"]*";',
    ],
    "top_scorers": [
        r'const\s+DAILY_SCORERS_GAME\s*=\s*\{[\s\S]*?\};',
        r'const\s+ALL_PLAYERS\s*=\s*\[[\s\S]*?\];',
        r'const\s+PUZZLE_NUMBER\s*=\s*\d+;',
        r'const\s+IS_BACK_IN_TIME\s*=\s*(true|false);',
        r'const\s+MAX_BACK_DAYS\s*=\s*\d+;',
        r'const\s+GAME_NOTE\s*=\s*"[^"]*";',
    ],
    "club_connect": [
        r'const\s+DAILY_CLUBCONNECT_GAME\s*=\s*\{[\s\S]*?\};',
        r'const\s+ALL_CLUBS\s*=\s*\[[\s\S]*?\];',
        r'const\s+ANSWER_CLUBS\s*=\s*\[[\s\S]*?\];',
        r'const\s+PUZZLE_NUMBER\s*=\s*\d+;',
        r'const\s+IS_BACK_IN_TIME\s*=\s*(true|false);',
        r'const\s+MAX_BACK_DAYS\s*=\s*\d+;',
        r'const\s+GAME_NOTE\s*=\s*"[^"]*";',
    ],
    "player_chain": [
        r'const\s+DAILY_CHAIN_GAME\s*=\s*\{[\s\S]*?\};',
        r'const\s+ALL_PLAYERS\s*=\s*\[[\s\S]*?\];',
        r'const\s+PUZZLE_NUMBER\s*=\s*\d+;',
        r'const\s+IS_BACK_IN_TIME\s*=\s*(true|false);',
        r'const\s+MAX_BACK_DAYS\s*=\s*\d+;',
        r'const\s+GAME_NOTE\s*=\s*"[^"]*";',
    ],
    "passport_fc": [
        r'const\s+DAILY_PASSPORT_GAME\s*=\s*\{[\s\S]*?\};',
        r'const\s+ALL_PLAYERS\s*=\s*\[[\s\S]*?\];',
        r'const\s+PUZZLE_NUMBER\s*=\s*\d+;',
        r'const\s+IS_BACK_IN_TIME\s*=\s*(true|false);',
        r'const\s+MAX_BACK_DAYS\s*=\s*\d+;',
        r'const\s+GAME_NOTE\s*=\s*"[^"]*";',
    ],
}


# ─────────────────────────────────────────────────────────────
# Core compiler
# ─────────────────────────────────────────────────────────────
def compile_game(game_cfg, puzzle_num, day_offset=0, max_back_days=7, content_puzzle_id=None):
    """
    Compile a single game HTML for a given puzzle_num.
    day_offset=0 → today's file (game_id.html)
    day_offset=1 → yesterday's file (game_id_d1.html)
    etc.
    puzzle_num: The chronological user-facing puzzle number (e.g. PUZZLE #47).
    content_puzzle_id: The specific dataset row ID to load. If None, defaults to puzzle_num.
    """
    game_id       = game_cfg["id"]
    template_file = game_cfg.get("templateFile", f"{game_id}_template.html")
    template_path = os.path.join(TEMPLATES_DIR, template_file)
    game_note     = game_cfg.get("note", "")

    if not os.path.exists(template_path):
        print(f"  ERROR: template not found: {template_path}")
        return False

    loader = GAME_LOADERS.get(game_id)
    if not loader:
        print(f"  ERROR: no loader registered for game id '{game_id}'")
        return False

    content_id = content_puzzle_id if content_puzzle_id is not None else puzzle_num
    game_data, extra = loader(content_id)
    if game_data is None:
        return False

    with open(template_path, "r", encoding="utf-8") as f:
        html = f.read()

    # Strip any previously injected data
    for pattern in STRIP_PATTERNS.get(game_id, []):
        html = re.sub(pattern, '', html)

    is_back_in_time = day_offset > 0
    data_var_name   = GAME_DATA_VAR.get(game_id, "DAILY_GAME")

    # Build injection block
    extra_lines = []
    for var_name, json_str in (extra or {}).items():
        extra_lines.append(f"        const {var_name} = {json_str};")

    # Inject game note (escaped for JS string)
    safe_note = game_note.replace('\\', '\\\\').replace('"', '\\"')
    extra_lines.append(f'        const GAME_NOTE = "{safe_note}";')

    injection = f"""
    <script id="daily-game-data">
        const {data_var_name} = {json.dumps(game_data, ensure_ascii=False)};
{chr(10).join(extra_lines)}
        const PUZZLE_NUMBER    = {puzzle_num};
        const IS_BACK_IN_TIME  = {'true' if is_back_in_time else 'false'};
        const MAX_BACK_DAYS    = {max_back_days};
    </script>
    """

    # Inject before the game-specific script (marker comment)
    marker = "<!-- Micro-interaction Script -->"
    if marker in html:
        compiled = html.replace(marker, injection + "\n" + marker)
    else:
        compiled = html.replace("</body>", injection + "\n</body>")

    # Determine output filename
    if day_offset == 0:
        out_name = f"{game_id}.html"
    else:
        out_name = f"{game_id}_d{day_offset}.html"

    # Write English version
    out_path = os.path.join(OUTPUT_DIR, out_name)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(compiled)

    # Write Spanish version
    es_compiled = localize_for_spanish(compiled, game_cfg, puzzle_num, is_back_in_time)
    es_out_path = os.path.join(ES_OUTPUT_DIR, out_name)
    os.makedirs(ES_OUTPUT_DIR, exist_ok=True)
    with open(es_out_path, "w", encoding="utf-8") as f:
        f.write(es_compiled)

    back_label = f" (back-in-time d{day_offset})" if is_back_in_time else ""
    print(f"  ✓ {out_path} & {es_out_path}  [puzzle #{puzzle_num}{back_label}]")
    return True


# ─────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Playmaker Game Compiler")
    parser.add_argument("--offset",        type=int,   default=0,  help="Offset today's date by N days.")
    parser.add_argument("--puzzle",        type=int,   default=0,  help="Force a specific puzzle index (1-indexed).")
    parser.add_argument("--random",        action="store_true",    help="Compile a random puzzle.")
    parser.add_argument("--max-back-days", type=int,   default=7,  help="Number of past days to compile (default 7).")
    parser.add_argument("--game",          type=str,   default="", help="Compile only this game id (default: all).")
    args = parser.parse_args()

    # Load games registry
    if not os.path.exists(GAMES_JSON):
        print(f"ERROR: {GAMES_JSON} not found.")
        return

    with open(GAMES_JSON, "r", encoding="utf-8") as f:
        games = json.load(f)

    if args.game:
        games = [g for g in games if g["id"] == args.game]
        if not games:
            print(f"ERROR: Game id '{args.game}' not found in {GAMES_JSON}.")
            return

    # Base default launch date: 2026-07-27 is Day 1 (Puzzle #1)
    DEFAULT_LAUNCH_DATE = datetime(2026, 7, 27)
    schedule_ledger = load_schedule_ledger()
    if schedule_ledger:
        print(f"📖 Loaded schedule ledger ({len(schedule_ledger)} dates mapped)")

    # Determine (chronological_puzzle_num, content_puzzle_id) for target date and game
    def puzzle_for_offset(off, launch_date_str="", game_id=""):
        target_date = datetime.today() + timedelta(days=args.offset - off)
        date_str = target_date.strftime("%Y-%m-%d")
        today_str = datetime.today().strftime("%Y-%m-%d")

        if args.random:
            rand_p = rand_mod.randint(1, TOTAL_DAYS)
            return rand_p, rand_p
        if args.puzzle > 0:
            p = args.puzzle - off
            if p < 1:
                return None, None
            return p, p

        # 1. Chronological puzzle number (always strictly linear by days from launch)
        launch_dt = datetime.strptime(launch_date_str, "%Y-%m-%d") if launch_date_str else DEFAULT_LAUNCH_DATE
        days_diff = (target_date.date() - launch_dt.date()).days
        if days_diff < 0:
            return None, None
        chrono_pnum = (days_diff % TOTAL_DAYS) + 1

        # 2. Content puzzle ID:
        # For past and today (date_str <= today_str): strictly maintain historical puzzle content.
        # For future dates (date_str > today_str): pull contextual matchday / rotation from schedule ledger.
        content_id = chrono_pnum
        if date_str > today_str and schedule_ledger and date_str in schedule_ledger:
            ledger_content = schedule_ledger[date_str].get("puzzles", {}).get(game_id)
            if ledger_content is not None:
                content_id = ledger_content

        return chrono_pnum, content_id

    max_back = args.max_back_days

    print(f"\n=== Playmaker Compiler — {datetime.today().strftime('%Y-%m-%d')} ===")
    print(f"Compiling {len(games)} game(s), today + {max_back} back-in-time days\n")

    for game_cfg in games:
        gid = game_cfg["id"]

        # Skip games not yet ready unless explicitly requested via --game
        if game_cfg.get("status") == "coming_soon" and not args.game:
            print(f"── {game_cfg['name']} ({gid}) — SKIPPED (coming soon)\n")
            continue

        print(f"── {game_cfg['name']} ({gid}) ──")

        # Today (offset 0)
        g_launch = game_cfg.get("launchDate", "")
        pnum_today, content_today = puzzle_for_offset(0, g_launch, game_id=gid)
        if pnum_today is not None:
            compile_game(game_cfg, pnum_today, day_offset=0, max_back_days=max_back, content_puzzle_id=content_today)

        # Back-in-time files
        for d in range(1, max_back + 1):
            pnum_past, content_past = puzzle_for_offset(d, g_launch, game_id=gid)
            if pnum_past is None:
                out_name = f"{gid}_d{d}.html"
                out_path = os.path.join(OUTPUT_DIR, out_name)
                if os.path.exists(out_path):
                    os.remove(out_path)
                es_out_path = os.path.join(ES_OUTPUT_DIR, out_name)
                if os.path.exists(es_out_path):
                    os.remove(es_out_path)
                continue
            compile_game(game_cfg, pnum_past, day_offset=d, max_back_days=max_back, content_puzzle_id=content_past)

        print()

    print("=== Compilation complete ===\n")


if __name__ == "__main__":
    main()
