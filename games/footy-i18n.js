/**
 * footy-i18n.js — Playmaker Internationalization (i18n) Engine
 *
 * Provides bilingual support (English & Spanish) for UI copy, game names,
 * toasts, end-game modals, share cards, and navigation.
 */

(function (global) {
    'use strict';

    const TRANSLATIONS = {
        en: {
            locale_name: 'English',
            locale_short: 'EN',
            switch_to: 'Español',

            // Brand & Navigation
            brand_tagline: "The Football Fan's Daily Arcade",
            daily_arcade: 'DAILY ARCADE',
            all_games: 'All Games',
            home: 'Home',
            prev: 'Prev',
            next: 'Next',
            puzzle: 'PUZZLE',
            back_in_time: 'Play Past Puzzles',
            arcade_standings: 'ARCADE STANDINGS',
            played: 'Played',
            wins: 'Wins',
            win_pct: 'Win %',
            streak: 'Streak',
            best_streak: 'Best Streak',
            feedback: 'Feedback',
            sound_on: 'Sound On',
            sound_off: 'Sound Off',
            share: 'Share',
            share_whatsapp: 'Share via WhatsApp',
            copy_result: 'Copy Result',
            copied_toast: 'Result copied to clipboard! 📋',
            link_copied: 'Link copied to clipboard! 📋',

            // Game Names
            game_top_transfers: 'Top Transfers',
            game_transfer_destination: 'Transfer Destination',
            game_top_scorers: 'Top Scorers',
            game_club_connect: 'Club Connect',
            game_player_chain: 'Player Chain',
            game_passport_fc: 'Passport FC',
            game_this_and_that: 'This & That',
            game_anyone_but: 'Anyone But',

            // More Daily Challenges suggestions
            more_daily_challenges: 'MORE DAILY CHALLENGES',
            tagline_top_transfers: 'Guess the record signings',
            tagline_transfer_destination: "Guess a player's career path",
            tagline_top_scorers: 'Name the top goalscorers',
            tagline_club_connect: '5 players, 1 club signed them all',
            tagline_player_chain: 'Connect consecutive clubs through shared teammates',
            tagline_passport_fc: 'Collect nationality stamps for a mystery club',
            badge_solved: 'SOLVED ✅',
            badge_failed: 'FAILED ❌',
            badge_played: 'FAILED ❌',
            back_to_playmaker: '← Back to Playmaker',

            // Common Gameplay
            lives: 'Lives',
            guessed: 'Guessed',
            guess: 'GUESS',
            submit: 'SUBMIT',
            give_up: 'Give Up',
            give_up_confirm: 'Are you sure you want to give up this match? Your current score will be recorded.',
            confirm_yes: 'Yes, End Match',
            confirm_no: 'Keep Playing',
            skip: 'Skip',
            hint: 'Hint',
            hints: 'Hints',
            free_hint: 'Free Hint',
            var_review: 'VAR Check',
            appeal_var: 'Appeal to VAR',
            var_checking: 'VAR Review in Progress...',
            var_success: 'VAR OVERRULED: Answer is Correct! +1 Life Restored 📺⚽',
            var_failed: 'VAR CONFIRMED: Ruling on Pitch Stands ❌',
            placeholder_player: 'Type and select player name...',
            placeholder_club: 'Type and select club name...',
            placeholder_general: 'Search name...',
            no_matches: 'No matching players found',
            no_matches_club: 'No matching clubs found',

            // Toasts & Messages
            toast_already_guessed: '"{name}" was already guessed!',
            toast_already_tried: '"{name}" was already attempted!',
            toast_invalid_selection: 'Please select an option from the dropdown list.',
            toast_wrong_guess: 'Wrong guess! -1 Life',
            toast_correct_guess: 'Correct! {name}',
            toast_life_lost: '-1 Life',
            toast_life_added: '+1 Life! ❤️',
            toast_hint_revealed: 'Hint revealed! 💡',
            toast_out_of_lives: 'Out of lives! Final score recorded.',

            // Modal & Outcomes
            outcome_win_title: 'COMPLETED!',
            outcome_perfect_title: 'MASTERMIND!',
            outcome_partial_title: 'GRITTY FINISH!',
            outcome_loss_title: 'GAME OVER',
            outcome_partial_default_msg: 'You reached the final whistle! Score: {score}/{maxScore}. Not a clean sheet, but a resilient shift.',
            outcome_loss_default_msg: 'Out of lives! Better luck tomorrow.',
            next_puzzle_in: 'Next puzzle in',
            score: 'Score',

            // Share Card Titles & Descriptions
            share_header: 'Playmaker',
            share_challenge: 'Can you beat my score?',
            share_all_found: '🏆 ALL {maxScore} FOUND! · ❤️ {lives} left',
            share_board_cleared: '🎖️ BOARD CLEARED! · {score}/{maxScore} found · ❤️ {lives} left',
            share_transfers_found: '🎯 {score}/{maxScore} found · ❤️ {lives} left',
            share_career_completed: '🌟 CAREER PATH COMPLETED! · ❤️ {lives} left',
            share_career_survived: '🎖️ CAREER SURVIVED! · {score}/{maxScore} clubs guessed backwards · ❤️ {lives} left',
            share_career_score: '🎯 {score}/{maxScore} clubs guessed backwards · ❤️ {lives} left',
            share_connected_in: '✨ CONNECTED IN {score} REVEAL{plural}! · ❤️ {lives} left',
            share_connected_missed: '❌ Connection Missed · 💔 Out of lives',
            share_chain_instant: '⭐️ INSTANT WIN! · 🎯 1-step direct connection!',
            share_chain_solved: '🔗 CHAIN SOLVED! · 🏆 Reached {target}! ({score}/{maxScore} steps) · ❤️ {lives} left',
            share_chain_partial: '🎖️ REACHED {target}! · {score}/{maxScore} steps · ❤️ {lives} left',
            share_chain_broke: '💔 CHAIN BROKE · {score}/{maxScore} steps before falling',
            share_passport_completed: '🛂 PASSPORT STAMPED! · 🏆 4/4 Nationalities Solved! · ❤️ {lives} left',
            share_passport_partial: '🎖️ IMMIGRATION PASSED! · {score}/4 Stamps Unlocked · ❤️ {lives} left',
            share_passport_loss: '⛔ VISA DENIED · {score}/4 Stamps Unlocked',
        },
        es: {
            locale_name: 'Español',
            locale_short: 'ES',
            switch_to: 'English',

            // Brand & Navigation
            brand_tagline: 'El Arcade Diario Para Fanáticos del Fútbol',
            daily_arcade: 'ARCADE DIARIO',
            all_games: 'Todos los Juegos',
            home: 'Inicio',
            prev: 'Anterior',
            next: 'Siguiente',
            puzzle: 'PUZZLE',
            back_in_time: 'Puzzles Anteriores',
            arcade_standings: 'TABLA DE POSICIONES',
            played: 'Jugadas',
            wins: 'Victorias',
            win_pct: '% Victoria',
            streak: 'Racha',
            best_streak: 'Mejor Racha',
            feedback: 'Comentarios',
            sound_on: 'Sonido Activado',
            sound_off: 'Sonido Desactivado',
            share: 'Compartir',
            share_whatsapp: 'Compartir por WhatsApp',
            copy_result: 'Copiar Resultado',
            copied_toast: '¡Resultado copiado al portapapeles! 📋',
            link_copied: '¡Enlace copiado al portapapeles! 📋',

            // Game Names
            game_top_transfers: 'Top Fichajes',
            game_transfer_destination: 'Destino de Fichaje',
            game_top_scorers: 'Máximos Goleadores',
            game_club_connect: 'Conexión de Clubes',
            game_player_chain: 'Cadena de Jugadores',
            game_passport_fc: 'Pasaporte FC',
            game_this_and_that: 'Esto y Aquello',
            game_anyone_but: 'Cualquiera Menos',

            // More Daily Challenges suggestions
            more_daily_challenges: 'MÁS DESAFÍOS DIARIOS',
            tagline_top_transfers: 'Adivina los fichajes récord',
            tagline_transfer_destination: 'Adivina la trayectoria de un jugador',
            tagline_top_scorers: 'Nombra a los máximos goleadores',
            tagline_club_connect: '5 jugadores, 1 club los fichó a todos',
            tagline_player_chain: 'Conecta clubes consecutivos mediante compañeros',
            tagline_passport_fc: 'Colecciona sellos de nacionalidad para un club',
            badge_solved: 'RESUELTO ✅',
            badge_failed: 'FALLIDO ❌',
            badge_played: 'FALLIDO ❌',
            back_to_playmaker: '← Volver a Playmaker',

            // Common Gameplay
            lives: 'Vidas',
            guessed: 'Adivinados',
            guess: 'ADIVINAR',
            submit: 'ENVIAR',
            give_up: 'Rendirse',
            give_up_confirm: '¿Estás seguro de que quieres rendirte? Se guardará tu puntuación actual.',
            confirm_yes: 'Sí, Terminar Partido',
            confirm_no: 'Seguir Jugando',
            skip: 'Saltar',
            hint: 'Pista',
            hints: 'Pistas',
            free_hint: 'Pista Gratis',
            var_review: 'Revisión VAR',
            appeal_var: 'Apelar al VAR',
            var_checking: 'Revisión del VAR en Progreso...',
            var_success: 'VAR CORRIGE: ¡Gol Válido! +1 Vida Restaurada 📺⚽',
            var_failed: 'VAR CONFIRMA: Se Mantiene la Decisión de Campo ❌',
            placeholder_player: 'Escribe y selecciona el nombre del jugador...',
            placeholder_club: 'Escribe y selecciona el nombre del club...',
            placeholder_general: 'Buscar nombre...',
            no_matches: 'No se encontraron jugadores coincidentes',
            no_matches_club: 'No se encontraron clubes coincidentes',

            // Toasts & Messages
            toast_already_guessed: '¡"{name}" ya fue adivinado!',
            toast_already_tried: '¡"{name}" ya fue intentado!',
            toast_invalid_selection: 'Por favor selecciona una opción de la lista desplegable.',
            toast_wrong_guess: '¡Incorrecto! -1 Vida',
            toast_correct_guess: '¡Correcto! {name}',
            toast_life_lost: '-1 Vida',
            toast_life_added: '¡+1 Vida! ❤️',
            toast_hint_revealed: '¡Pista revelada! 💡',
            toast_out_of_lives: '¡Te quedaste sin vidas! Puntuación final guardada.',

            // Modal & Outcomes
            outcome_win_title: '¡COMPLETADO!',
            outcome_perfect_title: '¡GENIO TOTAL!',
            outcome_partial_title: '¡GRAN ESFUERZO!',
            outcome_loss_title: 'FIN DEL JUEGO',
            outcome_partial_default_msg: '¡Llegaste al pitido final! Puntuación: {score}/{maxScore}. ¡Gran esfuerzo y resistencia!',
            outcome_loss_default_msg: '¡Te quedaste sin vidas! Mejor suerte mañana.',
            next_puzzle_in: 'Siguiente puzzle en',
            score: 'Puntuación',

            // Share Card Titles & Descriptions
            share_header: 'Playmaker',
            share_challenge: '¿Puedes superar mi puntuación?',
            share_all_found: '🏆 ¡TODOS LOS {maxScore} FICHADOS! · ❤️ {lives} vidas restantes',
            share_board_cleared: '🎖️ ¡TABLERO COMPLETADO! · {score}/{maxScore} encontrados · ❤️ {lives} vidas',
            share_transfers_found: '🎯 {score}/{maxScore} encontrados · ❤️ {lives} vidas',
            share_career_completed: '🌟 ¡TRAYECTORIA COMPLETADA! · ❤️ {lives} vidas restantes',
            share_career_survived: '🎖️ ¡TRAYECTORIA SUPERADA! · {score}/{maxScore} clubes adivinados · ❤️ {lives} vidas',
            share_career_score: '🎯 {score}/{maxScore} clubes adivinados · ❤️ {lives} vidas',
            share_connected_in: '✨ ¡CONECTADO EN {score} PISTA{plural}! · ❤️ {lives} vidas',
            share_connected_missed: '❌ Conexión Fallida · 💔 Sin vidas',
            share_chain_instant: '⭐️ ¡VICTORIA DIRECTA! · 🎯 ¡Conexión en 1 solo paso!',
            share_chain_solved: '🔗 ¡CADENA RESUELTA! · 🏆 Llegaste a {target}! ({score}/{maxScore} pasos) · ❤️ {lives} vidas',
            share_chain_partial: '🎖️ ¡LLEGASTE A {target}! · {score}/{maxScore} pasos · ❤️ {lives} vidas',
            share_chain_broke: '💔 CADENA ROTA · {score}/{maxScore} pasos completados',
            share_passport_completed: '🛂 ¡PASAPORTE SELLADO! · 🏆 4/4 Nacionalidades Resueltas · ❤️ {lives} vidas',
            share_passport_partial: '🎖️ ¡CONTROL SUPERADO! · {score}/4 Sellos Desbloqueados · ❤️ {lives} vidas',
            share_passport_loss: '⛔ VISA DENEGADA · {score}/4 Sellos Desbloqueados',
        }
    };

    /**
     * Determines current active language from path or storage.
     */
    function detectLang() {
        if (typeof window !== 'undefined' && window.location) {
            const path = window.location.pathname || '';
            if (path.startsWith('/es/') || path === '/es' || path.includes('/es/games/')) {
                return 'es';
            }
        }
        try {
            if (typeof localStorage !== 'undefined') {
                const stored = localStorage.getItem('playmaker_lang');
                if (stored === 'es' || stored === 'en') {
                    return stored;
                }
            }
        } catch (e) {}
        return 'en';
    }

    let currentLang = detectLang();

    function getLang() {
        return currentLang || 'en';
    }

    function setLang(lang) {
        if (lang !== 'es' && lang !== 'en') lang = 'en';
        currentLang = lang;
        try {
            if (typeof localStorage !== 'undefined') {
                localStorage.setItem('playmaker_lang', lang);
            }
        } catch (e) {}
    }

    /**
     * Translates a given key with optional string interpolation params.
     */
    function t(key, params, langOverride) {
        const lang = langOverride || currentLang || 'en';
        const dict = TRANSLATIONS[lang] || TRANSLATIONS.en;
        let str = dict[key] !== undefined ? dict[key] : (TRANSLATIONS.en[key] !== undefined ? TRANSLATIONS.en[key] : key);

        if (params && typeof params === 'object') {
            Object.keys(params).forEach(k => {
                str = str.replace(new RegExp('\\{' + k + '\\}', 'g'), String(params[k]));
            });
        }
        return str;
    }

    /**
     * Returns the counterpart URL for language toggling.
     * e.g. /games/top_transfers.html -> /es/games/top_transfers.html
     *      /es/games/top_transfers.html -> /games/top_transfers.html
     *      / or /index.html -> /es/ or /es/index.html
     */
    function getCounterpartUrl(targetLang) {
        if (typeof window === 'undefined' || !window.location) return '/';
        const path = window.location.pathname || '/';
        const search = window.location.search || '';
        const hash = window.location.hash || '';

        if (targetLang === 'es') {
            if (path.startsWith('/es/') || path === '/es') {
                return path + search + hash;
            }
            if (path === '/' || path === '/index.html') {
                return '/es/' + search + hash;
            }
            if (path.startsWith('/games/')) {
                return '/es' + path + search + hash;
            }
            return '/es/' + search + hash;
        } else {
            // targetLang === 'en'
            if (path.startsWith('/es/games/')) {
                return path.replace('/es/games/', '/games/') + search + hash;
            }
            if (path.startsWith('/es/') || path === '/es') {
                const sub = path.replace(/^\/es\/?/, '');
                return '/' + sub + search + hash;
            }
            return path + search + hash;
        }
    }

    /**
     * Toggles language and navigates.
     */
    function switchLanguage(targetLang) {
        const newLang = targetLang || (currentLang === 'es' ? 'en' : 'es');
        setLang(newLang);
        const url = getCounterpartUrl(newLang);
        if (typeof window !== 'undefined' && window.location) {
            window.location.href = url;
        }
    }

    /**
     * Renders language toggle button HTML into any target container or generates snippet.
     */
    const POSITIONS_ES = {
        'Forward': 'Delantero',
        'Attack': 'Delantero',
        'Attacker': 'Delantero',
        'Midfield': 'Centrocampista',
        'Midfielder': 'Centrocampista',
        'Defender': 'Defensa',
        'Defence': 'Defensa',
        'Defense': 'Defensa',
        'Goalkeeper': 'Portero',
        'Keeper': 'Portero',
        'Centre-Back': 'Defensa Central',
        'Center-Back': 'Defensa Central',
        'Left-Back': 'Lateral Izquierdo',
        'Right-Back': 'Lateral Derecho',
        'Central Midfield': 'Mediocentro',
        'Attacking Midfield': 'Mediapunta',
        'Defensive Midfield': 'Pivote',
        'Left Winger': 'Extremo Izquierdo',
        'Right Winger': 'Extremo Derecho',
        'Second Striker': 'Segundo Delantero',
        'Centre-Forward': 'Delantero Centro'
    };

    const NATIONALITIES_ES = {
        'Germany': 'Alemania',
        'Spain': 'España',
        'France': 'Francia',
        'Italy': 'Italia',
        'England': 'Inglaterra',
        'Brazil': 'Brasil',
        'Argentina': 'Argentina',
        'Portugal': 'Portugal',
        'Netherlands': 'Países Bajos',
        'Belgium': 'Bélgica',
        'Croatia': 'Croacia',
        'Uruguay': 'Uruguay',
        'Colombia': 'Colombia',
        'Senegal': 'Senegal',
        'Japan': 'Japón',
        'Morocco': 'Marruecos',
        'Nigeria': 'Nigeria',
        'Cameroon': 'Camerún',
        'Ivory Coast': 'Costa de Marfil',
        "Côte d'Ivoire": 'Costa de Marfil',
        'Mexico': 'México',
        'USA': 'Estados Unidos',
        'United States': 'Estados Unidos',
        'Wales': 'Gales',
        'Scotland': 'Escocia',
        'Northern Ireland': 'Irlanda del Norte',
        'Republic of Ireland': 'Irlanda',
        'Ireland': 'Irlanda',
        'Poland': 'Polonia',
        'Denmark': 'Dinamarca',
        'Sweden': 'Suecia',
        'Switzerland': 'Suiza',
        'Austria': 'Austria',
        'Norway': 'Noruega',
        'Algeria': 'Argelia',
        'Egypt': 'Egipto',
        'Ghana': 'Ghana',
        'Turkey': 'Turquía',
        'Greece': 'Grecia',
        'Czech Republic': 'República Checa',
        'Czechia': 'República Checa',
        'Serbia': 'Serbia',
        'Ukraine': 'Ucrania',
        'Chile': 'Chile',
        'Peru': 'Perú',
        'Ecuador': 'Ecuador',
        'Paraguay': 'Paraguay',
        'Venezuela': 'Venezuela',
        'South Korea': 'Corea del Sur',
        'Korea, South': 'Corea del Sur',
        'Australia': 'Australia',
        'Canada': 'Canadá',
        'Hungary': 'Hungría',
        'Romania': 'Rumanía',
        'Bulgaria': 'Bulgaria',
        'Slovakia': 'Eslovaquia',
        'Slovenia': 'Eslovenia',
        'Bosnia-Herzegovina': 'Bosnia y Herzegovina',
        'Bosnia and Herzegovina': 'Bosnia y Herzegovina',
        'Finland': 'Finlandia',
        'Iceland': 'Islandia',
        'Albania': 'Albania',
        'Georgia': 'Georgia',
        'Mali': 'Malí',
        'Guinea': 'Guinea',
        'Gabon': 'Gabón',
        'DR Congo': 'RD Congo',
        'Democratic Republic of the Congo': 'RD Congo',
        'South Africa': 'Sudáfrica',
        'Jamaica': 'Jamaica',
        'Costa Rica': 'Costa Rica',
        'Montenegro': 'Montenegro',
        'North Macedonia': 'Macedonia del Norte',
        'Kosovo': 'Kosovo',
        'Israel': 'Israel',
        'Iran': 'Irán',
        'Saudi Arabia': 'Arabia Saudí',
        'Qatar': 'Catar',
        'Tunisia': 'Túnez',
        'Armenia': 'Armenia',
        'New Zealand': 'Nueva Zelanda',
        'Honduras': 'Honduras',
        'Panama': 'Panamá',
        'Bolivia': 'Bolivia',
        'Trinidad and Tobago': 'Trinidad y Tobago'
    };

    const DEMONYMS_ES = {
        'Germany': 'alemán',
        'Spain': 'español',
        'France': 'francés',
        'Italy': 'italiano',
        'England': 'inglés',
        'Brazil': 'brasileño',
        'Argentina': 'argentino',
        'Portugal': 'portugués',
        'Netherlands': 'holandés',
        'Belgium': 'belga',
        'Croatia': 'croata',
        'Uruguay': 'uruguayo',
        'Colombia': 'colombiano',
        'Senegal': 'senegalés',
        'Japan': 'japonés',
        'Morocco': 'marroquí',
        'Nigeria': 'nigeriano',
        'Cameroon': 'camerunés',
        'Ivory Coast': 'marfileño',
        "Côte d'Ivoire": 'marfileño',
        'Mexico': 'mexicano',
        'USA': 'estadounidense',
        'United States': 'estadounidense',
        'Wales': 'galés',
        'Scotland': 'escocés',
        'Northern Ireland': 'norirlandés',
        'Republic of Ireland': 'irlandés',
        'Ireland': 'irlandés',
        'Poland': 'polaco',
        'Denmark': 'danés',
        'Sweden': 'sueco',
        'Switzerland': 'suizo',
        'Austria': 'austriaco',
        'Norway': 'noruego',
        'Algeria': 'argelino',
        'Egypt': 'egipcio',
        'Ghana': 'ghanés',
        'Turkey': 'turco',
        'Türkiye': 'turco',
        'Greece': 'griego',
        'Czech Republic': 'checo',
        'Czechia': 'checo',
        'Serbia': 'serbio',
        'Ukraine': 'ucraniano',
        'Chile': 'chileno',
        'Peru': 'peruano',
        'Ecuador': 'ecuatoriano',
        'Paraguay': 'paraguayo',
        'Venezuela': 'venezolano',
        'South Korea': 'surcoreano',
        'Korea, South': 'surcoreano',
        'Australia': 'australiano',
        'Canada': 'canadiense',
        'Hungary': 'húngaro',
        'Romania': 'rumano',
        'Bulgaria': 'búlgaro',
        'Slovakia': 'eslovaco',
        'Slovenia': 'esloveno',
        'Bosnia-Herzegovina': 'bosnio',
        'Bosnia and Herzegovina': 'bosnio',
        'Bosnia & Herzegovina': 'bosnio',
        'Finland': 'finlandés',
        'Iceland': 'islandés',
        'Albania': 'albanés',
        'Georgia': 'georgiano',
        'Mali': 'maliense',
        'Guinea': 'guineano',
        'Guinea-Bissau': 'bisauguineano',
        'Gabon': 'gabonés',
        'DR Congo': 'congoleño',
        'Democratic Republic of the Congo': 'congoleño',
        'South Africa': 'sudafricano',
        'Jamaica': 'jamaicano',
        'Costa Rica': 'costarricense',
        'Montenegro': 'montenegrino',
        'North Macedonia': 'macedonio',
        'Kosovo': 'kosovar',
        'Israel': 'israelí',
        'Iran': 'iraní',
        'Saudi Arabia': 'saudí',
        'Qatar': 'catarí',
        'Tunisia': 'tunecino',
        'Armenia': 'armenio',
        'New Zealand': 'neozelandés',
        'Honduras': 'hondureño',
        'Panama': 'panameño',
        'Bolivia': 'boliviano',
        'Trinidad and Tobago': 'trinitense'
    };

    function translatePosition(pos, lang) {
        if (!pos) return '';
        const l = lang || getLang();
        if (l === 'es') {
            return POSITIONS_ES[pos] || pos;
        }
        return pos;
    }

    function translateNationality(nat, lang) {
        if (!nat) return '';
        const l = lang || getLang();
        if (l === 'es') {
            return NATIONALITIES_ES[nat] || nat;
        }
        return nat;
    }

    function translateDemonym(nat, lang) {
        if (!nat) return '';
        const l = lang || getLang();
        if (l === 'es') {
            return DEMONYMS_ES[nat] || nat;
        }
        return nat;
    }

    function renderLanguageSwitcher() {
        const isEs = getLang() === 'es';
        return `
            <div class="flex items-center bg-white/5 border border-white/10 rounded-lg p-0.5 font-mono text-xs select-none">
                <a href="${getCounterpartUrl('en')}" onclick="FootyI18n.setLang('en')" class="px-2 py-0.5 rounded transition-all ${!isEs ? 'bg-accent/20 text-accent font-bold shadow-sm' : 'text-on-surface-variant hover:text-white'}" title="Switch to English">EN</a>
                <span class="text-white/20 text-[10px] select-none">|</span>
                <a href="${getCounterpartUrl('es')}" onclick="FootyI18n.setLang('es')" class="px-2 py-0.5 rounded transition-all ${isEs ? 'bg-accent/20 text-accent font-bold shadow-sm' : 'text-on-surface-variant hover:text-white'}" title="Cambiar a Español">ES</a>
            </div>
        `;
    }

    global.FootyI18n = {
        getLang,
        setLang,
        t,
        getCounterpartUrl,
        switchLanguage,
        renderLanguageSwitcher,
        translatePosition,
        translateNationality,
        translateDemonym,
        POSITIONS_ES,
        NATIONALITIES_ES,
        DEMONYMS_ES,
        TRANSLATIONS
    };

})(typeof window !== 'undefined' ? window : this);
