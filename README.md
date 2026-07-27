# ⚽ Playmaker - Top Transfers Guessing Game

An entirely free, serverless, and autonomous football player transfer guessing game based on the Kaggle `davidcariboo/player-scores` dataset.

---

## 🛠️ Project Structure

- `index.html`: The main landing page pointing to active challenges.
- `games.json`: Configuration defining available games (now streamlined to Top Transfers).
- `build_transfer_datasets.py`: Preprocessing script that downloads the latest player-scores dataset from Kaggle, generates daily challenge CSVs, and exports `all_players.json` for autocomplete suggestions.
- `fetch_daily.py`: The build script that compiles `templates/top_transfers_template.html` to `games/top_transfers.html` with today's target club/nationality and player list.
- `templates/top_transfers_template.html`: The game UI template.

---

## 🚀 Quick Start

### 1. Install Dependencies
Ensure you have the required Python libraries installed:
```bash
pip install pandas kagglehub
```

### 2. Download Kaggle Dataset & Build Preprocessed Files
Run the preprocessor script to download data from Kaggle and generate the database:
```bash
python3 build_transfer_datasets.py
```
This produces:
- `daily_transfer_games.csv`
- `daily_nationality_transfer_games.csv`
- `all_players.json`

### 3. Compile the Daily Puzzle
Execute the fetch script to inject the daily game data and player lists into the final HTML:
```bash
python3 fetch_daily.py
```
Options available:
- `--offset N`: Offset today's date by `N` days to preview future puzzles.
- `--puzzle N`: Force compile a specific puzzle index (1-180).
- `--random`: Compile a random puzzle index.

### 4. Preview the Game Locally
Start a lightweight local server to play:
```bash
python3 -m http.server 8000
```
Open [http://localhost:8000](http://localhost:8000) in your web browser.
