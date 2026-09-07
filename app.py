import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="PharmaGuard",
    page_icon="💊",
    layout="centered"
)

st.title("PharmaGuard")
st.caption("Drug-Drug Interaction Checker")

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


st.divider()

st.caption(
    "PharmaGuard is an educational prototype and is not intended to replace "
    "clinical judgment or validated drug-information systems."
)
