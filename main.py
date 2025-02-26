import os
import logging
from datetime import datetime
from dotenv import load_dotenv
from web3 import Web3
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    CallbackContext,
)
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from limit import check_time_limit, check_user_wallet_limit, check_wallet_address_limit
import json  # Import library json - PENTING!

# Load environment variables
load_dotenv()

# Configuration from .env
BOT_TOKEN = os.getenv("BOT_TOKEN")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
WALLET_ADDRESS = os.getenv("WALLET_ADDRESS")
GOOGLE_CREDS_FILE = os.getenv("GOOGLE_CREDS_FILE")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
CHANNEL_ID = os.getenv("CHANNEL_ID")
FAUCET_AMOUNT = float(os.getenv("FAUCET_AMOUNT", 0.25))
RPC_URL = os.getenv("RPC_URL")
CHAIN_ID = int(os.getenv("CHAIN_ID"))

# Initialize Web3
web3 = Web3(Web3.HTTPProvider(RPC_URL))

# Setup Google Sheets
def setup_google_sheets():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(
            GOOGLE_CREDS_FILE, scope
        )
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        sheet = spreadsheet.sheet1

        headers = sheet.row_values(1)
        expected_headers = [
            "User ID", "Username", "First Name", "Last Name",
            "Last Request", "Wallet Address", "Tx Hash"
        ]

        if headers != expected_headers:
            sheet.clear()
            sheet.append_row(expected_headers)
            logging.info("✅ Created headers in Google Sheets.")

        return sheet
    except Exception as e:
        logging.error(f"Error connecting to Google Sheets: {e}")
        return None

sheet = setup_google_sheets()

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"👋 Hello {user.first_name}!\n\n"
        f"🚀 Use /faucet followed by your wallet address to get testnet coins.\n"
        f"📢 Make sure you have joined our channel first!\n\n"
        f"Rules:\n"
        f"1. Max 1 request per 24 hours\n"
        f"2. 1 wallet address can only be used once\n"
        f"3. 1 User ID can only use 1 wallet address\n\n"
        f"Example: /faucet 0x123...abc"
    )

async def check_channel_membership(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    try:
        member = await context.bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        logging.error(f"Error checking membership: {e}")
        return False

def send_mon(to_address: str, amount_in_mon: float) -> str:
    try:
        amount_wei = Web3.to_wei(amount_in_mon, "ether")
        nonce = web3.eth.get_transaction_count(WALLET_ADDRESS)

        tx = {
            "nonce": nonce,
            "to": to_address,
            "value": amount_wei,
            "gasPrice": Web3.to_wei(55, "gwei"),
            "chainId": CHAIN_ID,
        }

        tx["gas"] = web3.eth.estimate_gas(tx)
        signed_tx = web3.eth.account.sign_transaction(tx, PRIVATE_KEY)
        tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
        return tx_hash.hex()
    except Exception as e:
        logging.error(f"Transaction failed: {e}")
        return None

async def faucet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id

    logging.info(f"faucet - User ID: {user_id}, Wallet Address Args: {context.args}")

    # Cek keanggotaan channel
    if not await check_channel_membership(update, context):
        keyboard = [[InlineKeyboardButton(
            text="📢 Join Channel Here", url=f"https://t.me/{CHANNEL_ID[1:]}")]]
        await update.message.reply_text(
            "⛔ You must join our channel first!",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    # Validasi format command
    if not context.args:
        await update.message.reply_text(
            "❌ Incorrect format!\nUse: /faucet <wallet_address>\nExample: /faucet 0x1234...abcd"
        )
        return

    wallet_address = context.args[0].strip().lower()
    if not web3.is_address(wallet_address):
        await update.message.reply_text("❌ Invalid wallet address!")
        return

    try:
        # Ambil semua record dari Google Sheets
        records = sheet.get_all_records() if sheet else []
        logging.info(f"faucet - All Records from Google Sheets: {records}")

        # Tambahan Logging SEBELUM filter user_requests - JSON LOGGING ADDED
        logging.info(f"faucet - SEBELUM filter user_requests - records (JSON): {json.dumps(records)}, user_id: {user_id}")

        # Filter record untuk User ID yang sedang request
        user_requests = [r for r in records if str(r["User ID"]) == str(user_id)]

        # Tambahan Logging SETELAH filter user_requests - JSON LOGGING ADDED
        logging.info(f"faucet - SETELAH filter user_requests - user_requests: {user_requests}")


        logging.info(f"faucet - User Requests for User ID {user_id}: {user_requests}") # Log user requests (redundant, bisa dihapus setelah debug)

        # Filter 1: Batasan waktu 24 jam
        logging.info("faucet - Memanggil check_time_limit")
        time_limit_message = check_time_limit(user_requests, user_id)
        logging.info(f"faucet - Hasil check_time_limit: {time_limit_message}")
        if time_limit_message:
            await update.message.reply_text(time_limit_message)
            return

        # Filter 2: Batasan wallet per User ID
        logging.info("faucet - Memanggil check_user_wallet_limit")
        user_wallet_limit_message = check_user_wallet_limit(records, user_id, wallet_address)
        logging.info(f"faucet - Hasil check_user_wallet_limit: {user_wallet_limit_message}")
        if user_wallet_limit_message:
            await update.message.reply_text(user_wallet_limit_message)
            return

        # Filter 3: Batasan Wallet Address global - HANYA DIPANGGIL JIKA user_requests KOSONG (first request atau re-request wallet BARU)
        if not user_requests: # kondisi: user_requests kosong
            logging.info("faucet - Memanggil check_wallet_address_limit")
            wallet_address_limit_message = check_wallet_address_limit(records, user_id, wallet_address)
            logging.info(f"faucet - Hasil check_wallet_address_limit: {wallet_address_limit_message}")
            if wallet_address_limit_message:
                await update.message.reply_text(wallet_address_limit_message)
                return

        # Kirim faucet
        checksum_address = Web3.to_checksum_address(wallet_address)
        tx_hash = send_mon(checksum_address, FAUCET_AMOUNT)

        if not tx_hash:
            raise Exception("Failed to send transaction")

        # Simpan ke Google Sheets
        if sheet:
            new_row = [
                str(user_id),
                user.username or "",
                user.first_name or "",
                user.last_name or "",
                datetime.now().isoformat(),
                wallet_address,
                tx_hash,
            ]
            sheet.append_row(new_row)

        explorer_url = f"https://testnet.monadexplorer.com/tx/0x{tx_hash}"
        await update.message.reply_text(
            f"✅ Transaction successful! You have received {FAUCET_AMOUNT} MON.\n\n"
            f"🔗 Tx Hash: 0x{tx_hash}\n"
            f"🌐 View transaction: {explorer_url}"
        )

    except Exception as e:
        logging.error(f"Faucet error: {e}")
        await update.message.reply_text("❌ Request failed! Please try again later.")

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("faucet", faucet))
    logging.info("🤖 Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()
