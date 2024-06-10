from flask import Flask, render_template, request, redirect, url_for, flash, session
from eth_account import Account
from eth_utils import to_checksum_address
from bitcoin import privkey_to_address, random_key
from tronpy.keys import PrivateKey
from tronpy import Tron
import requests
import os

app = Flask(__name__)
app.secret_key = '@###23333'

tron = Tron()

ETHERSCAN_API_KEY = 'I756VBZC1WW8CDAIXIW4IPGGET1SB6664G'

def get_nonce(address):
    url = f'https://api.etherscan.io/api?module=proxy&action=eth_getTransactionCount&address={address}&tag=latest&apikey={ETHERSCAN_API_KEY}'
    response = requests.get(url).json()
    return int(response['result'], 16)

def get_gas_price():
    url = f'https://api.etherscan.io/api?module=proxy&action=eth_gasPrice&apikey={ETHERSCAN_API_KEY}'
    response = requests.get(url).json()
    return int(response['result'], 16)

def send_eth(private_key, to_address, amount):
    account = Account.from_key(private_key)
    from_address = account.address

    nonce = get_nonce(from_address)
    gas_price = get_gas_price()

    tx = {
        'nonce': nonce,
        'to': to_checksum_address(to_address),
        'value': amount,
        'gas': 21000,
        'gasPrice': gas_price,
        'chainId': 1
    }

    signed_tx = account.sign_transaction(tx)
    tx_hex = signed_tx.raw_transaction.hex()

    url = f'https://api.etherscan.io/api?module=proxy&action=eth_sendRawTransaction&hex={tx_hex}&apikey={ETHERSCAN_API_KEY}'
    response = requests.get(url).json()
    return response

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/generate_wallet', methods=['POST'])
def generate_wallet():
    crypto = request.form.get('crypto')
    if crypto == 'ethereum':
        address, private_key = generate_ethereum_wallet()
    elif crypto == 'bitcoin':
        address, private_key = generate_bitcoin_wallet()
    elif crypto == 'tron':
        private_key, address = generate_tron_wallet()
    else:
        flash('Invalid cryptocurrency selected')
        return redirect(url_for('home'))
    
    session['private_key'] = private_key
    session['address'] = address

    flash(f'{crypto.capitalize()} Wallet Generated: Address: {address}, Private Key: {private_key}')
    return redirect(url_for('home'))

def generate_ethereum_wallet():
    acct = Account.create()
    address = acct.address
    private_key = acct.key.hex()
    save_wallet('Ethereum', address, private_key)
    return address, private_key

def generate_bitcoin_wallet():
    private_key = random_key()
    address = privkey_to_address(private_key)
    save_wallet('Bitcoin', address, private_key)
    return address, private_key

def generate_tron_wallet():
    private_key = PrivateKey.random()
    address = private_key.public_key.to_base58check_address()
    save_wallet('TRON', address, private_key.hex())
    return private_key.hex(), address

def save_wallet(folder_name, address, private_key):
    os.makedirs(folder_name, exist_ok=True)
    with open(f"{folder_name}/wallet.txt", "w") as file:
        file.write(f"Address: {address}\nPrivate Key: {private_key}\n")

@app.route('/receive')
def receive():
    address = session.get('address')
    return render_template('receive.html', address=address)

@app.route('/clear_session')
def clear_session():
    session.clear()
    return redirect(url_for('home'))

@app.route('/send_eth')
def send_eth():
    return render_template('send_eth.html')


# Import wallet route
@app.route('/import_wallet', methods=['GET', 'POST'])
def import_wallet():
    if request.method == 'POST':
        private_key = request.form.get('private_key')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Validate password
        if password != confirm_password:
            flash('Passwords do not match!')
            return redirect(url_for('import_wallet'))

        if len(password) != 4:
            flash('Password must be 4 digits long!')
            return redirect(url_for('import_wallet'))
        
        # Save private key in session
        session['private_key'] = private_key
        flash('Wallet imported successfully!')
        
        return redirect(url_for('send_eth'))

    return render_template('import.html')


@app.route('/send_eth_transaction', methods=['POST'])
def send_eth_transaction():
    if request.method == 'POST':
        private_key = request.form.get('private_key')
        to_address = request.form.get('to_address')
        amount = request.form.get('amount')
        
        response = send_eth(private_key, to_address, amount)
        
        if 'error' in response:
            flash(f"Error: {response['error']['message']}")
        else:
            flash('Ethereum sent successfully')
        
        return redirect(url_for('home'))

    return render_template('send_eth.html')

def get_balance(address):
    url = f'https://api.etherscan.io/api?module=account&action=balance&address={address}&tag=latest&apikey={ETHERSCAN_API_KEY}'
    response = requests.get(url).json()
    balance = int(response['result']) / 10**18  # Convert from Wei to ETH
    return balance

def get_tron_balance(address):
    url = f'https://api.trongrid.io/v1/accounts/{address}'
    headers = {'TRON-PRO-API-KEY': '3022fab4-cd87-48c5-b5d1-65fb3e588f67'}
    response = requests.get(url, headers=headers).json()
    balance = response.get('balance', 0) / 10**6  # TRX balance
    return balance

def get_tronscan_balance(address):
    url = f'https://tronscan.org/#/address/{address}'
    # You would need to use a library like BeautifulSoup to scrape the balance from this page
    # For demonstration purposes, let's assume we're fetching the balance using Tronscan's API
    # Replace this logic with actual scraping code if needed
    balance = 100  # Example balance fetched from Tronscan
    return balance

@app.route('/balance')
def balance():
    eth_address = session.get('address')
    eth_balance = None
    tron_address = session.get('tron_address')
    tron_balance = None
    
    if eth_address:
        eth_balance = get_balance(eth_address)
    
    if tron_address:
        tron_balance = get_tron_balance(tron_address)
    
    return render_template('balance.html', eth_address=eth_address, eth_balance=eth_balance, tron_address=tron_address, tron_balance=tron_balance)


@app.route('/export_data', methods=['POST'])
def export_data():
    address = request.form.get('address')
    # Your code to export the data for the address here
    flash('Data exported successfully')
    return redirect(url_for('balance'))

if __name__ == '__main__':
    app.run(debug=True)
