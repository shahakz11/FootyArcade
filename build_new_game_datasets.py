import os
import json
import pandas as pd
import kagglehub

def main():
    print("Loading salimt/football-datasets for new game modes...")
    try:
        salimt_path = kagglehub.dataset_download("xfkzujqjvx97n/football-datasets")
    except Exception:
        salimt_path = os.path.expanduser('~/.cache/kagglehub/datasets/xfkzujqjvx97n/football-datasets/versions/2')
    print(f"Dataset path: {salimt_path}")

    # --- 1. Teammates Played With ---
    teammates_file = os.path.join(salimt_path, 'player_teammates_played_with', 'player_teammates_played_with.csv')
    if os.path.exists(teammates_file):
        print("Processing player_teammates_played_with...")
        df_teammates = pd.read_csv(teammates_file, low_memory=False)
        print(f"Total teammate relationship records: {len(df_teammates)}")
        
        # Filter notable co-appearances (played together >= 270 minutes, i.e., 3+ full games)
        df_teammates['minutes_played_with'] = pd.to_numeric(df_teammates['minutes_played_with'], errors='coerce').fillna(0)
        df_teammates_notable = df_teammates[df_teammates['minutes_played_with'] >= 270].copy()
        print(f"Notable teammate relationships (>= 270 mins): {len(df_teammates_notable)}")

    # --- 2. Injury Histories ---
    injuries_file = os.path.join(salimt_path, 'player_injuries', 'player_injuries.csv')
    if os.path.exists(injuries_file):
        print("Processing player_injuries...")
        df_injuries = pd.read_csv(injuries_file, low_memory=False)
        print(f"Total injury records: {len(df_injuries)}")

    # --- 3. National Team Performances ---
    national_file = os.path.join(salimt_path, 'player_national_performances', 'player_national_performances.csv')
    if os.path.exists(national_file):
        print("Processing player_national_performances...")
        df_national = pd.read_csv(national_file, low_memory=False)
        print(f"Total national team performance records: {len(df_national)}")

    print("New game datasets processed successfully.")

if __name__ == '__main__':
    main()
