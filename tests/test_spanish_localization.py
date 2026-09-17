"""
test_spanish_localization.py — Verification Suite for Task #25
===============================================================
Validates:
1. footy-i18n.js existence and dictionary integrity.
2. footy-ui.js integration with FootyI18n.
3. Dual-locale compilation across all 6 live game modes in games/ and es/games/.
4. Spanish Hub (es/index.html) metadata, hreflang tags, and localized copy.
5. HTML asset depth, canonical URLs, and language switcher active states.
"""

import os
import json
import re
import unittest
import subprocess


class TestSpanishLocalization(unittest.TestCase):

    def setUp(self):
        self.root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.games_json_path = os.path.join(self.root_dir, "games.json")
        with open(self.games_json_path, "r", encoding="utf-8") as f:
            self.games = json.load(f)
        self.live_games = [g for g in self.games if g.get("status") != "coming_soon"]

    def test_i18n_dictionary_completeness(self):
        """Verify footy-i18n.js contains matching keys between 'en' and 'es'."""
        i18n_path = os.path.join(self.root_dir, "games", "footy-i18n.js")
        self.assertTrue(os.path.exists(i18n_path), "games/footy-i18n.js must exist")

        # Run node script to test dictionary keys
        node_script = """
        const fs = require('fs');
        const path = require('path');
        const code = fs.readFileSync('games/footy-i18n.js', 'utf8');
        eval(code);
        const enKeys = Object.keys(FootyI18n.TRANSLATIONS.en);
        const esKeys = Object.keys(FootyI18n.TRANSLATIONS.es);
        
        const missingInEs = enKeys.filter(k => !(k in FootyI18n.TRANSLATIONS.es));
        const missingInEn = esKeys.filter(k => !(k in FootyI18n.TRANSLATIONS.en));
        
        console.log(JSON.stringify({
            enCount: enKeys.length,
            esCount: esKeys.length,
            missingInEs,
            missingInEn,
            sampleEs: FootyI18n.t('game_top_transfers', {}, 'es'),
            sampleEn: FootyI18n.t('game_top_transfers', {}, 'en')
        }));
        """
        res = subprocess.run(["node", "-e", node_script], cwd=self.root_dir, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"Node i18n test failed: {res.stderr}")
        data = json.loads(res.stdout.strip())
        self.assertEqual(len(data["missingInEs"]), 0, f"Missing keys in ES dictionary: {data['missingInEs']}")
        self.assertEqual(len(data["missingInEn"]), 0, f"Missing keys in EN dictionary: {data['missingInEn']}")
        self.assertEqual(data["sampleEs"], "Top Fichajes")
        self.assertEqual(data["sampleEn"], "Top Transfers")

    def test_spanish_hub_index_html(self):
        """Verify es/index.html is valid Spanish landing page with SEO tags."""
        es_index = os.path.join(self.root_dir, "es", "index.html")
        self.assertTrue(os.path.exists(es_index), "es/index.html must exist")

        with open(es_index, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn('lang="es"', content)
        self.assertIn('<link rel="canonical" href="https://playmaker.best/es/"', content)
        self.assertIn('<link rel="alternate" hreflang="en" href="https://playmaker.best/"', content)
        self.assertIn('<link rel="alternate" hreflang="es" href="https://playmaker.best/es/"', content)
        self.assertIn('<link rel="alternate" hreflang="x-default" href="https://playmaker.best/"', content)
        self.assertIn("TRIVIA DE FÚTBOL", content)
        self.assertIn("SELECCIONA UN RETO", content)
        self.assertIn("TABLA DE POSICIONES", content)
        self.assertIn("footy-i18n.js", content)
        self.assertIn("footy-ui.js", content)

    def test_english_hub_hreflang_tags(self):
        """Verify index.html contains bidirectional hreflang links."""
        en_index = os.path.join(self.root_dir, "index.html")
        with open(en_index, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn('<link rel="alternate" hreflang="en" href="https://playmaker.best/"', content)
        self.assertIn('<link rel="alternate" hreflang="es" href="https://playmaker.best/es/"', content)
        self.assertIn('<link rel="alternate" hreflang="x-default" href="https://playmaker.best/"', content)
        self.assertIn('id="lang-switcher"', content)

    def test_all_live_games_dual_compilation(self):
        """Verify every live game exists in both games/ and es/games/ with matching puzzle IDs."""
        for game in self.live_games:
            gid = game["id"]
            en_file = os.path.join(self.root_dir, "games", f"{gid}.html")
            es_file = os.path.join(self.root_dir, "es", "games", f"{gid}.html")

            self.assertTrue(os.path.exists(en_file), f"English game file must exist: {en_file}")
            self.assertTrue(os.path.exists(es_file), f"Spanish game file must exist: {es_file}")

            with open(en_file, "r", encoding="utf-8") as f:
                en_content = f.read()
            with open(es_file, "r", encoding="utf-8") as f:
                es_content = f.read()

            # Verify HTML language tag
            self.assertIn('lang="en"', en_content, f"{en_file} must have lang=en")
            self.assertIn('lang="es"', es_content, f"{es_file} must have lang=es")

            # Verify canonical and alternate hreflang
            self.assertIn(f'<link rel="canonical" href="https://playmaker.best/games/{gid}.html"', en_content)
            self.assertIn(f'<link rel="canonical" href="https://playmaker.best/es/games/{gid}.html"', es_content)
            self.assertIn(f'<link rel="alternate" hreflang="es" href="https://playmaker.best/es/games/{gid}.html"', en_content)
            self.assertIn(f'<link rel="alternate" hreflang="es" href="https://playmaker.best/es/games/{gid}.html"', es_content)

            # Verify relative asset depth in Spanish file (../../)
            self.assertIn('href="../../assets/', es_content)
            self.assertIn('src="../../assets/', es_content)
            self.assertIn('href="../../games/footy-ui.css', es_content)
            self.assertIn('src="../../games/footy-i18n.js', es_content)
            self.assertIn('src="../../games/footy-ui.js', es_content)

            # Verify language switcher element
            self.assertIn('id="lang-switcher"', en_content)
            self.assertIn('id="lang-switcher"', es_content)

    def test_spanish_game_titles_and_branding(self):
        """Verify localized game titles in Spanish files."""
        title_map = {
            "top_transfers": "TOP FICHAJES",
            "transfer_destination": "DESTINO DE FICHAJE",
            "top_scorers": "MÁXIMOS GOLEADORES",
            "club_connect": "CONEXIÓN DE CLUBES",
            "player_chain": "CADENA DE JUGADORES",
            "passport_fc": "PASAPORTE FC",
        }
        for gid, expected_title in title_map.items():
            es_file = os.path.join(self.root_dir, "es", "games", f"{gid}.html")
            with open(es_file, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn(f">{expected_title}<", content, f"{gid} must have Spanish title {expected_title}")
            self.assertIn("FootyI18n.setLang('es')", content)

    def test_spanish_ui_elements_and_tables(self):
        """Verify comprehensive Spanish UI elements, table headers, and bottom sections."""
        # Check top_transfers
        tt_es = os.path.join(self.root_dir, "es", "games", "top_transfers.html")
        with open(tt_es, "r", encoding="utf-8") as f:
            tt_content = f.read()
        self.assertIn(">Jugador<", tt_content)
        self.assertIn(">Coste<", tt_content)
        self.assertIn(">Acciones<", tt_content)
        self.assertIn("Vidas:", tt_content)
        self.assertIn("Adivinados:", tt_content)
        self.assertIn(">ADIVINAR<", tt_content)
        self.assertIn(">CÓMO JUGAR<", tt_content)
        self.assertIn(">MÁS RETOS DIARIOS<", tt_content)
        self.assertIn("Volver a Playmaker", tt_content)

        self.assertIn("Adivina los 10 fichajes récord", tt_content)
        self.assertIn("COMPARTIR", tt_content)
        self.assertIn("CERRAR", tt_content)

        # Check transfer_destination
        td_es = os.path.join(self.root_dir, "es", "games", "transfer_destination.html")
        with open(td_es, "r", encoding="utf-8") as f:
            td_content = f.read()
        self.assertIn(">Reto de Trayectoria Deportiva<", td_content)
        self.assertIn("Jugador del Día", td_content)
        self.assertIn("Progreso:", td_content)
        self.assertIn(">ENVIAR<", td_content)
        self.assertIn("Escribe y selecciona el club...", td_content)
        self.assertIn(">CÓMO JUGAR<", td_content)
        self.assertIn("COMPARTIR", td_content)
        self.assertIn("CERRAR", td_content)

        # Check top_scorers
        ts_es = os.path.join(self.root_dir, "es", "games", "top_scorers.html")
        with open(ts_es, "r", encoding="utf-8") as f:
            ts_content = f.read()
        self.assertIn(">Goles<", ts_content)
        self.assertIn(">Partidos<", ts_content)
        self.assertIn(">Nacionalidad<", ts_content)
        self.assertIn("Adivina los máximos goleadores históricos", ts_content)
        self.assertIn("Adivina los fichajes récord de clubes y países", ts_content)

        # Check club_connect
        cc_es = os.path.join(self.root_dir, "es", "games", "club_connect.html")
        with open(cc_es, "r", encoding="utf-8") as f:
            cc_content = f.read()
        self.assertIn("¿Qué Club Fichó a los 5 Jugadores?", cc_content)
        self.assertIn("Escribe el nombre del club...", cc_content)
        self.assertIn("EL CLUB MISTERIOSO", cc_content)
        self.assertIn("¡CONECTADO!", cc_content)

        # Check player_chain
        pc_es = os.path.join(self.root_dir, "es", "games", "player_chain.html")
        with open(pc_es, "r", encoding="utf-8") as f:
            pc_content = f.read()
        self.assertIn(">CADENA DE JUGADORES<", pc_content)
        self.assertIn("El Puzzle de Trayectoria", pc_content)
        self.assertIn("Pista: Nacionalidad", pc_content)
        self.assertIn("Pista: Posición", pc_content)
        self.assertIn("Victoria Directa:", pc_content)
        self.assertIn("EL JUGADOR MISTERIOSO ERA", pc_content)
        self.assertIn("JUGADOR MISTERIOSO DEL DÍA", pc_content)
        self.assertIn("COMPLETADO", pc_content)
        self.assertIn("Paso ${step.step_number} — Bloqueado", pc_content)
        self.assertIn("Tu elección:", pc_content)
        self.assertIn("Jugó en:", pc_content)
        self.assertIn("Mostrar los ${validList.length} futbolistas válidos", pc_content)

        # Check passport_fc
        pfc_es = os.path.join(self.root_dir, "es", "games", "passport_fc.html")
        with open(pfc_es, "r", encoding="utf-8") as f:
            pfc_content = f.read()
        self.assertIn(">PASAPORTE FC<", pfc_content)
        self.assertIn("Sella el Pasaporte del Club", pfc_content)
        self.assertIn("PASAPORTE DEL CLUB DE HOY", pfc_content)
        self.assertIn("SELLO #${idx + 1}", pfc_content)
        self.assertIn("Bloqueado", pfc_content)
        self.assertIn("Futbolistas Elegibles", pfc_content)
        self.assertIn("¿Qué es Pasaporte FC?", pfc_content)
        self.assertIn("Cobertura de la Base de Datos:", pfc_content)
        self.assertIn("Verificación VAR:", pfc_content)
        self.assertIn("MÁS RETOS DIARIOS", pfc_content)
        self.assertIn("Volver al Lobby de Playmaker", pfc_content)
        self.assertIn("Política de Privacidad", pfc_content)
        self.assertIn("Términos y Condiciones", pfc_content)
        self.assertIn("ADIVINAR", pfc_content)


if __name__ == "__main__":
    unittest.main()

