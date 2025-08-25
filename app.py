from fastapi import FastAPI, Query
import requests
import re
from bs4 import BeautifulSoup

app = FastAPI(title="CNIC & Phone Info API")

# Function to fetch CNIC and Name from phone number
def fetch_cnic_and_name(phone_number: str) -> dict:
    url = "https://datacorporation.com.pk/sim-info-3/"
    data = {"phoneNumber": phone_number, "submit": "submit"}
    headers = {"User-Agent": "Mozilla/5.0"}

    response = requests.post(url, data=data, headers=headers)
    if response.status_code != 200:
        return {"cnic": "N/A", "name": "N/A"}

    soup = BeautifulSoup(response.text, "html.parser")
    text = soup.get_text().upper()

    cnic_match = re.search(r"CNIC[:\s]+(\d{13})", text)
    name_match = re.search(r"NAME[:\s]+([A-Z ]{3,})", text)

    cnic = cnic_match.group(1) if cnic_match else "N/A"
    name = name_match.group(1).strip() if name_match else "N/A"

    return {"cnic": cnic, "name": name}


# Function to fetch full CNIC details
def fetch_cnic_details(cnic_number: str) -> dict:
    url = "https://cnicinformation.pk/"
    data = {"searchNumber": cnic_number}
    headers = {"User-Agent": "Mozilla/5.0"}

    response = requests.post(url, data=data, headers=headers)
    if response.status_code != 200:
        return {}

    soup = BeautifulSoup(response.text, "html.parser")
    details = {}

    # Extract Name
    name_label = soup.find("p", class_="label", string=lambda s: s and s.strip().lower() == "name")
    if name_label:
        name_value = name_label.find_next_sibling("p", class_="label-value")
        details["Name"] = name_value.text.strip().upper() if name_value else "N/A"
    else:
        details["Name"] = "N/A"

    # Extract Gender
    gender_span = soup.find("span", class_="label", string=lambda s: s and s.strip().lower() in ["male", "female"])
    details["Gender"] = gender_span.text.strip().upper() if gender_span else "N/A"

    # Helper function
    def get_value(label):
        div = soup.find("div", string=lambda s: s and s.strip().lower() == label.lower())
        if div:
            next_div = div.find_next_sibling("div")
            if next_div:
                return next_div.text.strip().upper()
        return "N/A"

    details["Full_address"] = get_value("Full_address")
    details["Division"] = get_value("Division")
    details["Province"] = get_value("Province")
    details["District"] = get_value("District")
    details["Counsil"] = get_value("Counsil")
    details["Cnic"] = get_value("Cnic") if get_value("Cnic") != "N/A" else cnic_number

    return details


# API Endpoint
@app.get("/lookup")
def lookup_phone(phone: str = Query(..., description="Phone number e.g. 03001234567")):
    # Normalize number
    if phone.startswith("+92") and len(phone) == 13:
        phone_number = phone[3:]
    elif phone.startswith("92") and len(phone) == 12:
        phone_number = phone[2:]
    elif phone.startswith("0") and len(phone) == 11:
        phone_number = phone[1:]
    else:
        phone_number = phone

    # Fetch CNIC + Name
    cnic_data = fetch_cnic_and_name(phone_number)
    cnic = cnic_data.get("cnic", "N/A")
    name = cnic_data.get("name", "N/A")

    if cnic == "N/A":
        return {"status": "error", "message": "CNIC not found for this number", "phone": phone}

    # Fetch full CNIC details
    details = fetch_cnic_details(cnic)
    details["Phone"] = phone
    details["Name"] = details.get("Name", name)

    return {"status": "success", "data": details}


# Run using: uvicorn filename:app --reload
