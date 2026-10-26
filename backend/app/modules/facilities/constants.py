"""P10-F02: the allowed values for facility setup. One list, served to the
setup wizard by `GET /platform/setup-options`, so the UI never keeps its own copy."""
from typing import Literal

FacilityType = Literal["hospital", "clinic", "medical_centre"]

FACILITY_TYPES: list[tuple[str, str]] = [
    ("hospital", "Hospital"),
    ("clinic", "Clinic"),
    ("medical_centre", "Medical centre"),
]

# (IANA name, label). A curated list rather than the full tz database: the
# container image and Windows hosts do not all ship one, and a hospital picks
# from a handful of zones.
TIMEZONES: list[tuple[str, str]] = [
    ("Asia/Kolkata", "India (IST, UTC+05:30)"),
    ("Asia/Kathmandu", "Nepal (UTC+05:45)"),
    ("Asia/Colombo", "Sri Lanka (UTC+05:30)"),
    ("Asia/Dhaka", "Bangladesh (UTC+06:00)"),
    ("Asia/Karachi", "Pakistan (UTC+05:00)"),
    ("Asia/Dubai", "United Arab Emirates (UTC+04:00)"),
    ("Asia/Riyadh", "Saudi Arabia (UTC+03:00)"),
    ("Asia/Qatar", "Qatar (UTC+03:00)"),
    ("Asia/Singapore", "Singapore (UTC+08:00)"),
    ("Asia/Kuala_Lumpur", "Malaysia (UTC+08:00)"),
    ("Asia/Bangkok", "Thailand (UTC+07:00)"),
    ("Asia/Jakarta", "Indonesia - Western (UTC+07:00)"),
    ("Asia/Manila", "Philippines (UTC+08:00)"),
    ("Asia/Tokyo", "Japan (UTC+09:00)"),
    ("Africa/Nairobi", "Kenya (UTC+03:00)"),
    ("Africa/Lagos", "Nigeria (UTC+01:00)"),
    ("Africa/Johannesburg", "South Africa (UTC+02:00)"),
    ("Africa/Cairo", "Egypt (UTC+02:00)"),
    ("Europe/London", "United Kingdom"),
    ("Europe/Paris", "Central Europe"),
    ("America/New_York", "US Eastern"),
    ("America/Chicago", "US Central"),
    ("America/Los_Angeles", "US Pacific"),
    ("Australia/Sydney", "Australia - Sydney"),
    ("UTC", "UTC"),
]

CURRENCIES: list[tuple[str, str]] = [
    ("INR", "Indian rupee (INR)"),
    ("NPR", "Nepalese rupee (NPR)"),
    ("LKR", "Sri Lankan rupee (LKR)"),
    ("BDT", "Bangladeshi taka (BDT)"),
    ("PKR", "Pakistani rupee (PKR)"),
    ("AED", "UAE dirham (AED)"),
    ("SAR", "Saudi riyal (SAR)"),
    ("QAR", "Qatari riyal (QAR)"),
    ("SGD", "Singapore dollar (SGD)"),
    ("MYR", "Malaysian ringgit (MYR)"),
    ("THB", "Thai baht (THB)"),
    ("IDR", "Indonesian rupiah (IDR)"),
    ("PHP", "Philippine peso (PHP)"),
    ("JPY", "Japanese yen (JPY)"),
    ("KES", "Kenyan shilling (KES)"),
    ("NGN", "Nigerian naira (NGN)"),
    ("ZAR", "South African rand (ZAR)"),
    ("USD", "US dollar (USD)"),
    ("EUR", "Euro (EUR)"),
    ("GBP", "Pound sterling (GBP)"),
    ("AUD", "Australian dollar (AUD)"),
]

TIMEZONE_CODES = {code for code, _ in TIMEZONES}
CURRENCY_CODES = {code for code, _ in CURRENCIES}
