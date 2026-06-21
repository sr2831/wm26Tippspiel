import streamlit as st
import requests
import pandas as pd

# Seiten-Konfiguration (Muss ganz oben stehen)
st.set_page_config(page_title="WM 2026 Tippspiel", page_icon="🏆", layout="centered")

# 1. Eure Tippspiel-Runden-Zuweisung
TEAMS = {
    "Stephan": ["Iran", "Paraguay", "Germany", "Deutschland", "Sweden", "Schweden", "Algeria", "Algerien", "Uruguay", "Spain", "Spanien", "Ghana", "Portugal"],
    "Matthias": ["South Africa", "Südafrika", "Korea Republic", "South Korea", "Südkorea", "Canada", "Kanada", "Scotland", "Schottland", "Brazil", "Brasilien", "Australia", "Australien", "Japan", "Netherlands", "Niederlande", "Belgium", "Belgien", "Norway", "Norwegen", "Austria", "Österreich"],
    "Achim": ["Mexico", "Mexiko", "Switzerland", "Schweiz", "Ivory Coast", "Elfenbeinküste", "Cote d'Ivoire", "Argentina", "Argentinien", "Colombia", "Kolumbien", "England"],
    "Boernie": ["Czech Republic", "Czechia", "Tschechien", "Bosnia and Herzegovina", "Bosnia-Herzegovina", "Bosnien", "Morocco", "Marokko", "Turkey", "Türkiye", "Türkei", "USA", "United States", "Ecuador", "Tunisia", "Tunesien", "Senegal", "Croatia", "Kroatien"]
}

URL_GAMES = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard?limit=100"
URL_STANDINGS = "https://site.api.espn.com/apis/v2/sports/soccer/fifa.world/standings"

# Nutzt Streamlits Cache, damit ESPN nicht bei jedem Seitenaufruf neu abgefragt wird (schont die API)
@st.cache_data(ttl=300)  # Daten werden 5 Minuten zwischengespeichert
def fetch_data(url):
    try:
        # Wenn wir nach Spielen suchen, nutzen wir das erweiterte WM-Archiv der API
        if "scoreboard" in url:
            archive_url = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard?dates=20260611-20260719&limit=100"
            response = requests.get(archive_url)
        else:
            response = requests.get(url)
            
        response.raise_for_status()
        return response.json()
    except:
        return None

def calculate_scores(events):
    player_results = {player: {"points": 0, "details": [], "bonus_teams": []} for player in TEAMS}
    seen_matches = set()
    if not events: return player_results
    
    for event in events:
        match_id = event.get('id')
        if match_id in seen_matches: continue
        status = event.get('status', {}).get('type', {}).get('name', '')
        
        if status == "STATUS_FULL_TIME":
            competitions = event.get('competitions', [{}])[0]
            competitors = competitions.get('competitors', [])
            if len(competitors) < 2: continue
                
            team1_name = competitors[0].get('team', {}).get('name')
            team1_score = int(competitors[0].get('score', 0))
            team2_name = competitors[1].get('team', {}).get('name')
            team2_score = int(competitors[1].get('score', 0))
            seen_matches.add(match_id)
            
            if team1_score > team2_score:
                winner, loser = team1_name, team2_name
                draw = False
            elif team2_score > team1_score:
                winner, loser = team2_name, team1_name
                draw = False
            else:
                winner, loser = None, None
                draw = True

            for player, countries in TEAMS.items():
                if draw:
                    if team1_name in countries:
                        player_results[player]["points"] += 1
                        player_results[player]["details"].append(f"1 P. | {team1_name} ({team1_score}:{team2_score} vs. {team2_name})")
                    if team2_name
