#!/usr/bin/env python3

intro = """
 Download latest PlusGSM invoice.

 This script downloads latest PlusGSM portal invoice bundle, leaves just an invoice page and saves it to file.
 System keyring is used to handle password storage.
 
 License: GPL 3.0
"""

import requests
import argparse
import re
import keyring
import getpass
from PyPDF2 import PdfFileWriter, PdfFileReader

HEADERS = {'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:65.0) Gecko/20100101 Firefox/65.0'}
KEYRING_SERVICE = 'plusgsm'

parser = argparse.ArgumentParser(description=intro)
parser.add_argument('msisdn', help='Subscriber phone number')
args = parser.parse_args()

password = keyring.get_password(KEYRING_SERVICE, args.msisdn) or getpass.getpass('PlusGSM on-line password:')

l1_resp = requests.get('https://ssl.plusgsm.pl/ebok-web/basic/loginStep1.action', headers=HEADERS)

login_resp = requests.post(
    'https://ssl.plusgsm.pl/ebok-web/basic/loginStep2.action',
    data={'brandId': '', 'msisdn': args.msisdn, 'password': password},
    cookies=l1_resp.cookies, headers=HEADERS)

if 'loginError' in login_resp.url:
    print("Login failed")
    exit(1)


init_resp = requests.get('https://ssl.plusgsm.pl/ebok-web/spectrum/welcome.action',
                         cookies=l1_resp.cookies, headers=HEADERS)

if init_resp.status_code != 200 or "Zalogowany jako" not in init_resp.text:
    print("Main page failed", init_resp.text)
    exit(1)

# Once logged in remember the password
keyring.set_password(KEYRING_SERVICE, args.msisdn, password)

menu_resp = requests.get('https://ssl.plusgsm.pl/ebok-web/spectrum/payments/showPaymentsHistory.action',
                         cookies=l1_resp.cookies, headers=HEADERS)

if menu_resp.status_code != 200:
    print("Can't open menu", menu_resp)
    exit(1)

doc_select_resp = requests.get(
    'https://ssl.plusgsm.pl/ebok-web/spectrum/payments/downloadInvoice.action',
    params={'positionOnList': 1, 'positionOnSubList': 0},
    cookies=l1_resp.cookies, headers=HEADERS)

if doc_select_resp.status_code != 200:
    print("Can't select document", doc_select_resp)
    exit(1)

doc_resp = requests.post('https://ssl.plusgsm.pl/ebok-web/spectrum/brpDocumentDownload/downloadDocument.action',
                         cookies=l1_resp.cookies, headers=HEADERS)

if doc_resp.status_code != 200:
    print("Can't download document", doc_select_resp)
    exit(1)

disposition = doc_resp.headers['Content-Disposition']
filename = re.search("^filename=([^\.]+.pdf)", disposition).group(1)

if not re.search("^[a-zA-Z0-9_\.]+$", filename):
    print("Bad file name: ", filename)
    exit(1)

orig_filename = filename + ".orig"

with open(orig_filename, "wb+") as pdf_file:
    pdf_file.write(doc_resp.content)

print("Saved:", orig_filename)

pages_to_keep = [1] # leave page no 2
infile = PdfFileReader(orig_filename, 'rb')
output = PdfFileWriter()

for i in pages_to_keep:
    p = infile.getPage(1)
    text = p.extractText()
    output.addPage(p)


with open(filename, 'wb') as f:
    output.write(f)

print("Saved:", filename)

text = infile.getPage(1).extractText().encode('cp1252').decode('cp1250')
print("Text:", text)

