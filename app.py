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

URL_GAMES = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard?dates=20260611-20260719&limit=100"
URL_STANDINGS = "https://site.api.espn.com/apis/v2/sports/soccer/fifa.world/standings"

# Nutzt Streamlits Cache, damit ESPN nicht bei jedem Seitenaufruf neu abgefragt wird (schont die API)
@st.cache_data(ttl=300)  # Daten werden 5 Minuten zwischengespeichert
def fetch_data(url):
    try:
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
                    if team2_name in countries:
                        player_results[player]["points"] += 1
                        player_results[player]["details"].append(f"1 P. | {team2_name} ({team2_score}:{team1_score} vs. {team1_name})")
                else:
                    if winner in countries:
                        player_results[player]["points"] += 3
                        player_results[player]["details"].append(f"3 P. | {winner} (Sieg {team1_score if winner==team1_name else team2_score}:{team2_score if winner==team1_name else team1_score} vs. {loser})")
                    if loser in countries:
                        player_results[player]["details"].append(f"0 P. | {loser} (Niederlage gegen {winner})")
    return player_results

def apply_bonus_points(player_results, standings_data):
    if not standings_data or 'children' not in standings_data: return player_results
    for group in standings_data['children']:
        standings = group.get('standings', {})
        entries = standings.get('entries', [])

        group_finished = True
        for entry in entries:
            stats = entry.get('stats', [])
            games_played = 0
            for stat in stats:
                if stat.get('name') == 'gamesPlayed': games_played = int(stat.get('value', 0))
            if games_played < 3:
                group_finished = False
                break

        if group_finished and len(entries) >= 2:
            for i, entry in enumerate(entries[:2]):
                team_name = entry.get('team', {}).get('name')
                for player, countries in TEAMS.items():
                    if team_name in countries:
                        player_results[player]["points"] += 1
                        player_results[player]["bonus_teams"].append(team_name)
    return player_results

# --- WEB-OBERFLÄCHE ---
st.title("🏆 WM-Tippspiel Runde 2026")
st.write("Die Tabellenstände aktualisieren sich automatisch im Hintergrund.")

# Daten laden & berechnen
games_json = fetch_data(URL_GAMES)
events = games_json.get('events', []) if games_json else []
standings_json = fetch_data(URL_STANDINGS)

results = calculate_scores(events)
results = apply_bonus_points(results, standings_json)

# 1. Haupttabelle vorbereiten
table_data = []
for player, data in results.items():
    bonus_anzahl = len(set(data["bonus_teams"]))
    table_data.append({
        "Mitspieler": player,
        "Punkte": data["points"],
        "Bonus-Teams": bonus_anzahl
    })

df = pd.DataFrame(table_data).sort_values(by="Punkte", ascending=False).reset_index(drop=True)
df.index += 1  # Platzierung bei 1 starten lassen

# Haupttabelle anzeigen
st.subheader("Aktuelle Rangliste")
st.dataframe(df, use_container_width=True)

# 2. Detaillierte Aufklapp-Menüs pro Spieler
st.subheader("Details pro Spieler")
for player in df["Mitspieler"]:
    data = results[player]
    with st.expander(f"📊 Details für {player} ({data['points']} Punkte)"):
        if data["bonus_teams"]:
            st.markdown("**🌟 Erreichte Bonuspunkte (Nächste Runde):**")
            for b_team in sorted(list(set(data["bonus_teams"]))):
                st.write(f"🟢 +1 Punkt für **{b_team}**")
            st.divider()

        st.markdown("**Spiele in der Wertung:**")
        if data["details"]:
            # --- DIAGNOSE-BEREICH (Ganz unten in die app.py einfügen) ---
st.divider()
st.subheader("🔍 API-Diagnose: Alle importierten Spiele")

if events:
    diagnose_list = []
    for event in events:
        status = event.get('status', {}).get('type', {}).get('name', '')
        competitions = event.get('competitions', [{}])[0]
        competitors = competitions.get('competitors', [])
        
        if len(competitors) >= 2:
            t1 = competitors[0].get('team', {}).get('name')
            s1 = competitors[0].get('score', 0)
            t2 = competitors[1].get('team', {}).get('name')
            s2 = competitors[1].get('score', 0)
            
            diagnose_list.append({
                "Spiel": f"{t1} vs. {t2}",
                "Ergebnis": f"{s1}:{s2}",
                "Status (API)": status
            })
    
    st.table(pd.DataFrame(diagnose_list))
else:
    st.write("Keine Spieldaten von der API empfangen.")
    st.table(pd.DataFrame(diagnose_list))
else:
    st.write("Keine Spieldaten von der API empfangen.")
            for detail in sorted(list(set(data["details"]))):
                st.write(detail)
        else:
            st.write("Noch keine Spiele in der Wertung.")
