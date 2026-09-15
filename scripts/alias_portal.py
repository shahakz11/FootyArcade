"""
scripts/alias_portal.py

Local GUI portal for managing team & player aliases and hidden lists.
Run directly or via AliasPortal.command.
Serves on http://localhost:5050 by default.
"""

import os
import sys
import json
import logging
from flask import Flask, jsonify, request, render_template_string

# Add repository root to python path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from scripts.alias_utils import (
    load_aliases_config,
    save_aliases_config,
    get_club_alias_map,
    get_hidden_clubs,
    get_hidden_players,
    get_config_path,
    normalize_search_text
)

app = Flask(__name__)
# Suppress noisy Flask dev server logs
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# In-memory cached dataset lists for fast searching
CACHED_CLUBS = None
CACHED_PLAYERS = None

def get_all_clubs():
    global CACHED_CLUBS
    if CACHED_CLUBS is None:
        path = os.path.join(ROOT_DIR, "all_clubs.json")
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    CACHED_CLUBS = json.load(f)
            except Exception as e:
                print(f"Error loading all_clubs.json: {e}")
                CACHED_CLUBS = []
        else:
            CACHED_CLUBS = []
    return CACHED_CLUBS

def get_all_players():
    global CACHED_PLAYERS
    if CACHED_PLAYERS is None:
        path = os.path.join(ROOT_DIR, "all_players.json")
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    CACHED_PLAYERS = json.load(f)
            except Exception as e:
                print(f"Error loading all_players.json: {e}")
                CACHED_PLAYERS = []
        else:
            CACHED_PLAYERS = []
    return CACHED_PLAYERS

# ─────────────────────────────────────────────────────────────
# API Endpoints
# ─────────────────────────────────────────────────────────────

@app.route("/api/config", methods=["GET"])
def api_get_config():
    cfg = load_aliases_config(ROOT_DIR)
    return jsonify({
        "status": "success",
        "config": cfg,
        "path": get_config_path(ROOT_DIR)
    })

@app.route("/api/config", methods=["POST"])
def api_save_config():
    data = request.get_json(force=True, silent=True)
    if not data or not isinstance(data, dict):
        return jsonify({"status": "error", "message": "Invalid JSON body"}), 400
    
    # Basic schema sanitization
    clubs_data = data.get("clubs", {})
    sanitized = {
        "version": data.get("version", 1),
        "clubs": {
            "groups": clubs_data.get("groups", []),
            "hidden_standalone": [c.strip() for c in clubs_data.get("hidden_standalone", []) if isinstance(c, str) and c.strip()]
        },
        "players": {
            "hidden": [p.strip() for p in data.get("players", {}).get("hidden", []) if isinstance(p, str) and p.strip()]
        }
    }
    
    # Sanitize groups
    clean_groups = []
    for g in sanitized["clubs"]["groups"]:
        d_name = (g.get("display_name") or "").strip()
        if not d_name:
            continue
        aliases = [a.strip() for a in g.get("aliases", []) if isinstance(a, str) and a.strip() and a.strip() != d_name]
        # Remove duplicate aliases while keeping order
        seen_a = set()
        clean_a = []
        for a in aliases:
            if a not in seen_a:
                seen_a.add(a)
                clean_a.append(a)
        clean_groups.append({
            "display_name": d_name,
            "aliases": clean_a,
            "hidden": bool(g.get("hidden", False))
        })
    sanitized["clubs"]["groups"] = clean_groups

    save_aliases_config(sanitized, ROOT_DIR)
    return jsonify({"status": "success", "message": "Saved successfully", "config": sanitized})

@app.route("/api/search/clubs", methods=["GET"])
def api_search_clubs():
    raw_q = (request.args.get("q") or "").strip()
    norm_q = normalize_search_text(raw_q)
    limit = int(request.args.get("limit", 25))
    if not norm_q:
        return jsonify([])
    
    clubs = get_all_clubs()
    prefix_matches = []
    sub_matches = []
    
    for c in clubs:
        if not isinstance(c, str):
            continue
        c_clean = c.strip()
        c_norm = normalize_search_text(c_clean)
        if c_norm.startswith(norm_q):
            prefix_matches.append(c_clean)
        elif norm_q in c_norm:
            sub_matches.append(c_clean)
        if len(prefix_matches) >= limit:
            break
            
    results = (prefix_matches + sub_matches)[:limit]
    return jsonify(results)

@app.route("/api/search/players", methods=["GET"])
def api_search_players():
    raw_q = (request.args.get("q") or "").strip()
    norm_q = normalize_search_text(raw_q)
    limit = int(request.args.get("limit", 25))
    if not norm_q:
        return jsonify([])
    
    players = get_all_players()
    prefix_matches = []
    sub_matches = []
    
    for p in players:
        if isinstance(p, dict):
            name = (p.get("Name") or "").strip()
            nat = p.get("Nationality") or ""
            pos = p.get("Position") or ""
            val = p.get("MarketValue") or 0
        elif isinstance(p, str):
            name = p.strip()
            nat, pos, val = "", "", 0
        else:
            continue
            
        n_norm = normalize_search_text(name)
        item = {"Name": name, "Nationality": nat, "Position": pos, "MarketValue": val}
        if n_norm.startswith(norm_q):
            prefix_matches.append(item)
        elif norm_q in n_norm:
            sub_matches.append(item)
            
        if len(prefix_matches) >= limit:
            break
            
    results = (prefix_matches + sub_matches)[:limit]
    return jsonify(results)

# ─────────────────────────────────────────────────────────────
# UI Template
# ─────────────────────────────────────────────────────────────

PORTAL_HTML = r"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Playmaker · Team & Player Aliases Maker</title>
    <link rel="icon" href="/favicon.ico" type="image/x-icon">
    <!-- Tailwind CSS CDN -->
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            darkMode: 'class',
            theme: {
                extend: {
                    colors: {
                        brand: {
                            gold: '#fbbf24',
                            emerald: '#10b981',
                            red: '#ef4444',
                            dark: '#0f172a',
                            card: '#1e293b',
                            border: '#334155'
                        }
                    }
                }
            }
        }
    </script>
    <style>
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: #0f172a; }
        ::-webkit-scrollbar-thumb { background: #334155; border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: #475569; }
        .tab-active { border-bottom: 2px solid #fbbf24; color: #fbbf24; }
        .glass-card { background: rgba(30, 41, 59, 0.85); backdrop-filter: blur(8px); }
    </style>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen flex flex-col font-sans selection:bg-amber-500 selection:text-black">

    <!-- Header / Navbar -->
    <header class="border-b border-slate-800 bg-slate-900/90 sticky top-0 z-50 backdrop-blur">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between">
            <div class="flex items-center space-x-3">
                <span class="text-2xl">⚽</span>
                <div>
                    <h1 class="text-lg font-bold tracking-wide flex items-center gap-2">
                        <span>PLAYMAKER</span>
                        <span class="text-xs uppercase px-2 py-0.5 rounded bg-amber-500/20 text-amber-400 font-semibold border border-amber-500/30">Aliases & Dropdown Portal</span>
                    </h1>
                    <p class="text-xs text-slate-400">Manage canonical team aliases and hide noisy clubs or players</p>
                </div>
            </div>
            <div class="flex items-center space-x-3">
                <span id="save-status" class="text-xs text-emerald-400 font-medium px-2.5 py-1 rounded bg-emerald-500/10 border border-emerald-500/20 hidden">Saved</span>
                <button onclick="saveConfig()" class="bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold px-4 py-2 rounded-lg text-sm shadow-lg shadow-amber-500/20 transition flex items-center gap-2 active:scale-95">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4"/></svg>
                    Save Changes
                </button>
            </div>
        </div>
    </header>

    <!-- Main Container -->
    <main class="max-w-7xl mx-auto px-4 sm:px-6 py-6 flex-1 w-full space-y-6">

        <!-- Navigation Tabs & Stats Bar -->
        <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between border-b border-slate-800 pb-3 gap-4">
            <nav class="flex space-x-6 text-sm font-medium">
                <button onclick="switchTab('groups')" id="tab-btn-groups" class="pb-2 text-slate-400 hover:text-slate-200 transition tab-active flex items-center gap-2">
                    <span>🛡️ Team Aliases</span>
                    <span id="stat-groups-count" class="text-xs bg-slate-800 px-2 py-0.5 rounded-full text-slate-300">0</span>
                </button>
                <button onclick="switchTab('hidden-clubs')" id="tab-btn-hidden-clubs" class="pb-2 text-slate-400 hover:text-slate-200 transition flex items-center gap-2">
                    <span>🚫 Hidden Clubs</span>
                    <span id="stat-hidden-clubs-count" class="text-xs bg-slate-800 px-2 py-0.5 rounded-full text-slate-300">0</span>
                </button>
                <button onclick="switchTab('hidden-players')" id="tab-btn-hidden-players" class="pb-2 text-slate-400 hover:text-slate-200 transition flex items-center gap-2">
                    <span>👤 Hidden Players</span>
                    <span id="stat-hidden-players-count" class="text-xs bg-slate-800 px-2 py-0.5 rounded-full text-slate-300">0</span>
                </button>
            </nav>

            <div class="flex items-center gap-2 text-xs text-slate-400">
                <span>Config Path:</span>
                <code id="config-path" class="bg-slate-900 px-2 py-1 rounded text-slate-300 border border-slate-800 font-mono">private/aliases_config.json</code>
            </div>
        </div>

        <!-- TAB 1: TEAM ALIAS GROUPS -->
        <section id="tab-groups" class="space-y-6">
            <!-- Action Bar: Add Group & Filter -->
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4 items-center">
                <div class="relative md:col-span-2">
                    <input type="text" id="group-search-input" oninput="renderGroups()" placeholder="Filter alias groups by team name or alias..." class="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-amber-500 transition">
                    <span class="absolute right-3 top-2.5 text-slate-500">🔍</span>
                </div>
                <div class="flex justify-end">
                    <button onclick="openNewGroupModal()" class="w-full sm:w-auto bg-slate-800 hover:bg-slate-700 border border-slate-600 text-slate-100 font-medium px-4 py-2.5 rounded-lg text-sm transition flex items-center justify-center gap-2 shadow">
                        <span class="text-amber-400 font-bold">+</span> Create Team Alias Group
                    </button>
                </div>
            </div>

            <!-- Groups Cards Grid -->
            <div id="groups-container" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                <!-- Injected dynamically -->
            </div>
        </section>

        <!-- TAB 2: HIDDEN STANDALONE CLUBS -->
        <section id="tab-hidden-clubs" class="hidden space-y-6">
            <div class="bg-slate-900/60 border border-slate-800 p-4 rounded-xl flex flex-col md:flex-row gap-4 justify-between items-start md:items-center">
                <div>
                    <h3 class="font-semibold text-slate-200">Standalone Hidden Clubs</h3>
                    <p class="text-xs text-slate-400">Clubs in this list are completely excluded from autocomplete dropdowns across all games.</p>
                </div>
                <div class="w-full md:w-96 relative">
                    <input type="text" id="hide-club-input" placeholder="Search club to hide (e.g. 01 Bamberg)..." oninput="searchClubToHide(this.value)" class="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-amber-500 transition">
                    <div id="hide-club-results" class="absolute z-20 w-full mt-1 bg-slate-900 border border-slate-700 rounded-lg shadow-xl max-h-48 overflow-y-auto hidden"></div>
                </div>
            </div>

            <!-- List of Hidden Clubs -->
            <div id="hidden-clubs-chips" class="flex flex-wrap gap-2">
                <!-- Injected dynamically -->
            </div>
        </section>

        <!-- TAB 3: HIDDEN PLAYERS -->
        <section id="tab-hidden-players" class="hidden space-y-6">
            <div class="bg-slate-900/60 border border-slate-800 p-4 rounded-xl flex flex-col md:flex-row gap-4 justify-between items-start md:items-center">
                <div>
                    <h3 class="font-semibold text-slate-200">Hidden Players</h3>
                    <p class="text-xs text-slate-400">Players in this list will never appear in autocomplete suggestion dropdowns (e.g. retired, duplicated, or non-applicable entries).</p>
                </div>
                <div class="w-full md:w-96 relative">
                    <input type="text" id="hide-player-input" placeholder="Search player to hide..." oninput="searchPlayerToHide(this.value)" class="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-amber-500 transition">
                    <div id="hide-player-results" class="absolute z-20 w-full mt-1 bg-slate-900 border border-slate-700 rounded-lg shadow-xl max-h-48 overflow-y-auto hidden"></div>
                </div>
            </div>

            <!-- List of Hidden Players -->
            <div id="hidden-players-chips" class="flex flex-wrap gap-2">
                <!-- Injected dynamically -->
            </div>
        </section>

    </main>

    <!-- Modal: Create / Edit Group -->
    <div id="group-modal" class="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4 hidden">
        <div class="bg-slate-900 border border-slate-700 rounded-xl max-w-xl w-full p-6 space-y-5 shadow-2xl relative">
            <button onclick="closeGroupModal()" class="absolute top-4 right-4 text-slate-400 hover:text-slate-100 text-xl font-bold">&times;</button>
            <h2 id="modal-title" class="text-lg font-bold text-slate-100 flex items-center gap-2">
                <span>🛡️</span> Team Alias Group
            </h2>

            <div class="space-y-4">
                <div>
                    <label class="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">Primary Display Name</label>
                    <input type="text" id="modal-display-name" placeholder="Canonical name (e.g. Manchester City)" class="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-amber-500 font-semibold">
                    <p class="text-xs text-slate-500 mt-1">This is what appears in the game dropdown and answers.</p>
                </div>

                <div>
                    <label class="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">Search & Add Aliases</label>
                    <div class="relative">
                        <input type="text" id="modal-alias-search" oninput="searchAliases(this.value)" placeholder="Type to search all_clubs.json (e.g. Man City, Man. City)..." class="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-amber-500">
                        <div id="modal-alias-results" class="absolute z-30 w-full mt-1 bg-slate-900 border border-slate-700 rounded-lg shadow-xl max-h-40 overflow-y-auto hidden"></div>
                    </div>
                </div>

                <div>
                    <label class="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">Attached Aliases (Variants)</label>
                    <div id="modal-aliases-container" class="min-h-[60px] p-2 bg-slate-950 border border-slate-800 rounded-lg flex flex-wrap gap-2 items-start max-h-40 overflow-y-auto">
                        <!-- Chips inserted here -->
                    </div>
                    <div class="flex gap-2 mt-2">
                        <input type="text" id="modal-custom-alias-input" placeholder="Or manually type an alias..." class="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-slate-600">
                        <button onclick="addCustomAlias()" class="bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs px-3 py-1.5 rounded-lg border border-slate-700 font-medium">Add</button>
                    </div>
                </div>

                <div class="flex items-center gap-2 pt-2 border-t border-slate-800">
                    <input type="checkbox" id="modal-hidden-checkbox" class="rounded bg-slate-950 border-slate-700 text-amber-500 focus:ring-amber-500 h-4 w-4">
                    <label for="modal-hidden-checkbox" class="text-xs text-slate-300 font-medium">Hide this entire team group from autocomplete dropdowns</label>
                </div>
            </div>

            <div class="flex justify-end gap-3 pt-3 border-t border-slate-800">
                <button onclick="closeGroupModal()" class="px-4 py-2 text-sm text-slate-400 hover:text-slate-200">Cancel</button>
                <button onclick="saveGroupModal()" class="bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold px-4 py-2 rounded-lg text-sm shadow active:scale-95">Save Group</button>
            </div>
        </div>
    </div>

    <!-- JavaScript Application Logic -->
    <script>
        // State
        let config = { version: 1, clubs: { groups: [], hidden_standalone: [] }, players: { hidden: [] } };
        let activeTab = 'groups';
        let editingIndex = -1; // -1 means new group
        let modalAliases = [];

        // Fetch initial config
        async function init() {
            try {
                const res = await fetch('/api/config');
                const data = await res.json();
                if (data.status === 'success') {
                    config = data.config;
                    document.getElementById('config-path').textContent = data.path;
                    updateStats();
                    renderGroups();
                    renderHiddenClubs();
                    renderHiddenPlayers();
                }
            } catch (err) {
                console.error("Failed to load initial config:", err);
            }
        }

        function updateStats() {
            document.getElementById('stat-groups-count').textContent = config.clubs.groups.length;
            document.getElementById('stat-hidden-clubs-count').textContent = config.clubs.hidden_standalone.length;
            document.getElementById('stat-hidden-players-count').textContent = config.players.hidden.length;
        }

        // Tab Switching
        function switchTab(tab) {
            activeTab = tab;
            ['groups', 'hidden-clubs', 'hidden-players'].forEach(t => {
                const btn = document.getElementById('tab-btn-' + t);
                const section = document.getElementById('tab-' + t);
                if (t === tab) {
                    btn.classList.add('tab-active');
                    btn.classList.remove('text-slate-400');
                    section.classList.remove('hidden');
                } else {
                    btn.classList.remove('tab-active');
                    btn.classList.add('text-slate-400');
                    section.classList.add('hidden');
                }
            });
        }

        // Frontend string normalization helper for accents & diacritics
        function normalizeSearchText(str) {
            if (!str) return '';
            return String(str)
                .replace(/[\u200b-\u200f\u202a-\u202e\ufeff]/g, '')
                .replace(/[ðÐ]/g, 'd')
                .replace(/[þÞ]/g, 'th')
                .replace(/[øØ]/g, 'o')
                .replace(/[łŁ]/g, 'l')
                .replace(/[đĐ]/g, 'd')
                .replace(/[æÆ]/g, 'ae')
                .replace(/[œŒ]/g, 'oe')
                .replace(/ß/g, 'ss')
                .normalize('NFD')
                .replace(/[\u0300-\u036f]/g, '')
                .toLowerCase()
                .replace(/[-._']/g, ' ')
                .replace(/\s+/g, ' ')
                .trim();
        }

        // Render Group Cards
        function renderGroups() {
            const container = document.getElementById('groups-container');
            const rawSearch = (document.getElementById('group-search-input').value || '').trim();
            const search = normalizeSearchText(rawSearch);
            container.innerHTML = '';

            const groups = config.clubs.groups;
            let matchCount = 0;

            groups.forEach((g, idx) => {
                const normDisplay = normalizeSearchText(g.display_name);
                const matchesSearch = !search || 
                    normDisplay.includes(search) || 
                    g.aliases.some(a => normalizeSearchText(a).includes(search));

                if (!matchesSearch) return;
                matchCount++;

                const card = document.createElement('div');
                card.className = "bg-slate-900/90 border border-slate-800 hover:border-slate-700 p-4 rounded-xl flex flex-col justify-between space-y-3 transition shadow-sm relative group";

                const isHidden = g.hidden;

                let aliasesHtml = g.aliases.map(a => 
                    `<span class="bg-slate-800 text-slate-300 text-xs px-2 py-0.5 rounded border border-slate-700">${escapeHtml(a)}</span>`
                ).join(' ');

                if (!aliasesHtml) {
                    aliasesHtml = `<span class="text-xs text-slate-500 italic">No additional aliases</span>`;
                }

                card.innerHTML = `
                    <div>
                        <div class="flex items-start justify-between gap-2">
                            <div class="flex items-center gap-2">
                                <span class="text-amber-400 font-bold">🛡️</span>
                                <h3 class="font-bold text-slate-100 text-base">${escapeHtml(g.display_name)}</h3>
                            </div>
                            <div class="flex items-center gap-1.5">
                                ${isHidden ? '<span class="text-[10px] uppercase font-bold px-1.5 py-0.5 rounded bg-red-500/20 text-red-400 border border-red-500/30">Hidden</span>' : ''}
                                <button onclick="editGroup(${idx})" class="text-slate-400 hover:text-amber-400 p-1 text-xs" title="Edit">✏️</button>
                                <button onclick="deleteGroup(${idx})" class="text-slate-400 hover:text-red-400 p-1 text-xs" title="Delete">&times;</button>
                            </div>
                        </div>
                        <div class="mt-3">
                            <p class="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1.5">Recognized Aliases (${g.aliases.length}):</p>
                            <div class="flex flex-wrap gap-1 max-h-24 overflow-y-auto">
                                ${aliasesHtml}
                            </div>
                        </div>
                    </div>
                    <div class="pt-2 border-t border-slate-800 flex justify-between items-center text-xs text-slate-500">
                        <span>Maps to: <strong class="text-slate-300">${escapeHtml(g.display_name)}</strong></span>
                        <button onclick="toggleGroupHidden(${idx})" class="text-[11px] hover:underline ${isHidden ? 'text-emerald-400' : 'text-slate-400'}">
                            ${isHidden ? 'Unhide' : 'Hide from dropdown'}
                        </button>
                    </div>
                `;
                container.appendChild(card);
            });

            if (matchCount === 0) {
                container.innerHTML = `
                    <div class="col-span-full py-12 text-center text-slate-500">
                        <p class="text-sm">No alias groups match your search.</p>
                    </div>
                `;
            }
        }

        function toggleGroupHidden(idx) {
            config.clubs.groups[idx].hidden = !config.clubs.groups[idx].hidden;
            renderGroups();
            triggerSaveFeedback();
        }

        function deleteGroup(idx) {
            if (confirm(`Delete alias group "${config.clubs.groups[idx].display_name}"?`)) {
                config.clubs.groups.splice(idx, 1);
                updateStats();
                renderGroups();
                triggerSaveFeedback();
            }
        }

        // Modal Operations
        function openNewGroupModal() {
            editingIndex = -1;
            modalAliases = [];
            document.getElementById('modal-title').innerHTML = '<span>🛡️</span> New Team Alias Group';
            document.getElementById('modal-display-name').value = '';
            document.getElementById('modal-alias-search').value = '';
            document.getElementById('modal-custom-alias-input').value = '';
            document.getElementById('modal-hidden-checkbox').checked = false;
            renderModalAliases();
            document.getElementById('group-modal').classList.remove('hidden');
        }

        function editGroup(idx) {
            editingIndex = idx;
            const g = config.clubs.groups[idx];
            modalAliases = [...g.aliases];
            document.getElementById('modal-title').innerHTML = '<span>🛡️</span> Edit Team Alias Group';
            document.getElementById('modal-display-name').value = g.display_name;
            document.getElementById('modal-alias-search').value = '';
            document.getElementById('modal-custom-alias-input').value = '';
            document.getElementById('modal-hidden-checkbox').checked = !!g.hidden;
            renderModalAliases();
            document.getElementById('group-modal').classList.remove('hidden');
        }

        function closeGroupModal() {
            document.getElementById('group-modal').classList.add('hidden');
        }

        function renderModalAliases() {
            const container = document.getElementById('modal-aliases-container');
            container.innerHTML = '';
            if (modalAliases.length === 0) {
                container.innerHTML = '<span class="text-xs text-slate-500 italic p-1">No aliases attached yet.</span>';
                return;
            }
            modalAliases.forEach((alias, aIdx) => {
                const chip = document.createElement('span');
                chip.className = "bg-slate-800 text-slate-200 text-xs px-2.5 py-1 rounded-md border border-slate-700 flex items-center gap-1.5";
                chip.innerHTML = `
                    <span>${escapeHtml(alias)}</span>
                    <button onclick="removeModalAlias(${aIdx})" class="text-slate-400 hover:text-red-400 font-bold ml-1">&times;</button>
                `;
                container.appendChild(chip);
            });
        }

        function removeModalAlias(aIdx) {
            modalAliases.splice(aIdx, 1);
            renderModalAliases();
        }

        function addCustomAlias() {
            const val = (document.getElementById('modal-custom-alias-input').value || '').trim();
            if (val && !modalAliases.includes(val)) {
                modalAliases.push(val);
                renderModalAliases();
                document.getElementById('modal-custom-alias-input').value = '';
            }
        }

        async function searchAliases(q) {
            const resultsBox = document.getElementById('modal-alias-results');
            q = q.trim();
            if (!q) {
                resultsBox.classList.add('hidden');
                return;
            }
            try {
                const res = await fetch(`/api/search/clubs?q=${encodeURIComponent(q)}&limit=15`);
                const matches = await res.json();
                if (matches.length === 0) {
                    resultsBox.innerHTML = '<div class="p-2 text-xs text-slate-500">No matching clubs found in all_clubs.json</div>';
                } else {
                    resultsBox.innerHTML = matches.map(c => `
                        <div onclick="selectModalAlias('${escapeAttr(c)}')" class="px-3 py-1.5 text-xs text-slate-200 hover:bg-slate-800 cursor-pointer flex justify-between items-center">
                            <span>${escapeHtml(c)}</span>
                            <span class="text-amber-400 text-[10px] uppercase font-semibold">+ Add</span>
                        </div>
                    `).join('');
                }
                resultsBox.classList.remove('hidden');
            } catch (err) {
                console.error(err);
            }
        }

        function selectModalAlias(alias) {
            if (!modalAliases.includes(alias)) {
                modalAliases.push(alias);
                renderModalAliases();
            }
            // Auto set display name if empty
            const disp = document.getElementById('modal-display-name');
            if (!disp.value.trim()) {
                disp.value = alias;
            }
            document.getElementById('modal-alias-search').value = '';
            document.getElementById('modal-alias-results').classList.add('hidden');
        }

        function saveGroupModal() {
            const displayName = (document.getElementById('modal-display-name').value || '').trim();
            if (!displayName) {
                alert('Please enter a Primary Display Name.');
                return;
            }
            const isHidden = document.getElementById('modal-hidden-checkbox').checked;
            const newGroup = {
                display_name: displayName,
                aliases: modalAliases.filter(a => a !== displayName),
                hidden: isHidden
            };

            if (editingIndex >= 0) {
                config.clubs.groups[editingIndex] = newGroup;
            } else {
                config.clubs.groups.unshift(newGroup);
            }

            updateStats();
            renderGroups();
            closeGroupModal();
            triggerSaveFeedback();
        }

        // TAB 2: Hidden Clubs
        function renderHiddenClubs() {
            const container = document.getElementById('hidden-clubs-chips');
            container.innerHTML = '';
            const list = config.clubs.hidden_standalone;
            if (list.length === 0) {
                container.innerHTML = '<p class="text-xs text-slate-500 italic">No standalone hidden clubs.</p>';
                return;
            }
            list.forEach((c, idx) => {
                const chip = document.createElement('span');
                chip.className = "bg-red-500/10 border border-red-500/30 text-red-300 text-xs px-3 py-1 rounded-lg flex items-center gap-2";
                chip.innerHTML = `
                    <span>${escapeHtml(c)}</span>
                    <button onclick="removeHiddenClub(${idx})" class="text-red-400 hover:text-red-100 font-bold">&times;</button>
                `;
                container.appendChild(chip);
            });
        }

        async function searchClubToHide(q) {
            const resultsBox = document.getElementById('hide-club-results');
            q = q.trim();
            if (!q) {
                resultsBox.classList.add('hidden');
                return;
            }
            try {
                const res = await fetch(`/api/search/clubs?q=${encodeURIComponent(q)}&limit=15`);
                const matches = await res.json();
                if (matches.length === 0) {
                    resultsBox.innerHTML = '<div class="p-2 text-xs text-slate-500">No clubs found</div>';
                } else {
                    resultsBox.innerHTML = matches.map(c => `
                        <div onclick="addHiddenClub('${escapeAttr(c)}')" class="px-3 py-1.5 text-xs text-slate-200 hover:bg-slate-800 cursor-pointer flex justify-between items-center">
                            <span>${escapeHtml(c)}</span>
                            <span class="text-red-400 text-[10px] uppercase font-semibold">Hide</span>
                        </div>
                    `).join('');
                }
                resultsBox.classList.remove('hidden');
            } catch (err) {
                console.error(err);
            }
        }

        function addHiddenClub(club) {
            if (!config.clubs.hidden_standalone.includes(club)) {
                config.clubs.hidden_standalone.push(club);
                renderHiddenClubs();
                updateStats();
                triggerSaveFeedback();
            }
            document.getElementById('hide-club-input').value = '';
            document.getElementById('hide-club-results').classList.add('hidden');
        }

        function removeHiddenClub(idx) {
            config.clubs.hidden_standalone.splice(idx, 1);
            renderHiddenClubs();
            updateStats();
            triggerSaveFeedback();
        }

        // TAB 3: Hidden Players
        function renderHiddenPlayers() {
            const container = document.getElementById('hidden-players-chips');
            container.innerHTML = '';
            const list = config.players.hidden;
            if (list.length === 0) {
                container.innerHTML = '<p class="text-xs text-slate-500 italic">No hidden players configured.</p>';
                return;
            }
            list.forEach((p, idx) => {
                const chip = document.createElement('span');
                chip.className = "bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs px-3 py-1 rounded-lg flex items-center gap-2";
                chip.innerHTML = `
                    <span>👤 ${escapeHtml(p)}</span>
                    <button onclick="removeHiddenPlayer(${idx})" class="text-amber-400 hover:text-amber-100 font-bold">&times;</button>
                `;
                container.appendChild(chip);
            });
        }

        async function searchPlayerToHide(q) {
            const resultsBox = document.getElementById('hide-player-results');
            q = q.trim();
            if (!q) {
                resultsBox.classList.add('hidden');
                return;
            }
            try {
                const res = await fetch(`/api/search/players?q=${encodeURIComponent(q)}&limit=15`);
                const matches = await res.json();
                if (matches.length === 0) {
                    resultsBox.innerHTML = '<div class="p-2 text-xs text-slate-500">No players found</div>';
                } else {
                    resultsBox.innerHTML = matches.map(p => `
                        <div onclick="addHiddenPlayer('${escapeAttr(p.Name)}')" class="px-3 py-1.5 text-xs text-slate-200 hover:bg-slate-800 cursor-pointer flex justify-between items-center">
                            <div>
                                <span class="font-medium">${escapeHtml(p.Name)}</span>
                                <span class="text-slate-400 text-[10px] ml-1.5">${escapeHtml(p.Nationality)} · ${escapeHtml(p.Position)}</span>
                            </div>
                            <span class="text-red-400 text-[10px] uppercase font-semibold">Hide</span>
                        </div>
                    `).join('');
                }
                resultsBox.classList.remove('hidden');
            } catch (err) {
                console.error(err);
            }
        }

        function addHiddenPlayer(name) {
            if (!config.players.hidden.includes(name)) {
                config.players.hidden.push(name);
                renderHiddenPlayers();
                updateStats();
                triggerSaveFeedback();
            }
            document.getElementById('hide-player-input').value = '';
            document.getElementById('hide-player-results').classList.add('hidden');
        }

        function removeHiddenPlayer(idx) {
            config.players.hidden.splice(idx, 1);
            renderHiddenPlayers();
            updateStats();
            triggerSaveFeedback();
        }

        // Save Config to Server
        async function saveConfig() {
            try {
                const res = await fetch('/api/config', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(config)
                });
                const data = await res.json();
                if (data.status === 'success') {
                    config = data.config;
                    showSavedBanner();
                } else {
                    alert('Error saving config: ' + data.message);
                }
            } catch (err) {
                alert('Network error saving config: ' + err);
            }
        }

        function triggerSaveFeedback() {
            // Auto save on action or user can click main save button
            saveConfig();
        }

        function showSavedBanner() {
            const b = document.getElementById('save-status');
            b.classList.remove('hidden');
            setTimeout(() => { b.classList.add('hidden'); }, 2000);
        }

        // Utility Escaping
        function escapeHtml(str) {
            if (!str) return '';
            return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
        }
        function escapeAttr(str) {
            if (!str) return '';
            return String(str).replace(/'/g, "\\\\'").replace(/"/g, "&quot;");
        }

        // Boot
        init();
    </script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(PORTAL_HTML)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    print(f"==================================================")
    print(f"⚽ Playmaker Aliases & Dropdown Portal")
    print(f"🌐 Running on: http://localhost:{port}")
    print(f"==================================================")
    app.run(host="0.0.0.0", port=port, debug=False)
