import re
import numpy as np
import streamlit as st
from PIL import Image
from doctr.models import ocr_predictor

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