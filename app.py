import io
import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from datetime import datetime, date, time, timedelta

from database.auth import register_user, login_user
from database.admin_ops import (
    add_bus, get_all_buses, 
    add_route, get_all_routes, 
    add_trip, get_all_trips, search_trips,
    get_analytics_metrics, get_all_bookings_report
)
from database.booking_ops import (
    get_booked_seats, book_ticket_with_payment, 
    get_user_bookings, generate_ticket_qr, cancel_ticket
)
from database.tracking_ops import (
    update_bus_location, get_latest_bus_location, 
    CITY_COORDINATES
)

st.set_page_config(page_title="SmartBus System", page_icon="🚌", layout="wide")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = None

if "selected_trip" not in st.session_state:
    st.session_state.selected_trip = None

def logout():
    st.session_state.logged_in = False
    st.session_state.user = None
    st.session_state.selected_trip = None
    st.rerun()

# ----------------- MAIN APP LOGIC -----------------
if not st.session_state.logged_in:
    st.markdown("<h1 style='text-align: center;'>🚌 SmartBus Booking & Tracking System</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: gray;'>Secure Online Bus Reservation Platform</p>", unsafe_allow_html=True)
    st.divider()

    tab_login, tab_register = st.tabs(["🔐 Login", "📝 Register"])

    with tab_login:
        st.subheader("Login to your account")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            login_email = st.text_input("Email Address", key="login_email")
            login_pass = st.text_input("Password", type="password", key="login_pass")
            
            if st.button("Login", use_container_width=True, type="primary"):
                if not login_email or not login_pass:
                    st.error("Kripya dono fields bharein!")
                else:
                    user, msg = login_user(login_email, login_pass)
                    if user:
                        st.session_state.logged_in = True
                        st.session_state.user = user
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

    with tab_register:
        st.subheader("Create a New Account")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            reg_name = st.text_input("Full Name")
            reg_email = st.text_input("Email Address")
            reg_phone = st.text_input("Phone Number")
            reg_pass = st.text_input("Create Password", type="password")
            reg_confirm_pass = st.text_input("Confirm Password", type="password")
            reg_role = st.selectbox("Role", ["Passenger", "Admin"])

            if st.button("Create Account", use_container_width=True, type="primary"):
                if not reg_name or not reg_email or not reg_phone or not reg_pass:
                    st.error("Kripya saare fields bharein!")
                elif reg_pass != reg_confirm_pass:
                    st.error("Passwords match nahi ho rahe hain!")
                elif len(reg_pass) < 6:
                    st.error("Password kam se kam 6 characters ka hona chahiye!")
                else:
                    success, msg = register_user(reg_name, reg_email, reg_phone, reg_pass, reg_role)
                    if success:
                        st.success(msg)
                        st.info("Ab aap 'Login' tab me jaakar login kar sakte hain.")
                    else:
                        st.error(msg)

else:
    current_user = st.session_state.user
    
    # Sidebar
    with st.sidebar:
        st.title(f"👤 {current_user['full_name']}")
        st.caption(f"Role: **{current_user['role']}**")
        st.caption(f"Email: {current_user['email']}")
        st.divider()
        if st.button("Logout", type="secondary", use_container_width=True):
            logout()

    # ----------------- ADMIN DASHBOARD -----------------
    if str(current_user["role"]).strip().lower() == "admin":
        st.title("🛠️ Admin Operations & Analytics Hub")
        
        tab_analytics, tab_buses, tab_routes, tab_trips, tab_gps, tab_reports = st.tabs([
            "📊 Analytics", "🚌 Manage Buses", "🗺️ Manage Routes", 
            "🗓️ Schedule Trips", "📍 GPS Simulator", "📑 Excel Reports"
        ])
        
        # 1. Analytics Tab
        with tab_analytics:
            st.subheader("System Performance & Overview")
            metrics = get_analytics_metrics()
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Total Revenue Collected", f"₹{metrics['total_revenue']:,}")
            m2.metric("Confirmed Bookings", f"{metrics['total_bookings']}")
            m3.metric("Fleet in Operation", f"{metrics['active_buses']} Buses")
            st.divider()
            
            # Booking trends chart
            df_rep = get_all_bookings_report()
            if not df_rep.empty:
                st.write("### Route Popularity (Bookings by Destination)")
                route_counts = df_rep[df_rep["Booking Status"] == "Confirmed"]["Destination"].value_counts()
                if not route_counts.empty:
                    st.bar_chart(route_counts)
                else:
                    st.info("No confirmed bookings yet.")
            else:
                st.info("No bookings recorded yet.")

        # 2. Manage Buses
        with tab_buses:
            st.subheader("Add New Bus")
            with st.form("add_bus_form", clear_on_submit=True):
                col_b1, col_b2 = st.columns(2)
                with col_b1:
                    b_num = st.text_input("Bus Number (e.g. MH-12-AB-1234)")
                    b_name = st.text_input("Bus Name / Travels (e.g. Shivneri Express)")
                    b_type = st.selectbox("Bus Type", ["Seater", "Sleeper", "Semi-Sleeper", "Volvo Multi-Axle"])
                with col_b2:
                    b_seats = st.number_input("Total Seats", min_value=10, max_value=60, value=40, step=1)
                    st.write("**Facilities:**")
                    b_ac = st.checkbox("Air Conditioner (AC)", value=True)
                    b_wifi = st.checkbox("High-Speed Wi-Fi", value=True)
                    b_charging = st.checkbox("Charging Points", value=True)
                
                if st.form_submit_button("Add Bus", type="primary"):
                    if not b_num or not b_name:
                        st.error("Bus Number aur Bus Name required hain!")
                    else:
                        ok, msg = add_bus(b_num, b_name, b_type, b_seats, b_ac, b_wifi, b_charging)
                        if ok:
                            st.success(msg)
                        else:
                            st.error(msg)
            
            st.divider()
            st.subheader("Available Buses List")
            df_buses = get_all_buses()
            if not df_buses.empty:
                st.dataframe(df_buses, use_container_width=True)

        # 3. Manage Routes
        with tab_routes:
            st.subheader("Add New Route")
            with st.form("add_route_form", clear_on_submit=True):
                col_r1, col_r2 = st.columns(2)
                with col_r1:
                    r_source = st.text_input("Source City (Origin, e.g. Shirpur)")
                    r_dest = st.text_input("Destination City (e.g. Pune)")
                with col_r2:
                    r_dist = st.number_input("Distance (in km)", min_value=1.0, value=390.0, step=1.0)
                    r_time = st.number_input("Estimated Time (in minutes)", min_value=10, value=480, step=10)
                    r_fare = st.number_input("Base Fare (₹)", min_value=10.0, value=650.0, step=10.0)
                
                if st.form_submit_button("Add Route", type="primary"):
                    if not r_source or not r_dest:
                        st.error("Source aur Destination required hain!")
                    else:
                        ok, msg = add_route(r_source, r_dest, r_dist, r_time, r_fare)
                        if ok:
                            st.success(msg)
                        else:
                            st.error(msg)
            
            st.divider()
            st.subheader("Available Routes List")
            df_routes = get_all_routes()
            if not df_routes.empty:
                st.dataframe(df_routes, use_container_width=True)

        # 4. Schedule Trips
        with tab_trips:
            st.subheader("🗓️ Schedule a New Trip")
            df_buses = get_all_buses()
            df_routes = get_all_routes()
            
            if df_buses.empty or df_routes.empty:
                st.warning("Pehle kam se kam ek Bus aur ek Route hona zaroori hai.")
            else:
                bus_dict = {f"{row['bus_name']} ({row['bus_number']}) - {row['bus_type']}": row['bus_id'] for _, row in df_buses.iterrows()}
                route_dict = {f"{row['source']} ➡️ {row['destination']} (₹{row['base_fare']})": (row['route_id'], row['estimated_minutes']) for _, row in df_routes.iterrows()}
                
                with st.form("schedule_trip_form", clear_on_submit=True):
                    col_t1, col_t2 = st.columns(2)
                    with col_t1:
                        selected_bus = st.selectbox("Select Bus", list(bus_dict.keys()))
                        trip_date = st.date_input("Departure Date", min_value=date.today())
                        trip_dep_time = st.time_input("Departure Time", value=time(21, 0))
                    with col_t2:
                        selected_route = st.selectbox("Select Route", list(route_dict.keys()))
                        st.info("Arrival time route ke estimated minutes ke basis par auto-calculate hoga.")
                    
                    if st.form_submit_button("Schedule Trip", type="primary"):
                        chosen_bus_id = bus_dict[selected_bus]
                        chosen_route_id, est_min = route_dict[selected_route]
                        
                        dep_datetime = datetime.combine(trip_date, trip_dep_time)
                        arr_datetime = dep_datetime + timedelta(minutes=int(est_min))
                        
                        ok, msg = add_trip(chosen_bus_id, chosen_route_id, dep_datetime, arr_datetime)
                        if ok:
                            st.success(f"{msg} (Arrival: {arr_datetime.strftime('%Y-%m-%d %I:%M %p')})")
                        else:
                            st.error(msg)
                
                st.divider()
                st.subheader("Scheduled Trips List")
                df_trips = get_all_trips()
                if not df_trips.empty:
                    st.dataframe(df_trips, use_container_width=True)

        # 5. GPS Simulator
        with tab_gps:
            st.subheader("📍 Update Bus Live GPS Location")
            df_buses = get_all_buses()
            if df_buses.empty:
                st.warning("Pehle buses add karein.")
            else:
                bus_sel_dict = {f"{r['bus_name']} ({r['bus_number']})": r['bus_id'] for _, r in df_buses.iterrows()}
                chosen_bus_name = st.selectbox("Select Bus to Transmit GPS", list(bus_sel_dict.keys()))
                chosen_bus_id = bus_sel_dict[chosen_bus_name]
                
                cur_loc = get_latest_bus_location(chosen_bus_id)
                if cur_loc:
                    st.info(f"Last Reported Location: Lat: `{cur_loc['latitude']}`, Lng: `{cur_loc['longitude']}` (Time: {cur_loc['recorded_at']})")
                
                st.write("**Quick Checkpoint Selector**")
                preset_city = st.selectbox("Select City / Checkpoint", list(CITY_COORDINATES.keys()), index=0)
                preset_lat, preset_lng = CITY_COORDINATES[preset_city]
                
                with st.form("update_gps_form"):
                    col_g1, col_g2 = st.columns(2)
                    with col_g1:
                        lat_val = st.number_input("Latitude", value=float(preset_lat), format="%.4f")
                    with col_g2:
                        lng_val = st.number_input("Longitude", value=float(preset_lng), format="%.4f")
                    
                    if st.form_submit_button("Transmit GPS Location 📡", type="primary"):
                        ok, msg = update_bus_location(chosen_bus_id, lat_val, lng_val)
                        if ok:
                            st.success(f"{msg} Location updated to {preset_city.capitalize()} ({lat_val}, {lng_val})")
                            st.rerun()
                        else:
                            st.error(msg)

        # 6. Excel Reports & Backup
        with tab_reports:
            st.subheader("📑 Booking Audit & Excel Reports")
            df_report = get_all_bookings_report()
            
            if df_report.empty:
                st.info("Koi booking data available nahi hai.")
            else:
                st.dataframe(df_report, use_container_width=True)
                
                # Excel Generation with OpenPyXL
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_report.to_excel(writer, index=False, sheet_name='Bookings_Report')
                excel_data = output.getvalue()
                
                st.download_button(
                    label="📥 Download Complete Report (.xlsx)",
                    data=excel_data,
                    file_name=f"SmartBus_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary"
                )

    # ----------------- PASSENGER DASHBOARD -----------------
    else:
        st.title("🧳 Passenger Portal")
        p_tab_search, p_tab_my_bookings, p_tab_track = st.tabs([
            "🔍 Search & Book Buses", "🎟️ My Booked Tickets", "🗺️ Live Bus Tracking"
        ])

        # Tab 1: Search & Book
        with p_tab_search:
            if st.session_state.selected_trip is None:
                df_routes = get_all_routes()
                if df_routes.empty:
                    st.info("Abhi routes available nahi hain.")
                else:
                    sources = sorted(list(set(df_routes["source"].unique())))
                    destinations = sorted(list(set(df_routes["destination"].unique())))
                    
                    with st.container():
                        col_s1, col_s2, col_s3, col_s4 = st.columns([2, 2, 2, 1])
                        with col_s1:
                            src = st.selectbox("From (Origin)", sources)
                        with col_s2:
                            dest = st.selectbox("To (Destination)", destinations)
                        with col_s3:
                            travel_dt = st.date_input("Date of Journey", min_value=date.today())
                        with col_s4:
                            st.write("")
                            st.write("")
                            btn_search = st.button("Search Buses", type="primary", use_container_width=True)
                    
                    st.divider()
                    
                    results = search_trips(src, dest, travel_dt)
                    if btn_search or not results.empty:
                        if results.empty:
                            st.warning(f"'{src}' se '{dest}' ke liye {travel_dt.strftime('%d-%b-%Y')} ko koi bus schedule nahi hai.")
                        else:
                            st.success(f"**{len(results)} Buses Found** for {src} ➡️ {dest} on {travel_dt.strftime('%d-%b-%Y')}")
                            
                            for _, row in results.iterrows():
                                dep_t = pd.to_datetime(row['departure_time']).strftime('%I:%M %p')
                                arr_t = pd.to_datetime(row['arrival_time']).strftime('%I:%M %p')
                                
                                fac_list = []
                                if row['ac']: fac_list.append("❄️ AC")
                                if row['wifi']: fac_list.append("📶 Wi-Fi")
                                if row['charging_point']: fac_list.append("🔌 Charging")
                                fac_str = " | ".join(fac_list) if fac_list else "Basic Non-AC"
                                
                                with st.container():
                                    c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
                                    with c1:
                                        st.markdown(f"### {row['bus_name']}")
                                        st.caption(f"**{row['bus_number']}** • {row['bus_type']}")
                                        st.write(fac_str)
                                    with c2:
                                        st.markdown(f"**Departure:** {dep_t}")
                                        st.markdown(f"**Arrival:** {arr_t}")
                                        st.caption(f"Duration: {row['estimated_minutes'] // 60}h {row['estimated_minutes'] % 60}m")
                                    with c3:
                                        st.markdown(f"### ₹{row['base_fare']}")
                                        st.caption(f"Total Capacity: {row['total_seats']} seats")
                                    with c4:
                                        st.write("")
                                        if st.button("Select Seat 💺", key=f"btn_trip_{row['trip_id']}", use_container_width=True, type="primary"):
                                            st.session_state.selected_trip = row.to_dict()
                                            st.rerun()
                                    st.divider()
            
            else:
                trip = st.session_state.selected_trip
                
                col_back, col_title = st.columns([1, 6])
                with col_back:
                    if st.button("⬅️ Change Bus"):
                        st.session_state.selected_trip = None
                        st.rerun()
                with col_title:
                    st.subheader(f"💺 Select Seat: {trip['bus_name']} ({trip['source']} ➡️ {trip['destination']})")
                
                booked_seats = get_booked_seats(trip['trip_id'])
                total_seats = int(trip['total_seats'])
                available_seats = [f"S{i}" for i in range(1, total_seats + 1) if f"S{i}" not in booked_seats]

                col_layout, col_pay = st.columns([3, 2])
                
                with col_layout:
                    st.write("### Bus Seat Map")
                    st.caption("🔴 Red = Booked | 🟢 Green = Available")
                    
                    cols_per_row = 4
                    for row_start in range(1, total_seats + 1, cols_per_row):
                        seat_row = st.columns(cols_per_row)
                        for idx, c in enumerate(seat_row):
                            seat_num = row_start + idx
                            if seat_num <= total_seats:
                                s_label = f"S{seat_num}"
                                if s_label in booked_seats:
                                    c.error(f"🔴 {s_label}")
                                else:
                                    c.success(f"🟢 {s_label}")
                
                with col_pay:
                    st.write("### Booking & Payment")
                    st.info(f"**Fare per seat:** ₹{trip['base_fare']}")
                    
                    if not available_seats:
                        st.error("⚠️ Is bus me sabhi seats book ho chuki hain!")
                    else:
                        chosen_seat = st.selectbox("Choose Available Seat", available_seats)
                        pay_method = st.selectbox("Payment Method", ["UPI / QR Code", "Debit Card", "Net Banking", "Cash on Board"])
                        
                        if st.button("Confirm Booking & Pay ₹" + str(trip['base_fare']), type="primary", use_container_width=True):
                            success, msg, ticket = book_ticket_with_payment(
                                user_id=current_user['user_id'],
                                trip_id=trip['trip_id'],
                                seat_number=chosen_seat,
                                fare=trip['base_fare'],
                                payment_method=pay_method
                            )
                            if success:
                                st.balloons()
                                st.success(f"🎉 {msg}")
                                st.session_state.selected_trip = None
                                st.rerun()
                            else:
                                st.error(msg)

        # Tab 2: My Booked Tickets & QR Code
        with p_tab_my_bookings:
            st.subheader("🎟️ My Booked Tickets")
            my_bookings = get_user_bookings(current_user['user_id'])
            
            if my_bookings.empty:
                st.info("Aapne abhi tak koi ticket book nahi kiya hai.")
            else:
                for _, b in my_bookings.iterrows():
                    with st.container():
                        b_c1, b_c2, b_c3 = st.columns([3, 2, 2])
                        with b_c1:
                            st.markdown(f"### Ticket: `{b['ticket_code']}`")
                            st.write(f"**Bus:** {b['bus_name']} ({b['bus_number']})")
                            st.write(f"**Route:** {b['source']} ➡️ {b['destination']}")
                            dep_str = pd.to_datetime(b['departure_time']).strftime('%d-%b-%Y %I:%M %p')
                            st.caption(f"Departure: {dep_str}")
                        with b_c2:
                            st.metric("Seat Number", b['seat_number'])
                            st.write(f"**Fare Paid:** ₹{b['fare']}")
                            status_color = ":green" if b['status'] == "Confirmed" else ":red"
                            st.write(f"**Status:** {status_color}[{b['status']}]")
                            
                            # Cancel Ticket Button (only if confirmed)
                            if b['status'] == "Confirmed":
                                if st.button("Cancel Ticket ❌", key=f"cancel_{b['booking_id']}"):
                                    c_ok, c_msg = cancel_ticket(b['booking_id'])
                                    if c_ok:
                                        st.warning(c_msg)
                                        st.rerun()
                                    else:
                                        st.error(c_msg)
                        with b_c3:
                            if b['status'] == "Confirmed":
                                st.write("**Ticket QR Code:**")
                                qr_payload = f"SMARTBUS_TICKET|CODE:{b['ticket_code']}|PASSENGER:{current_user['full_name']}|SEAT:{b['seat_number']}|FARE:{b['fare']}"
                                qr_bytes = generate_ticket_qr(qr_payload)
                                st.image(qr_bytes, width=150)
                            else:
                                st.error("❌ TICKET CANCELLED")
                        st.divider()

        # Tab 3: Live Bus Tracking & Route Map
        with p_tab_track:
            st.subheader("🗺️ Live Bus GPS Tracking & Route Map")
            df_buses = get_all_buses()
            
            if df_buses.empty:
                st.info("Buses available nahi hain.")
            else:
                bus_track_dict = {f"{r['bus_name']} ({r['bus_number']})": r['bus_id'] for _, r in df_buses.iterrows()}
                bus_picked = st.selectbox("Select Bus to Track Live", list(bus_track_dict.keys()), key="track_bus_choice")
                b_id = bus_track_dict[bus_picked]
                
                loc_data = get_latest_bus_location(b_id)
                
                center_lat = loc_data['latitude'] if loc_data else 21.3500
                center_lng = loc_data['longitude'] if loc_data else 74.8800
                
                m = folium.Map(location=[center_lat, center_lng], zoom_start=8)
                
                if loc_data:
                    folium.Marker(
                        location=[loc_data['latitude'], loc_data['longitude']],
                        popup=f"🚌 <b>{bus_picked}</b><br>Live GPS: ({loc_data['latitude']}, {loc_data['longitude']})<br>Last Updated: {loc_data['recorded_at']}",
                        tooltip="Bus Current Location",
                        icon=folium.Icon(color="red", icon="bus", prefix="fa")
                    ).add_to(m)
                    
                    st.success(f"📍 **{bus_picked}** is currently near Lat: `{loc_data['latitude']}`, Lng: `{loc_data['longitude']}` (Updated: {loc_data['recorded_at']})")
                else:
                    st.warning("Is bus ki live GPS location abhi transmit nahi hui hai.")
                
                route_line = [
                    CITY_COORDINATES["shirpur"],
                    CITY_COORDINATES["dhule"],
                    CITY_COORDINATES["malegaon"],
                    CITY_COORDINATES["nashik"],
                    CITY_COORDINATES["pune"]
                ]
                folium.PolyLine(route_line, color="blue", weight=4, opacity=0.7, tooltip="Highway Route NH52 / NH60").add_to(m)
                
                for city, coords in [("Shirpur (Start)", CITY_COORDINATES["shirpur"]), ("Nashik (Mid)", CITY_COORDINATES["nashik"]), ("Pune (End)", CITY_COORDINATES["pune"])]:
                    folium.CircleMarker(
                        location=coords,
                        radius=6,
                        popup=city,
                        color="darkblue",
                        fill=True,
                        fill_color="blue"
                    ).add_to(m)
                
                st_folium(m, width=950, height=480)