import os
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Semester Dashboard",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="apple-mobile-web-app-title" content="Semester">
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <link rel="apple-touch-icon" href="static/apple-touch-icons.png">
    """,
    unsafe_allow_html=True,
)

CSV_PATH = "data/classes.csv"

DAYS = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]

TYPE_COLORS = {
    "Lecture": "#4f8ef7",
    "Exercise": "#2ca02c",
    "Lab": "#ff7f0e",
    "Seminar": "#9467bd",
    "Tutorial": "#8c564b",
    "Course": "#d62728",
}


@st.cache_data
def load_classes(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)

    required = {
        "course", "type", "day", "start", "end", "location_code", "room",
        "building_name", "address", "building_number", "floor", "map_link",
        "status", "priority", "attendance",
    }

    missing = required - set(df.columns)
    if missing:
        st.error(f"Missing columns in classes.csv: {', '.join(missing)}")
        st.stop()

    df["start_time"] = pd.to_datetime(df["start"], format="%H:%M").dt.time
    df["end_time"] = pd.to_datetime(df["end"], format="%H:%M").dt.time
    df["day"] = pd.Categorical(df["day"], categories=DAYS, ordered=True)

    return df


def format_duration(start_time, end_time):
    start = timedelta(hours=start_time.hour, minutes=start_time.minute)
    end = timedelta(hours=end_time.hour, minutes=end_time.minute)

    minutes = int((end - start).total_seconds() // 60)
    hours, mins = divmod(minutes, 60)

    if hours and mins:
        return f"{hours} h {mins} min"
    if hours:
        return f"{hours} h"

    return f"{mins} min"


def class_card(row, highlight=False):
    color = TYPE_COLORS.get(row["type"], "#607d8b")

    with st.container(border=True):
        cols = st.columns([0.18, 0.52, 0.30])

        cols[0].markdown(
            f"""
            <div style="
                background:{color};
                color:white;
                padding:0.6rem;
                border-radius:0.6rem;
                text-align:center;
                font-weight:700;
            ">
                {row['start']}<br>{row['end']}
            </div>
            """,
            unsafe_allow_html=True,
        )

        cols[1].markdown(
            f"""
            #### {row['course']}  
            `{row['type']}` • {format_duration(row['start_time'], row['end_time'])}  
            **{row['building_name']}** — Room `{row['room']}`  
            Location code: `{row['location_code']}`
            """,
        )

        details = []

        if pd.notna(row["address"]) and str(row["address"]).strip():
            details.append(f"📍 {row['address']}")

        if pd.notna(row["floor"]) and str(row["floor"]).strip():
            details.append(f"🏢 {row['floor']}")

        if pd.notna(row["building_number"]) and str(row["building_number"]).strip():
            details.append(f"🔢 Building no. {row['building_number']}")

        if pd.notna(row["priority"]) and str(row["priority"]).strip():
            details.append(f"⭐ Priority: **{row['priority']}**")

        if row["attendance"] != "Attend":
            details.append(f"⚠️ {row['attendance']}")

        cols[1].markdown("<br>".join(details))

        if pd.notna(row["map_link"]) and str(row["map_link"]).startswith("http"):
            cols[2].link_button(
                "Open in Google Maps",
                row["map_link"],
                use_container_width=True,
            )


def next_class_card(today_df):
    now = datetime.now().time()

    upcoming = today_df[
        (today_df["attendance"] == "Attend")
        & (today_df["start_time"] >= now)
    ].sort_values("start_time")

    if upcoming.empty:
        st.info("No more attended classes today. 🎉")
        return

    row = upcoming.iloc[0]

    now_dt = datetime.combine(datetime.today(), now)
    start_dt = datetime.combine(datetime.today(), row["start_time"])
    minutes_left = int((start_dt - now_dt).total_seconds() // 60)

    if minutes_left <= 0:
        message = "Starting now"
    elif minutes_left < 60:
        message = f"Starts in {minutes_left} min"
    else:
        hours, mins = divmod(minutes_left, 60)
        message = f"Starts in {hours} h {mins} min"

    st.success(
        f"""
        **Next class:** {row['course']} — {row['type']}  
        **{row['start']}–{row['end']}** • {message}  
        **Where:** {row['building_name']}, Room {row['room']}
        """
    )


df = load_classes(CSV_PATH)

today_name = datetime.now().strftime("%A")
tomorrow_name = (datetime.now() + timedelta(days=1)).strftime("%A")

today_df = df[df["day"] == today_name].copy()
attended_today = today_df[
    today_df["attendance"] == "Attend"
].sort_values("start_time")

conflicts_today = today_df[
    today_df["attendance"] != "Attend"
].sort_values("start_time")

with st.sidebar:
    st.title("🎓 Semester Dashboard")
    st.caption("Your TU Dresden semester schedule")

    st.divider()

    st.subheader("Filters")

    selected_types = st.multiselect(
        "Class type",
        options=sorted(df["type"].dropna().unique()),
        default=sorted(df["type"].dropna().unique()),
    )

    show_only_attend = st.toggle(
        "Show only classes I plan to attend",
        value=True,
    )

    st.divider()

    st.subheader("Quick stats")

    st.metric("Total sessions", len(df))
    st.metric("Courses", df["course"].nunique())
    st.metric("Today’s classes", len(attended_today))
    st.metric("Conflict sessions", (df["attendance"] != "Attend").sum())

    st.divider()

    st.caption(
        "Data source: `data/classes.csv`. "
        "Update the CSV and refresh this page to see changes."
    )

filtered_df = df[df["type"].isin(selected_types)].copy()

if show_only_attend:
    filtered_df = filtered_df[filtered_df["attendance"] == "Attend"]

tab_today, tab_tomorrow, tab_week, tab_locations, tab_conflicts, tab_data = st.tabs(
    [
        "📅 Today",
        "⏭ Tomorrow",
        "🗓 Weekly timetable",
        "📍 Buildings",
        "⚠️ Conflicts",
        "📊 All data",
    ]
)

with tab_today:
    st.header(f"Today — {today_name}")

    if attended_today.empty:
        st.info("No classes you plan to attend today.")
    else:
        next_class_card(attended_today)

        st.subheader("Schedule")

        for _, row in attended_today.iterrows():
            class_card(row)

    if not conflicts_today.empty and not show_only_attend:
        st.subheader("Lower-priority sessions today")
        st.caption("These overlap with a class you marked as higher priority.")

        for _, row in conflicts_today.iterrows():
            class_card(row, highlight=True)

with tab_tomorrow:
    st.header(f"Tomorrow — {tomorrow_name}")

    tomorrow_df = filtered_df[filtered_df["day"] == tomorrow_name].copy()

    tomorrow_attended = tomorrow_df[
        tomorrow_df["attendance"] == "Attend"
    ].sort_values("start_time")

    tomorrow_conflicts = tomorrow_df[
        tomorrow_df["attendance"] != "Attend"
    ].sort_values("start_time")

    if tomorrow_attended.empty:
        st.info("No classes you plan to attend tomorrow.")
    else:
        first_class = tomorrow_attended.iloc[0]

        st.success(
            f"""
            **First class tomorrow:** {first_class['course']} — {first_class['type']}  
            **{first_class['start']}–{first_class['end']}**  
            **Where:** {first_class['building_name']}, Room {first_class['room']}
            """
        )

        st.subheader("Schedule")

        for _, row in tomorrow_attended.iterrows():
            class_card(row)

    if not tomorrow_conflicts.empty and not show_only_attend:
        st.subheader("Lower-priority sessions tomorrow")
        st.caption("These overlap with a class you marked as higher priority.")

        for _, row in tomorrow_conflicts.iterrows():
            class_card(row, highlight=True)

with tab_week:
    st.header("Weekly timetable")

    week_df = filtered_df.sort_values(["day", "start_time"])

    if week_df.empty:
        st.info("No classes match the current filters.")
    else:
        for day in DAYS:
            day_df = week_df[week_df["day"] == day]

            if day_df.empty:
                continue

            st.subheader(day)

            if day == today_name:
                st.caption("Today")

            for _, row in day_df.iterrows():
                class_card(row)

with tab_locations:
    st.header("Buildings and rooms")

    location_df = (
        filtered_df.groupby(
            ["building_name", "address", "building_number", "map_link"],
            dropna=False,
        )
        .agg(
            sessions=("course", "count"),
            courses=("course", lambda x: ", ".join(sorted(x.unique()))),
        )
        .reset_index()
        .sort_values("building_name")
    )

    for _, row in location_df.iterrows():
        with st.container(border=True):
            cols = st.columns([0.7, 0.3])

            cols[0].markdown(
                f"""
                #### {row['building_name'] or 'Unknown building'}  
                {row['address'] if pd.notna(row['address']) and str(row['address']).strip() else 'Address not available'}  
                **Sessions:** {row['sessions']}  
                **Courses:** {row['courses']}
                """
            )

            if pd.notna(row["map_link"]) and str(row["map_link"]).startswith("http"):
                cols[1].link_button(
                    "Open map",
                    row["map_link"],
                    use_container_width=True,
                )

with tab_conflicts:
    st.header("Schedule conflicts")

    conflict_df = df[df["attendance"] != "Attend"].sort_values(
        ["day", "start_time"]
    )

    if conflict_df.empty:
        st.success("No conflicts in your current schedule.")
    else:
        st.warning(
            "These sessions overlap with another class that you marked as higher priority."
        )

        for day in DAYS:
            day_conflicts = conflict_df[conflict_df["day"] == day]

            if day_conflicts.empty:
                continue

            st.subheader(day)

            for _, row in day_conflicts.iterrows():
                class_card(row, highlight=True)

with tab_data:
    st.header("All class data")

    st.dataframe(
        df.drop(columns=["start_time", "end_time"]),
        use_container_width=True,
        hide_index=True,
        column_config={
            "map_link": st.column_config.LinkColumn("Map"),
            "course": st.column_config.TextColumn("Course"),
            "type": st.column_config.TextColumn("Type"),
            "day": st.column_config.TextColumn("Day"),
            "start": st.column_config.TextColumn("Start"),
            "end": st.column_config.TextColumn("End"),
            "location_code": st.column_config.TextColumn("Location"),
            "room": st.column_config.TextColumn("Room"),
            "building_name": st.column_config.TextColumn("Building"),
            "address": st.column_config.TextColumn("Address"),
            "building_number": st.column_config.TextColumn("Building no."),
            "floor": st.column_config.TextColumn("Floor"),
            "status": st.column_config.TextColumn("Status"),
            "priority": st.column_config.TextColumn("Priority"),
            "attendance": st.column_config.TextColumn("Attendance"),
        },
    )

    csv_bytes = (
        df.drop(columns=["start_time", "end_time"])
        .to_csv(index=False)
        .encode("utf-8")
    )

    st.download_button(
        label="Download current schedule as CSV",
        data=csv_bytes,
        file_name="classes.csv",
        mime="text/csv",
    )