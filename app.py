import os
import platform
import re
import streamlit as st
import pandas as pd
import pytesseract
from PIL import Image, ImageOps, ImageEnhance

# On Windows, pytesseract needs to know where the Tesseract program is
# installed, since it is usually not on the system PATH there. On
# Streamlit Cloud (Linux), tesseract-ocr is installed via packages.txt
# and is already on the PATH, so we leave pytesseract's default behaviour
# alone in that case.
if platform.system() == "Windows":
    windows_tesseract_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    if os.path.exists(windows_tesseract_path):
        pytesseract.pytesseract.tesseract_cmd = windows_tesseract_path

st.set_page_config(
    page_title="PharmaGuard",
    page_icon="💊",
    layout="centered"
)

st.title("PharmaGuard")
st.caption("Drug-Drug Interaction Checker and Medicine Scanner")

st.sidebar.title("About")
st.sidebar.write("Developed by Soham Deshmukh")
st.sidebar.write("B.Pharm | M.Tech Biomedical Devices, IIT Indore")
st.sidebar.write("Prototype Version")


# Load interaction database
@st.cache_data
def load_data():
    data = pd.read_csv("pharmaguard_ddi_200_clean.csv")

    data["drug1"] = data["drug1"].str.strip().str.lower()
    data["drug2"] = data["drug2"].str.strip().str.lower()
    data["severity"] = data["severity"].str.strip().str.title()

    return data


ddi_data = load_data()


# Create drug list for selection
drug_list = sorted(
    set(ddi_data["drug1"].tolist() + ddi_data["drug2"].tolist())
)

display_drugs = [drug.title() for drug in drug_list]


# ---------------------------------------------------------------------------
# Helper functions for the Scan Medicine feature
# ---------------------------------------------------------------------------

def preprocess_image(image):
    # Converting to grayscale and boosting contrast generally helps OCR read
    # text printed on shiny/reflective blister foil more reliably.
    gray_image = ImageOps.grayscale(image)
    enhancer = ImageEnhance.Contrast(gray_image)
    processed_image = enhancer.enhance(2.0)
    return processed_image


def guess_medicine_name(text):
    # This is only a guess. The medicine/brand name is usually printed in
    # large letters near the top of the packaging, so we look at the first
    # readable line of text that has a reasonable number of letters in it.
    # This is NOT a lookup against any verified drug database.
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    for line in lines:
        letter_count = sum(character.isalpha() for character in line)
        if letter_count >= 3:
            return line

    return ""


def find_strength(text):
    # Looks for a number followed by a common dosage unit, e.g. "650 mg"
    match = re.search(r"\d+\.?\d*\s*(mg|mcg|ml|g)\b", text, re.IGNORECASE)
    if match:
        return match.group()
    return ""


def find_batch_number(text):
    # Looks for common batch/lot labels followed by an alphanumeric code.
    # Real batch codes can be as short as 2-3 characters, so we do not
    # require a long minimum length here.
    match = re.search(
        r"(?:batch\s*no\.?|b\.?\s*no\.?|batch|lot\s*no\.?)\s*[:\-]?\s*([A-Z0-9]{2,12})",
        text,
        re.IGNORECASE
    )
    if match:
        return match.group(1)
    return ""


def find_expiry_date(text):
    # Expiry dates on packaging use "/", "-", or "." between month and year
    # (e.g. 06/2027, 06-2027, 2027.11), so we accept all three separators.
    match = re.search(
        r"(?:exp\.?|expiry|exp\s*date)\s*[:\-]?\s*(\d{1,2}[\/\-\.]\d{2,4})",
        text,
        re.IGNORECASE
    )
    if match:
        return match.group(1)

    # Fallback: look for any standalone MM/YYYY (or YYYY/MM) style date
    fallback_match = re.search(r"\b(\d{1,2}[\/\-\.](?:20)\d{2}|(?:20)\d{2}[\/\-\.]\d{1,2})\b", text)
    if fallback_match:
        return fallback_match.group(1)

    return ""


# ---------------------------------------------------------------------------
# Page layout: two tabs, DDI Checker (existing feature) and Scan Medicine (new)
# ---------------------------------------------------------------------------

tab1, tab2 = st.tabs(["DDI Checker", "Scan Medicine"])


with tab1:

    st.subheader("Patient Information")

    age = st.number_input(
        "Patient age",
        min_value=1,
        max_value=110,
        value=30
    )


    st.subheader("Medicines")

    col1, col2, col3 = st.columns(3)

    with col1:
        med1 = st.selectbox(
            "Medicine 1",
            ["Select medicine"] + display_drugs,
            index=0
        )

    with col2:
        med2 = st.selectbox(
            "Medicine 2",
            ["Select medicine"] + display_drugs,
            index=0
        )

    with col3:
        med3 = st.selectbox(
            "Medicine 3 (optional)",
            ["None"] + display_drugs,
            index=0
        )


    st.divider()


    if st.button("Check Interactions", use_container_width=True):

        medicines = []

        if med1 != "Select medicine":
            medicines.append(med1.lower())

        if med2 != "Select medicine":
            medicines.append(med2.lower())

        if med3 != "None":
            medicines.append(med3.lower())


        if len(medicines) < 2:
            st.warning("Please select at least two medicines.")

        elif len(medicines) != len(set(medicines)):
            st.warning("The same medicine has been selected more than once.")

        else:
            results = []

            for i in range(len(medicines)):
                for j in range(i + 1, len(medicines)):

                    drug_a = medicines[i]
                    drug_b = medicines[j]

                    match = ddi_data[
                        (
                            (ddi_data["drug1"] == drug_a) &
                            (ddi_data["drug2"] == drug_b)
                        )
                        |
                        (
                            (ddi_data["drug1"] == drug_b) &
                            (ddi_data["drug2"] == drug_a)
                        )
                    ]

                    if not match.empty:

                        for _, interaction in match.iterrows():

                            results.append({
                                "Drug Pair":
                                    f"{drug_a.title()} + {drug_b.title()}",

                                "Severity":
                                    interaction["severity"],

                                "Interaction":
                                    interaction["effect"]
                            })


            if results:

                st.subheader("Interactions Detected")

                results_df = pd.DataFrame(results)


                def color_severity(value):

                    if value == "Major":
                        return "background-color:#C62828;color:white"

                    elif value == "Moderate":
                        return "background-color:#EF6C00;color:white"

                    elif value == "Minor":
                        return "background-color:#2E7D32;color:white"

                    return ""


                styled_df = results_df.style.map(
                    color_severity,
                    subset=["Severity"]
                )

                st.dataframe(
                    styled_df,
                    use_container_width=True,
                    hide_index=True
                )


                if age >= 65:
                    st.info(
                        "Older adults may have altered drug handling and "
                        "greater susceptibility to adverse drug effects. "
                        "Clinical review may therefore be particularly important."
                    )

            else:

                st.info(
                    "No interaction was found for the selected combination "
                    "in the current PharmaGuard dataset."
                )


with tab2:

    st.subheader("Scan Medicine")

    st.caption(
        "Proof of concept: upload or photograph a medicine strip/package "
        "to test whether PharmaGuard can read the printed text using OCR."
    )

    st.caption(
        "Tip: fill the frame with the printed text panel and avoid extra "
        "background (table, hands, etc.) - OCR works much better on a tight, "
        "well-lit photo of just the text."
    )

    uploaded_image = st.file_uploader(
        "Upload an image of the medicine strip or package",
        type=["jpg", "jpeg", "png"]
    )

    camera_image = st.camera_input("Or take a photo using your camera")

    # if a photo was taken, use that; otherwise use the uploaded file
    image_file = camera_image if camera_image is not None else uploaded_image

    if image_file is not None:

        image = Image.open(image_file)
        st.image(image, caption="Image to be scanned", use_container_width=True)

        if st.button("Scan Image"):

            try:
                with st.spinner("Reading text from image..."):
                    processed_image = preprocess_image(image)
                    # psm 6 tells Tesseract to expect one dense block of text
                    # rather than trying to lay out a whole page. This matters
                    # a lot when the photo has background around the label,
                    # since Tesseract's default page-layout guessing otherwise
                    # gets confused and returns nothing.
                    raw_text = pytesseract.image_to_string(
                        processed_image,
                        config="--psm 6"
                    )

                # store results in session state so editing the fields below
                # does not trigger OCR again on every rerun
                st.session_state.raw_text = raw_text
                st.session_state.detected_name = guess_medicine_name(raw_text)
                st.session_state.detected_strength = find_strength(raw_text)
                st.session_state.detected_batch = find_batch_number(raw_text)
                st.session_state.detected_expiry = find_expiry_date(raw_text)

            except Exception as error:
                st.error(
                    "OCR failed. Make sure Tesseract OCR is installed on this "
                    f"system. Error: {error}"
                )

    if "raw_text" in st.session_state:

        st.divider()
        st.subheader("Detected Information")

        st.caption(
            "OCR is not always accurate, especially on reflective foil, small "
            "print, or damaged packaging. Please check and correct the values "
            "below if needed."
        )

        medicine_name = st.text_input(
            "Medicine / brand name",
            value=st.session_state.detected_name
        )

        strength = st.text_input(
            "Strength",
            value=st.session_state.detected_strength
        )

        batch_number = st.text_input(
            "Batch number",
            value=st.session_state.detected_batch
        )

        expiry_date = st.text_input(
            "Expiry date",
            value=st.session_state.detected_expiry
        )

        with st.expander("Show raw OCR text"):
            st.text(st.session_state.raw_text)

        st.info(
            "Note: OCR only reads text that is printed on the package. It "
            "cannot reliably identify the generic/chemical name of a medicine "
            "on its own. Matching a brand name to its generic name would "
            "require a separate, verified drug name database, which "
            "PharmaGuard does not currently include."
        )


st.divider()

st.caption(
    "PharmaGuard is an educational prototype and is not intended to replace "
    "clinical judgment or validated drug-information systems."
)
