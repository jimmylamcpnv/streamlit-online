import os
from typing import Iterable

import streamlit as st
from supabase import Client, create_client


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
