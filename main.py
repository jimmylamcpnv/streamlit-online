"""
Author      : Jimmy LAM
github      : https://github.com/jimmylamcpnv/pre-tpi
Date        : 05.02.2026
Version     : v1

Description : Make a web app in streamlit for a warranty checker/monitoring with camera ocr
website     : serial-guard.streamlit.app
"""

# ── Imports ──────────────────────────────────────────────────────────────────
import re
from datetime import date, datetime
from typing import Iterable

import numpy as np
import pandas as pd
import streamlit as st
from PIL import Image
from doctr.models import ocr_predictor
from supabase import Client, create_client


# ══════════════════════════════════════════════════════════════════════════════
#  DATABASE
# ══════════════════════════════════════════════════════════════════════════════

######################################
############## Config ###############
######################################

# create the supabase client
url = "https://nsbfvaghqvgdiiizclst.supabase.co"
key = "sb_publishable_uN4WtLAtQWu3AoeTbKZQpA_USXH8wsM"
supabase: Client = create_client(url, key)


#######################################
############## Devices ###############
#######################################

# delete one device by serial number
def delete_device(serial_number):
    respons = (
        supabase.table("devices")
        .delete()
        .eq("serial_number", serial_number)
        .execute()
    )
    return respons


# add one device to the database
def add_device(
    name_val,
    serial_val,
    manufacturer,
    assigned_user_str,
    tags,
    purchase_date,
    warranty_period_val,
):
    data = {
        "device_name": name_val,
        "serial_number": serial_val,
        "manufacturer": manufacturer,
        "assigned_user": assigned_user_str,
        "tags": tags,
        "purchase_date": purchase_date.isoformat() if purchase_date else None,
        "warranty_period": warranty_period_val,
    }

    response = supabase.table("devices").insert(data).execute()
    return response


# update one device with new values
def update_device(
    original_serial,
    device_name,
    serial_number,
    manufacturer,
    assigned_user,
    tags,
    purchase_date,
    warranty_period,
):
    tags_val = tags if isinstance(tags, list) else [tags]

    response = (
        supabase.table("devices")
        .update(
            {
                "device_name": device_name,
                "serial_number": serial_number,
                "manufacturer": manufacturer,
                "assigned_user": assigned_user,
                "tags": tags_val,
                "purchase_date": str(purchase_date),  # supabase expects a string here
                "warranty_period": warranty_period,
            }
        )
        .eq("serial_number", original_serial)
        .execute()
    )

    return response


#####################################
############## Users ###############
#####################################

# delete one user by name
def delete_user(user_name):
    respons = (
        supabase.table("users")
        .delete()
        .eq("user_name", user_name)
        .execute()
    )
    return respons


# add a user if it does not exist
def add_user(user_name):
    data = {
        "user_name": user_name
    }

    response = (
        supabase
        .table("users")
        .upsert(data, on_conflict="user_name")  # add the user only once
        .execute()
    )

    return response


# get all user names
def get_username():
    response = (
        supabase.table("users")
        .select("*")
        .execute()
    )
    usernames = [user["user_name"] for user in response.data]
    return usernames


######################################
############## Search ###############
######################################

# search devices with words from many fields
def search_devices(keywords: Iterable[str]):  # keywords can be a list or a tuple
    # clean the keywords
    words = [w.strip() for w in keywords if w and w.strip()]

    response = supabase.table("devices").select(
        "device_name, serial_number, manufacturer, assigned_user, tags, purchase_date, warranty_period"
    ).execute()

    devices = response.data or []

    if not words:
        return devices

    def normalize(value):
        return str(value).strip().lower()

    def matches_word(device, word):
        normalized_word = normalize(word)

        searchable_values = [
            device.get("device_name"),
            device.get("serial_number"),
            device.get("manufacturer"),
            device.get("assigned_user"),
        ]

        if any(
            normalized_word in normalize(value)
            for value in searchable_values
            if value is not None
        ):
            return True

        device_tags = device.get("tags") or []
        if not isinstance(device_tags, list):
            device_tags = [device_tags]

        return any(
            normalized_word in normalize(tag)
            for tag in device_tags
            if tag is not None
        )

    return [
        device for device in devices
        if all(matches_word(device, word) for word in words)
    ]


######################################
############## Stats ################
######################################

# count all devices
def total_devices():
    response = (
        supabase
        .table("devices")
        .select("*", count="exact")
        .execute()
    )

    return response.count


# get all device names
def all_devices_name():
    response = (
        supabase
        .table("devices")
        .select("device_name")
        .execute()
    )

    return [device["device_name"] for device in response.data]


# ══════════════════════════════════════════════════════════════════════════════
#  OCR
# ══════════════════════════════════════════════════════════════════════════════

#########################################
############## Photo / OCR ##############
#########################################

# load the model into the cache to avoid loading for every click
@st.cache_resource
def load_model():
    return ocr_predictor(
        pretrained=True,
        assume_straight_pages=False,
        straighten_pages=True,
        detect_orientation=True
    )

@st.dialog("OCR dialog")
def ocr():
    file = st.camera_input("take a picture") or st.file_uploader("upload a file here")

    # a filter for dell serial number pattern (7 characters in uppercase, )
    pattern = re.compile(r"[A-Z0-9]{7}")

    if file is not None:
        img = Image.open(file).convert("RGB")
        img = np.array(img)

        model = load_model()
        result = model([img])

        text = result.render()
        glued_text = "".join(text.split())

        matches = pattern.findall(glued_text)
        valid_tags = [m for m in matches if re.search(r"[A-Z]", m)]

        st.image(img)

        if valid_tags:
            st.success(f"Detected service tag: {valid_tags[0]}")
        else:
            st.warning("No service tag detected")


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN APP
# ══════════════════════════════════════════════════════════════════════════════

# tests variables to simule datas
users = sorted({user.strip() for user in get_username() if user and user.strip()})
all_devices_name_list = all_devices_name()
unique_devices_name = list(set(all_devices_name_list))
#todo: export button ton csv with tags to for filtering, settings menu for default tags

AUTH_PASSWORD = "Pa$$w0rd"

if "is_authenticated" not in st.session_state:
    st.session_state.is_authenticated = False

if "selected_status_filters" not in st.session_state:
    st.session_state.selected_status_filters = []


def toggle_status_filter(status_key):
    if status_key in st.session_state.selected_status_filters:
        st.session_state.selected_status_filters.remove(status_key)
    else:
        st.session_state.selected_status_filters.append(status_key)

# open a dialog to log in
@st.dialog("Login")
def login_dialog():
    with st.form("login_form", border=False):
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")

        if submitted:
            if password == AUTH_PASSWORD:
                st.session_state.is_authenticated = True
                st.success("You are now logged in.")
                st.rerun()
            else:
                st.error("Wrong password.")


# calculate the remaining warranty days
def days_left(purchase_date, warranty_months):
    if not purchase_date:
        return 0

    d = datetime.strptime(purchase_date, "%Y-%m-%d").date()

    # add the months
    y = d.year + (d.month - 1 + warranty_months) // 12
    m = (d.month - 1 + warranty_months) % 12 + 1
    end_date = date(y, m, d.day)

    return max(0, (end_date - date.today()).days)


# get the warranty status from the days left
def status(purchase_date, warranty_months):
    days = days_left(purchase_date, warranty_months)

    if days == 0:
        return {"key": "expired", "label": "Expired", "icon": "❌", "color": "red"}
    if days <= 30:
        return {"key": "expiring_soon", "label": "Expiring soon", "icon": "⏰", "color": "orange"}
    return {"key": "active", "label": "Active", "icon": "✅", "color": "green"}


# convert the warranty months to the selectbox format
def get_warranty_option(months):
    options = ["6 months", "12 months", "24 months", "36 months", "48 months"]
    target = f"{months} months"
    return target if target in options else "48 months"


def build_export_frame(devices):
    export_rows = []

    for item in devices:
        device_tags = item.get("tags") or []

        if not isinstance(device_tags, list):
            device_tags = [device_tags]

        device_tags = [str(tag).strip() for tag in device_tags if tag and str(tag).strip()]

        export_rows.append(
            {
                "device_name": item.get("device_name") or "",
                "serial_number": item.get("serial_number") or "",
                "manufacturer": item.get("manufacturer") or "",
                "assigned_user": item.get("assigned_user") or "",
                "tags": ", ".join(device_tags),
                "purchase_date": item.get("purchase_date") or "",
                "warranty_period": item.get("warranty_period") or "",
                "status": status(item.get("purchase_date"), item.get("warranty_period", 0))["label"],
                "days_left": days_left(item.get("purchase_date"), item.get("warranty_period", 0)),
            }
        )

    return pd.DataFrame(
        export_rows,
        columns=[
            "device_name",
            "serial_number",
            "manufacturer",
            "assigned_user",
            "tags",
            "purchase_date",
            "warranty_period",
            "status",
            "days_left",
        ],
    )

def convert_for_download(devices):
    return build_export_frame(devices).to_csv(index=False).encode("utf-8")


####################################
############## Header ##############
####################################
with st.container(border=True, horizontal=True, vertical_alignment="bottom"):
    header_left, header_right = st.columns([6.5, 5], vertical_alignment="center")
    with header_left:
        st.markdown(
            """
            <div style="text-align:left;">
                <div style="font-size:28px; font-weight:700;">Serial Guard</div>
                <div style="font-size:14px; margin-top:4px; margin-bottom:10px">Monitor warranties and serial numbers</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with header_right:
        auth_left, auth_right = st.columns(2, vertical_alignment="center")

        with auth_left:
            if st.session_state.is_authenticated:
                if st.button("Logout", use_container_width=True):
                    st.session_state.is_authenticated = False
                    st.rerun()
            else:
                if st.button("Login", use_container_width=True):
                    login_dialog()

        with auth_right:
            if st.button(
                "Scan Device",
                icon="📷",
                type="primary",
                use_container_width=True,
                disabled=not st.session_state.is_authenticated,
            ):
                ocr()

if not st.session_state.is_authenticated:
    st.info("Read only mode. Login to scan, export, add, or modify devices.")

####################################
############## Status ##############
####################################

all_status_items = search_devices([])
status_counts = {
    "active": 0,
    "expiring_soon": 0,
    "expired": 0,
}

for item in all_status_items:
    item_status = status(item["purchase_date"], item["warranty_period"])
    status_counts[item_status["key"]] += 1

selected_status_filters = st.session_state.selected_status_filters

# Status's Cards
card_left, card_middle, card_right = st.columns(3, border=False)

with card_left:
    active_label = f"({status_counts['active']}) Active Warranties"
    if "active" in selected_status_filters:
        active_label = f"{active_label} ✓"

    if st.button(
        active_label,
        use_container_width=True,
        type="primary" if "active" in selected_status_filters else "secondary",
    ):
        toggle_status_filter("active")
        st.rerun()

with card_middle:
    expiring_label = f"({status_counts['expiring_soon']}) Expiring soon"
    if "expiring_soon" in selected_status_filters:
        expiring_label = f"{expiring_label} ✓"

    if st.button(
        expiring_label,
        use_container_width=True,
        type="primary" if "expiring_soon" in selected_status_filters else "secondary",
    ):
        toggle_status_filter("expiring_soon")
        st.rerun()

with card_right:
    expired_label = f"({status_counts['expired']}) Expired"
    if "expired" in selected_status_filters:
        expired_label = f"{expired_label} ✓"

    if st.button(
        expired_label,
        use_container_width=True,
        type="primary" if "expired" in selected_status_filters else "secondary",
    ):
        toggle_status_filter("expired")
        st.rerun()

####################################
############## Search ##############
####################################

with st.container(border=True, vertical_alignment="center"):
    # create a search column with border
    search_column, download_button = st.columns([6.65, 1.01], vertical_alignment="bottom")

    # display the input bar in the search column
    with search_column:
        # search_options is the selected options
        search_options = st.multiselect(
            "Search by name, serial number, user, etc...",
            unique_devices_name,
            accept_new_options=True,
        )

    items = search_devices(search_options)

    if selected_status_filters:
        items = [
            item for item in items
            if status(item["purchase_date"], item["warranty_period"])["key"] in selected_status_filters
        ]

    # export all data with the current filter to a csv file
    with download_button:
        csv = convert_for_download(items)

        st.download_button(
            label="CSV",
            data=csv,
            file_name="devices_filtered.csv",
            mime="text/csv",
            icon=":material/download:",
            disabled=not st.session_state.is_authenticated,
        )

#########################################
############## Add devices ##############
#########################################

# open a dialog to add a device manually
@st.dialog("Add a new device")
def add_manually_device_dialog():
    if not st.session_state.is_authenticated:
        st.warning("Login required.")
        return

    with st.form("Add device", border=False):

        # inputs form
        device_name = st.multiselect("Device Name *", ["Dell 14", "Dell 16"], max_selections=1)
        serial_number = st.text_input("Serial Number *")
        manufacturer = st.text_input("Manufacturer")
        assigned_user = st.multiselect("Assigned user", users, max_selections=1)
        tags = st.multiselect("Tags", ["1", "2"], accept_new_options=True)
        purchase_date = st.date_input(format="DD/MM/YYYY", label="Purchase Date")
        warranty_period = st.multiselect(
            "Warranty Period (months)",
            ["6 months", "12 months", "24 months", "36 months", "48 months"],
            max_selections=1,
            default="48 months",
        )

        # validate and convert for the database
        submitted = st.form_submit_button("Add device")

        if submitted:
            name_val = (device_name[0] if device_name else "").strip()
            serial_val = (serial_number or "").strip()

            # convert lists to strings or integer
            assigned_user_str = (assigned_user[0] if assigned_user else "").strip()
            warranty_period_val = int(warranty_period[0].split()[0]) if warranty_period else 0

            if not name_val:
                st.error("Device Name can not be empty.", icon="🚨")
            if not serial_val:
                st.error("Serial Number can not be empty.", icon="🚨")
            else:
                st.success("Device added.")

                # add user in the db
                if assigned_user_str:
                    add_user(assigned_user_str)

                # call the function to add device if valid
                add_device(
                    name_val,
                    serial_val,
                    manufacturer,
                    assigned_user_str,
                    tags,
                    purchase_date,
                    warranty_period_val,
                )


# column without border
with st.container(horizontal=True, horizontal_alignment="center", vertical_alignment="bottom"):

    # display the number of all devices
    st.subheader(f"All devices ({total_devices()})")

    # button to call the function
    if st.button("➕ Add Manually", disabled=not st.session_state.is_authenticated):
        add_manually_device_dialog()

#############################################
############## Display devices ##############
#############################################
# open a dialog to edit one device
@st.dialog("Modify Device")
def modify_device_dialog(item):
    if not st.session_state.is_authenticated:
        st.warning("Login required.")
        return

    with st.form(f"modify_device_{item['serial_number']}", border=False):

        device_options = ["Dell 14", "Dell 16"]
        warranty_options = ["6 months", "12 months", "24 months", "36 months", "48 months"]

        # current values
        current_device_name = item["device_name"] if item["device_name"] in device_options else None
        current_user = item["assigned_user"] if item["assigned_user"] in users else None
        current_warranty = get_warranty_option(item["warranty_period"])

        # convert the date string to a date
        current_purchase_date = (
            datetime.strptime(item["purchase_date"], "%Y-%m-%d").date()
            if item["purchase_date"]
            else date.today()
        )

        # prefilled inputs
        device_name = st.selectbox(
            "Device Name *",
            options=device_options,
            index=device_options.index(current_device_name) if current_device_name else 0,
        )

        serial_number = st.text_input("Serial Number *", value=item["serial_number"] or "")
        manufacturer = st.text_input("Manufacturer", value=item["manufacturer"] or "")

        assigned_user_index = users.index(current_user) if current_user in users else None
        assigned_user = st.selectbox(
            "Assigned user",
            options=users,
            index=assigned_user_index,
            placeholder="unassigned",
        )

        tags = st.multiselect(
            "Tags",
            ["1", "2"],
            default=item["tags"] if item.get("tags") else [],
            accept_new_options=True,
        )

        purchase_date = st.date_input(
            "Purchase Date",
            value=current_purchase_date,
            format="DD/MM/YYYY",
        )

        warranty_period = st.selectbox(
            "Warranty Period (months)",
            options=warranty_options,
            index=warranty_options.index(current_warranty),
        )

        submitted = st.form_submit_button("Save changes")

        if submitted:
            name_val = (device_name or "").strip()
            serial_val = (serial_number or "").strip()
            manufacturer_val = (manufacturer or "").strip()
            assigned_user_val = (assigned_user or "").strip()
            warranty_period_val = int(warranty_period.split()[0])

            if not name_val:
                st.error("Device Name can not be empty.", icon="🚨")
            elif not serial_val:
                st.error("Serial Number can not be empty.", icon="🚨")
            else:
                # keep automatic add_user if needed
                if assigned_user_val:
                    add_user(assigned_user_val)

                # this requires an update_device function in database.py
                update_device(
                    original_serial=item["serial_number"],
                    device_name=name_val,
                    serial_number=serial_val,
                    manufacturer=manufacturer_val,
                    assigned_user=assigned_user_val,
                    tags=tags,
                    purchase_date=purchase_date,
                    warranty_period=warranty_period_val,
                )

                st.success("Device updated successfully.")
                st.rerun()


# devices cards where information like device name and serial number are shown
with st.container(border=False, height=600):
    for item in items:
        item_status = status(item["purchase_date"], item["warranty_period"])
        device_tags = item.get("tags") or []

        if not isinstance(device_tags, list):
            device_tags = [device_tags]

        device_tags = [str(tag).strip() for tag in device_tags if tag and str(tag).strip()]

        # outer card container with border
        devices_infos_container, = st.columns(1, border=True)

        with devices_infos_container:
            # two columns left for text and right for the button
            left, right = st.columns([3, 1], vertical_alignment="center", border=False)

            with left:
                with st.container(horizontal=True, border=False):
                    st.badge(item["serial_number"], color="violet")
                    st.write(item["device_name"])

                with st.container(horizontal=True):
                    st.badge(item["assigned_user"] or "Unassigned", color="blue")
                    st.badge(item_status["label"], icon=item_status["icon"], color=item_status["color"])
                    st.badge(
                        f"{days_left(item['purchase_date'], item['warranty_period'])} days left",
                        color="gray",
                    )
                    st.badge(
                        datetime.strptime(item["purchase_date"], "%Y-%m-%d").strftime("%d-%m-%Y")
                        if item["purchase_date"]
                        else "None",
                        color="grey",
                    )
                    for tag in device_tags:
                        st.badge(tag)

            with right:
                with st.container(horizontal=True, border=False):
                    with st.container(horizontal=False, horizontal_alignment="right"):
                        if st.button(
                            "modify",
                            icon="📝",
                            key=f"open_{item['serial_number']}",
                            type="secondary",
                            disabled=not st.session_state.is_authenticated,
                        ):
                            modify_device_dialog(item)
