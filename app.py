import streamlit as st
import pandas as pd
import calendar

st.set_page_config(layout="wide")
st.title("🏸 Badminton Fee Calculator")

# -----------------------------
# Month & Year
# -----------------------------
col1, col2 = st.columns(2)
with col1:
    year = st.number_input("Year", value=2026)
with col2:
    month = st.number_input("Month", value=4, min_value=1, max_value=12)

# -----------------------------
# Schedule
# -----------------------------
schedule = {
    "Monday": 1,
    "Tuesday": 1,
    "Thursday": 1,
    "Friday": 2
}

# Generate match days
cal = calendar.monthcalendar(year, month)
all_match_days = []

for week in cal:
    for i, day_name in enumerate(["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]):
        if week[i] != 0 and day_name in schedule:
            all_match_days.append((day_name, week[i], schedule[day_name]))

# -----------------------------
# Cost Inputs
# -----------------------------
st.subheader("💰 Cost Inputs")

c1, c2, c3 = st.columns(3)

with c1:
    cost_per_hour = st.number_input("Court Cost / Hr", value=55.0)

with c2:
    num_tubes = st.number_input("Shuttle Tubes", value=5)

with c3:
    cost_per_tube = st.number_input("Cost per Tube", value=135.0)

total_shuttle_cost = num_tubes * cost_per_tube

# -----------------------------
# Player Setup
# -----------------------------
st.subheader("👥 Players")

if "players" not in st.session_state:
    st.session_state.players = []

col1, col2 = st.columns([3,1])

with col1:
    new_player = st.text_input("Enter Player Name")

with col2:
    if st.button("➕ Add Player"):
        if new_player:
            st.session_state.players.append({
                "name": new_player,
                "days": all_match_days.copy()
            })

# Remove player
if st.session_state.players:
    remove_player = st.selectbox("Remove Player", ["None"] + [p["name"] for p in st.session_state.players])
    if st.button("❌ Remove"):
        if remove_player != "None":
            st.session_state.players = [p for p in st.session_state.players if p["name"] != remove_player]

# -----------------------------
# Player Availability
# -----------------------------
player_days_map = {}

st.subheader("📅 Player Availability")

for player in st.session_state.players:
    st.markdown(f"### {player['name']}")

    col1, col2 = st.columns(2)

    # Select All
    with col1:
        if st.button(f"Select All - {player['name']}"):
            player["days"] = all_match_days.copy()

    # Clear All
    with col2:
        if st.button(f"Clear All - {player['name']}"):
            player["days"] = []

    # Multi-select days
    selected_labels = st.multiselect(
        "Select Days",
        options=[f"{d[0]}-{d[1]} ({d[2]}h)" for d in all_match_days],
        default=[f"{d[0]}-{d[1]} ({d[2]}h)" for d in player["days"]],
        key=f"multi_{player['name']}"
    )

    selected_days = []
    for label in selected_labels:
        for d in all_match_days:
            if label == f"{d[0]}-{d[1]} ({d[2]}h)":
                selected_days.append(d)

    player_days_map[player["name"]] = selected_days

# -----------------------------
# CALCULATION
# -----------------------------
if player_days_map:

    player_totals = {p: {"hours": 0, "court_fee": 0} for p in player_days_map}

    day_summary = []

    for day_name, day_num, hours in all_match_days:

        attendees = [
            p for p in player_days_map
            if (day_name, day_num, hours) in player_days_map[p]
        ]

        if attendees:
            day_cost = hours * cost_per_hour
            per_player_cost = day_cost / len(attendees)

            day_summary.append([
                f"{day_name}-{day_num}",
                hours,
                len(attendees),
                round(day_cost, 2),
                round(per_player_cost, 2)
            ])

            for p in attendees:
                player_totals[p]["hours"] += hours
                player_totals[p]["court_fee"] += per_player_cost

    # Shuttle split (equal)
    total_players = len(player_days_map)
    shuttle_per_player = total_shuttle_cost / total_players if total_players else 0

    # Final table
    final_data = []
    for p in player_totals:
        total = player_totals[p]["court_fee"] + shuttle_per_player
        final_data.append([
            p,
            player_totals[p]["hours"],
            round(player_totals[p]["court_fee"], 2),
            round(shuttle_per_player, 2),
            round(total, 2)
        ])

    df = pd.DataFrame(final_data, columns=[
        "Player", "Hours", "Court Fee", "Shuttle Fee", "Total"
    ])

    # -----------------------------
    # OUTPUT
    # -----------------------------
    st.subheader("📊 Final Fee Table")
    st.dataframe(df, use_container_width=True)

    st.subheader("📅 Day-wise Breakdown")
    day_df = pd.DataFrame(day_summary, columns=[
        "Day", "Hours", "Players", "Total Cost", "Per Player"
    ])
    st.dataframe(day_df, use_container_width=True)

    # Download
    st.download_button(
        "⬇ Download CSV",
        df.to_csv(index=False).encode("utf-8"),
        "badminton_fees.csv"
    )

else:
    st.info("Add players to start calculation.")