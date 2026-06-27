import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import pytz

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

# Hilfsfunktion: Konvertiert die API-Uhrzeit (UTC) in MESZ (Stuttgart-Zeit)
def get_mesz_time(date_str):
    try:
        date_str = date_str.replace("Z", "+00:00")
        utc_dt = datetime.fromisoformat(date_str)
        mesz_tz = pytz.timezone("Europe/Berlin")
        mesz_dt = utc_dt.astimezone(mesz_tz)
        return mesz_dt
    except:
        return datetime.min

# Nutzt Streamlits Cache, damit ESPN nicht bei jedem Seitenaufruf neu abgefragt wird (schont die API)
@st.cache_data(ttl=300)  # Daten werden 5 Minuten zwischengespeichert
def fetch_data(url):
    try:
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
    player_results = {player: {"points": 0, "details": []} for player in TEAMS}
    seen_matches = set()
    if not events: return player_results
    
    # Vorab-Sortierung aller Spiele nach Datum/Uhrzeit
    sorted_events = sorted(events, key=lambda x: x.get('date', ''))
    
    for event in sorted_events:
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
            
            dt = get_mesz_time(event.get('date', ''))

            # EINFACHE & BOMBENFESTE K.O.-ERKENNUNG
            # Das erste K.o.-Spiel startet exakt am 28.06.2026 um 21:00 Uhr MESZ
            ko_start = datetime(2026, 6, 28, 21, 0, tzinfo=pytz.timezone("Europe/Berlin"))
            is_knockout = dt >= ko_start

            if is_knockout:
                # In der K.o.-Runde entscheidet das Weiterkommen ("winner" Flag der API)
                t1_winner = competitors[0].get('winner', False)
                if t1_winner:
                    winner, loser, draw = team1_name, team2_name, False
                else:
                    winner, loser, draw = team2_name, team1_name, False
            else:
                # Reguläre Gruppenphase nach Toren
                if team1_score > team2_score:
                    winner, loser, draw = team1_name, team2_name, False
                elif team2_score > team1_score:
                    winner, loser, draw = team2_name, team1_name, False
                else:
                    winner, loser, draw = None, None, True

            for player, countries in TEAMS.items():
                if draw:
                    if team1_name in countries:
                        player_results[player]["points"] += 1
                        player_results[player]["details"].append((dt, f"1 P. | {team1_name} ({team1_score}:{team2_score} vs. {team2_name})"))
                    if team2_name in countries:
                        player_results[player]["points"] += 1
                        player_results[player]["details"].append((dt, f"1 P. | {team2_name} ({team2_score}:{team1_score} vs. {team1_name})"))
                else:
                    if winner in countries:
                        if is_knockout:
                            player_results[player]["points"] += 4
                            if team1_score == team2_score:
                                player_results[player]["details"].append((dt, f"4 P. | {winner} (K.O.-Sieg i.E. {team1_score}:{team2_score} vs. {loser} – inkl. Bonus)"))
                            else:
                                player_results[player]["details"].append((dt, f"4 P. | {winner} (K.O.-Sieg {team1_score if winner==team1_name else team2_score}:{team2_score if winner==team1_name else team1_score} vs. {loser} – inkl. Bonus)"))
                        else:
                            player_results[player]["points"] += 3
                            player_results[player]["details"].append((dt, f"3 P. | {winner} (Sieg {team1_score if winner==team1_name else team2_score}:{team2_score if winner==team1_name else team1_score} vs. {loser})"))
                    if loser in countries:
                        player_results[player]["details"].append((dt, f"0 P. | {loser} (Ausgeschieden gegen {winner})"))
    return player_results

# --- WEB-OBERFLÄCHE ---
st.title("🏆 WM-Tippspiel Runde 2026")
st.write("Die Tabellenstände aktualisieren sich automatisch im Hintergrund.")

# Daten laden & berechnen
games_json = fetch_data(URL_GAMES)
events = games_json.get('events', []) if games_json else []

results = calculate_scores(events)

# 1. Haupttabelle vorbereiten
table_data = []
for player, data in results.items():
    table_data.append({
        "Mitspieler": player,
        "Punkte": data["points"]
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
        st.markdown("**Spiele in der Wertung (Chronologisch):**")
        if data["details"]:
            unique_details = list(set(data["details"]))
            sorted_details = sorted(unique_details, key=lambda x: x[0])
            for dt_obj, text in sorted_details:
                time_prefix = f"📅 *{dt_obj.strftime('%d.%m. %H:%M')}* | " if dt_obj != datetime.min else ""
                st.write(f"{time_prefix}{text}")
        else:
            st.write("Noch keine Spiele in der Wertung.")

# --- DIAGNOSE-BEREICH ---
st.divider()
st.subheader("🔍 API-Diagnose: Alle importierten Spiele (Nach Datum sortiert)")

if events:
    diagnose_list = []
    sorted_debug_events = sorted(events, key=lambda x: x.get('date', ''))
    
    for event in sorted_debug_events:
        status = event.get('status', {}).get('type', {}).get('name', '')
        competitions = event.get('competitions', [{}])[0]
        competitors = competitions.get('competitors', [])
        
        if len(competitors) >= 2:
            t1 = competitors[0].get('team', {}).get('name')
            s1 = competitors[0].get('score', 0)
            t2 = competitors[1].get('team', {}).get('name')
            s2 = competitors[1].get('score', 0)
            
            dt = get_mesz_time(event.get('date', ''))
            date_display = dt.strftime('%d.%m.%Y - %H:%M Uhr') if dt != datetime.min else "Unbekannt"
            
            diagnose_list.append({
                "Anstoß (MESZ)": date_display,
                "Spiel": f"{t1} vs. {t2}",
                "Ergebnis": f"{s1}:{s2}",
                "Status (API)": status
            })
    
    st.dataframe(pd.DataFrame(diagnose_list), use_container_width=True)
else:
    st.write("Keine Spieldaten von der API empfangen.")
