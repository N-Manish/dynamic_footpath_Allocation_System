import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import sqlite3
from streamlit_autorefresh import st_autorefresh

# =====================================================
# CONFIG
# =====================================================
DB_PATH = "metro_footpath.db"
st.set_page_config(page_title="Dynamic Footpath Dashboard", layout="wide")
st.title("🚉 Dynamic Footpath Allocation System")
st.markdown("### Real-Time Smart Path Finder for Bengaluru Metro Stations (DB Driven)")

# =====================================================
# DB HELPER FUNCTIONS
# =====================================================
def get_connection():
    return sqlite3.connect(DB_PATH)

def get_lines():
    conn = get_connection()
    df = pd.read_sql(
        "SELECT DISTINCT TRIM(line_name) AS line_name FROM stations ORDER BY line_name;",
        conn
    )
    conn.close()
    return df["line_name"].tolist()

def get_stations(line_name):
    conn = get_connection()
    df = pd.read_sql(
        "SELECT DISTINCT station_name FROM stations WHERE TRIM(line_name) = ? ORDER BY station_name;",
        conn,
        params=(line_name,)
    )
    conn.close()
    return df["station_name"].tolist()

def get_station_size(station_name):
    conn = get_connection()
    df = pd.read_sql(
        "SELECT station_size FROM stations WHERE station_name = ? LIMIT 1;",
        conn,
        params=(station_name,)
    )
    conn.close()
    if df.empty:
        return "small"
    return df["station_size"].iloc[0]

def get_locations(station_name):
    conn = get_connection()
    df = pd.read_sql(
        """
        SELECT location_name 
        FROM station_locations 
        WHERE station_name = ? 
        ORDER BY location_name;
        """,
        conn,
        params=(station_name,)
    )
    conn.close()
    return df["location_name"].tolist()

def get_routes(station_name, start_location, end_location):
    conn = get_connection()
    df = pd.read_sql(
        """
        SELECT 
            path_name AS "Path",
            base_distance AS "Base Distance (m)",
            base_time AS "Base Time (mins)"
        FROM routes
        WHERE station_name = ?
          AND start_location = ?
          AND end_location = ?
        """,
        conn,
        params=(station_name, start_location, end_location)
    )
    conn.close()
    return df

# =====================================================
# VISUAL HELPERS
# =====================================================
def draw_station_layout(station_name):
    size = get_station_size(station_name)
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.set_title(f"Schematic Layout – {station_name}", fontsize=11)

    if size == "big":
        ax.add_patch(plt.Rectangle((0.05, 0.65), 0.35, 0.12, fill=False))
        ax.text(0.225, 0.71, "Main Platforms", ha="center", va="center", fontsize=8)
        ax.add_patch(plt.Rectangle((0.6, 0.65), 0.35, 0.12, fill=False))
        ax.text(0.775, 0.71, "Branch Platforms", ha="center", va="center", fontsize=8)
        ax.add_patch(plt.Rectangle((0.1, 0.4), 0.8, 0.15, fill=False))
        ax.text(0.5, 0.475, "Large Concourse", ha="center", va="center", fontsize=8)
        ax.text(0.05, 0.45, "Entry Side", fontsize=7)
        ax.text(0.95, 0.45, "Exit Side", fontsize=7, ha="right")
    elif size == "medium":
        ax.add_patch(plt.Rectangle((0.2, 0.65), 0.6, 0.12, fill=False))
        ax.text(0.5, 0.71, "Platform Zone", ha="center", va="center", fontsize=8)
        ax.add_patch(plt.Rectangle((0.25, 0.4), 0.5, 0.15, fill=False))
        ax.text(0.5, 0.475, "Concourse", ha="center", va="center", fontsize=8)
        ax.text(0.1, 0.45, "Entry A", fontsize=7)
        ax.text(0.9, 0.45, "Exit C", fontsize=7, ha="right")
    else:
        ax.add_patch(plt.Rectangle((0.25, 0.6), 0.5, 0.12, fill=False))
        ax.text(0.5, 0.66, "Platform", ha="center", va="center", fontsize=8)
        ax.add_patch(plt.Rectangle((0.3, 0.4), 0.4, 0.12, fill=False))
        ax.text(0.5, 0.46, "Concourse", ha="center", va="center", fontsize=8)
        ax.text(0.2, 0.42, "Entry", fontsize=7)
        ax.text(0.8, 0.42, "Exit", fontsize=7, ha="right")

    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    return fig

def simulate_station_load(station_name):
    hours = [
        "6-7", "7-8", "8-9", "9-10",
        "10-11", "11-12", "12-13", "13-14",
        "14-15", "15-16", "16-17", "17-18",
        "18-19", "19-20", "20-21"
    ]
    size = get_station_size(station_name)
    if size == "big":
        base = 700
    elif size == "medium":
        base = 450
    else:
        base = 250

    load = []
    for idx in range(len(hours)):
        if 2 <= idx <= 4:      # 8–11 AM peak
            val = base + np.random.randint(300, 450)
        elif 11 <= idx <= 13:  # 5–8 PM peak
            val = base + np.random.randint(300, 450)
        else:
            val = base - np.random.randint(80, 220)
        load.append(max(60, val))
    return pd.DataFrame({"Time": hours, "Passengers": load})

# =====================================================
# SESSION STATE
# =====================================================
if "stage" not in st.session_state:
    st.session_state.stage = "station_selection"
if "selected_line" not in st.session_state:
    st.session_state.selected_line = None
if "selected_station" not in st.session_state:
    st.session_state.selected_station = None
if "selected_start" not in st.session_state:
    st.session_state.selected_start = None
if "selected_end" not in st.session_state:
    st.session_state.selected_end = None
if "base_routes" not in st.session_state:
    st.session_state.base_routes = None
if "locked_shortest_path" not in st.session_state:
    st.session_state.locked_shortest_path = None
if "locked_best_path" not in st.session_state:
    st.session_state.locked_best_path = None
if "live_routes" not in st.session_state:
    st.session_state.live_routes = None
if "crowd_time_base" not in st.session_state:
    st.session_state.crowd_time_base = None
if "station_load_base" not in st.session_state:
    st.session_state.station_load_base = {}
# NEW: path assignment count (per station + start + end + path)
if "path_assign_count" not in st.session_state:
    st.session_state.path_assign_count = {}

# =====================================================
# STAGE 1 – Line & Station selection
# =====================================================
if st.session_state.stage == "station_selection":
    st.subheader("Step 1: Select Metro Line & Station")

    line_names = get_lines()
    if not line_names:
        st.error("No lines found in database. Please check 'stations' table.")
        st.stop()

    label_map, color_labels = {}, []
    for ln in line_names:
        if "Purple" in ln:
            label = f"🟣 {ln}"
        elif "Green" in ln:
            label = f"🟢 {ln}"
        elif "Yellow" in ln:
            label = f"🟡 {ln}"
        else:
            label = ln
        label_map[label] = ln
        color_labels.append(label)

    if st.session_state.selected_line is None:
        default_index = 0
    else:
        inv_map = {v: k for k, v in label_map.items()}
        current_label = inv_map.get(st.session_state.selected_line, color_labels[0])
        default_index = color_labels.index(current_label)

    selected_label = st.radio("🚇 Select Metro Line:", color_labels, index=default_index)
    selected_line = label_map[selected_label]
    st.session_state.selected_line = selected_line

    search_text = st.text_input("🔎 Search station in this line:", value="")
    full_station_list = get_stations(selected_line)
    if not full_station_list:
        st.error(f"No stations found for line: {selected_line}")
        st.stop()

    if search_text.strip():
        station_list = [s for s in full_station_list if search_text.lower() in s.lower()]
        if not station_list:
            st.warning("No station matches your search. Showing all stations in this line.")
            station_list = full_station_list
    else:
        station_list = full_station_list

    station = st.selectbox("🚏 Choose a station on this line:", station_list)

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Next ➡️"):
            st.session_state.selected_station = station
            st.session_state.stage = "route_selection"
            st.session_state.live_routes = None
            st.session_state.crowd_time_base = None
            st.session_state.station_load_base = {}
            st.rerun()
    with col2:
        st.markdown("#### Station Layout Preview")
        st.pyplot(draw_station_layout(station))

# =====================================================
# STAGE 2 – Source & Destination inside station
# =====================================================
elif st.session_state.stage == "route_selection":
    station_name = st.session_state.selected_station
    st.subheader(f"Step 2: Select Source & Destination inside {station_name}")

    locations = get_locations(station_name)
    if not locations:
        st.error("No internal locations found for this station in 'station_locations' table.")
        if st.button("⬅️ Back to Line & Station Selection"):
            st.session_state.stage = "station_selection"
            st.rerun()
        st.stop()

    col1, col2 = st.columns(2)
    with col1:
        start_loc = st.selectbox("📍 Select your current location:", locations, key="start_loc")
    with col2:
        end_loc = st.selectbox("🎯 Select your destination:", locations, key="end_loc")

    if start_loc == end_loc:
        st.warning("⚠️ Source and destination cannot be the same.")
    else:
        if st.button("Show Available Paths 🛤️"):
            st.session_state.selected_start = start_loc
            st.session_state.selected_end = end_loc

            base_df = get_routes(station_name, start_loc, end_loc)
            if base_df.empty:
                st.error("No predefined walking paths found for this source-destination pair in 'routes' table.")
            else:
                st.session_state.base_routes = base_df

                # shortest by distance (fixed)
                shortest_idx = base_df["Base Distance (m)"].idxmin()
                shortest = base_df.loc[shortest_idx]
                st.session_state.locked_shortest_path = shortest.to_dict()

                # best path initially unknown – will be set using live time
                st.session_state.locked_best_path = None

                # reset per-route live data
                st.session_state.live_routes = None
                st.session_state.crowd_time_base = None
                st.session_state.station_load_base = {}

                st.session_state.stage = "results"
                st.rerun()

    if st.button("⬅️ Back to Line & Station Selection"):
        st.session_state.stage = "station_selection"
        st.rerun()

# =====================================================
# STAGE 3 – Results (real-time graphs, frozen table)
# =====================================================
elif st.session_state.stage == "results":
    st_autorefresh(interval=3000, key="auto_refresh_results")

    station_name = st.session_state.selected_station
    start_loc = st.session_state.selected_start
    end_loc = st.session_state.selected_end
    base_df = st.session_state.base_routes
    st.subheader(f"Step 3: Paths from '{start_loc}' → '{end_loc}' at {station_name}")

    if base_df is None or base_df.empty:
        st.error("⚠️ No routes found for this combination in DB.")
    else:
        # ---------- FROZEN TABLE + BEST PATH (MIN LIVE TIME) ----------
        if st.session_state.live_routes is None:
            df_live = base_df.copy()

            live_crowd_list = []
            for _, row in df_live.iterrows():
                path_name = row["Path"]
                base_random = np.random.randint(30, 70)
                key = (station_name, start_loc, end_loc, path_name)
                past_assignments = st.session_state.path_assign_count.get(key, 0)
                crowd = base_random + past_assignments * 8   # +8% per previous assignment
                crowd = int(np.clip(crowd, 5, 95))
                live_crowd_list.append(crowd)

            df_live["Live Crowd (%)"] = [f"{c}%" for c in live_crowd_list]
            df_live["Live Estimated Time (mins)"] = (
                df_live["Base Time (mins)"] * (1 + (np.array(live_crowd_list) / 100))
            ).round(1)

            st.session_state.live_routes = df_live

            # choose best path based on minimum live estimated time
            best_idx = df_live["Live Estimated Time (mins)"].astype(float).idxmin()
            locked_best = df_live.loc[best_idx].to_dict()
            st.session_state.locked_best_path = locked_best

            # increment assignment count for this chosen path
            best_key = (station_name, start_loc, end_loc, locked_best["Path"])
            st.session_state.path_assign_count[best_key] = \
                st.session_state.path_assign_count.get(best_key, 0) + 1
        else:
            df_live = st.session_state.live_routes.copy()
            locked_best = st.session_state.locked_best_path
        # ---------------------------------------------------------------

        best_name = locked_best["Path"] if locked_best else None

        def highlight_best(row):
            if best_name and row["Path"] == best_name:
                return ['background-color: #1b5e20; color: #ffffff; font-weight: bold;'
                        for _ in row]
            else:
                return ['' for _ in row]

        styled_df = df_live.style.apply(highlight_best, axis=1)
        st.markdown("### 🛤️ All Possible Paths (Frozen Assignment for This User)")
        st.dataframe(styled_df, use_container_width=True)

        # shortest path (fixed)
        locked_short = st.session_state.locked_shortest_path
        st.info(
            f"📏 SHORTEST PATH (FIXED): {locked_short['Path']} | "
            f"{locked_short['Base Distance (m)']} m | "
            f"{locked_short['Base Time (mins)']} mins"
        )

        # assigned best path (min live time when user came)
        st.success(
            f"✅ ASSIGNED USER PATH (FIXED – MIN LIVE TIME): {locked_best['Path']} | "
            f"Base Distance: {locked_best['Base Distance (m)']} m | "
            f"Base Time: {locked_best['Base Time (mins)']} mins | "
            f"Initial Live Time: {locked_best['Live Estimated Time (mins)']} mins"
        )

        # path details
        st.markdown("### 🔍 View Details of a Specific Path")
        selected_path_name = st.selectbox(
            "Select a path to view its details:",
            df_live["Path"].tolist()
        )
        sel_row = df_live[df_live["Path"] == selected_path_name].iloc[0]
        st.write(
            f"**Path:** {sel_row['Path']}  \n"
            f"**Base Distance:** {sel_row['Base Distance (m)']} m  \n"
            f"**Base Time:** {sel_row['Base Time (mins)']} mins  \n"
            f"**Live Crowd (at assignment):** {sel_row['Live Crowd (%)']}  \n"
            f"**Live Estimated Time (at assignment):** {sel_row['Live Estimated Time (mins)']} mins"
        )

        # station layout
        st.markdown("### 🗺 Station Layout (Schematic View)")
        st.pyplot(draw_station_layout(station_name))

        # ============ CROWD VARIATION PER PATH (BAR CHART) ============
        st.markdown("### 📊 Crowd Variation Over the Day (Per Path – Mild Live Update on Last Slot)")

        time_intervals = [
            "6-8 AM", "8-10 AM", "10-12 PM", "12-2 PM",
            "2-4 PM", "4-6 PM", "6-8 PM", "8-10 PM"
        ]

        if st.session_state.crowd_time_base is None:
            crowd_time_base = {}
            for _, row in df_live.iterrows():
                base_val = int(str(row["Live Crowd (%)"]).replace("%", ""))
                pattern = base_val + np.random.randint(-15, 16, size=len(time_intervals))
                pattern = np.clip(pattern, 0, 100)
                crowd_time_base[row["Path"]] = pattern
            st.session_state.crowd_time_base = crowd_time_base

        crowd_matrix = {}
        for path, base_arr in st.session_state.crowd_time_base.items():
            arr = base_arr.copy()
            arr[-1] = int(np.clip(arr[-1] + np.random.randint(-5, 6), 0, 100))
            crowd_matrix[path] = arr

        df_time = pd.DataFrame(crowd_matrix, index=time_intervals)
        fig1, ax1 = plt.subplots(figsize=(10, 5))
        df_time.plot(kind="bar", ax=ax1)
        ax1.set_ylabel("Crowd Density (%)")
        ax1.set_xlabel("Time Intervals")
        ax1.set_title(f"Crowd Variation for Paths from '{start_loc}' → '{end_loc}'")
        st.pyplot(fig1)

        # ============ STATION-LEVEL PASSENGER LOAD (LINE CHART) ============
        st.markdown("### 🚦 Station-Level Passenger Load (Last Point Mildly Updating)")

        if station_name not in st.session_state.station_load_base:
            st.session_state.station_load_base[station_name] = simulate_station_load(station_name)

        df_load_base = st.session_state.station_load_base[station_name].copy()
        last_idx = df_load_base.index[-1]
        df_load_base.loc[last_idx, "Passengers"] = max(
            50,
            df_load_base.loc[last_idx, "Passengers"] + np.random.randint(-25, 26)
        )

        fig2, ax2 = plt.subplots(figsize=(10, 3))
        ax2.plot(df_load_base["Time"], df_load_base["Passengers"], marker="o")
        ax2.set_xlabel("Time (Hours)")
        ax2.set_ylabel("Passengers")
        ax2.set_title(f"Passenger Load at {station_name}")
        ax2.grid(True)
        st.pyplot(fig2)

    # ---------- navigation buttons ----------
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔁 Choose Another Source/Destination"):
            st.session_state.stage = "route_selection"
            st.session_state.base_routes = None
            st.session_state.live_routes = None
            st.session_state.crowd_time_base = None
            st.rerun()
    with c2:
        if st.button("🏁 Restart from Line & Station Selection"):
            for key in [
                "selected_station", "selected_start", "selected_end",
                "base_routes", "locked_shortest_path", "locked_best_path",
                "live_routes", "crowd_time_base"
            ]:
                st.session_state[key] = None
            # we *keep* path_assign_count so system remembers past users
            st.session_state.station_load_base = {}
            st.session_state.stage = "station_selection"
            st.rerun()
