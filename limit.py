import logging
from datetime import datetime, timedelta

TIME_LIMIT_HOURS = 24

def check_time_limit(user_requests, user_id):
    logging.info(f"check_time_limit - user_requests: {user_requests}, user_id: {user_id}")  # Log input
    if user_requests:
        # Urutkan user_requests berdasarkan waktu terbaru (dari yang terbaru ke terlama)
        sorted_requests = sorted(user_requests, key=lambda x: datetime.fromisoformat(x["Last Request"]), reverse=True)
        
        # Ambil request terbaru
        last_request_str = sorted_requests[0]["Last Request"]
        last_request_time = datetime.fromisoformat(last_request_str)
        time_difference = datetime.now() - last_request_time
        logging.info(f"check_time_limit - Last Request Time: {last_request_time}")  # Log last request time
        logging.info(f"check_time_limit - Time Difference: {time_difference}")  # Log time difference

        if time_difference < timedelta(hours=TIME_LIMIT_HOURS):
            remaining_wait_time = timedelta(hours=TIME_LIMIT_HOURS) - time_difference
            hours = remaining_wait_time.seconds // 3600
            minutes = (remaining_wait_time.seconds % 3600) // 60
            logging.info(f"check_time_limit - Batasan waktu dilanggar, kondisi: {time_difference} < {timedelta(hours=TIME_LIMIT_HOURS)} adalah True")  # Log kondisi batasan waktu
            error_message = f"⏳ Request denied! You must wait {hours}h {minutes}m before making another request."
            logging.info(f"check_time_limit - Return error message: {error_message}")  # Log error message
            return error_message
        else:
            logging.info(f"check_time_limit - Batasan waktu terpenuhi, kondisi: {time_difference} < {timedelta(hours=TIME_LIMIT_HOURS)} adalah False")  # Log kondisi batasan waktu
            logging.info("check_time_limit - Return None")  # Log return None
            return None
    else:
        logging.info("check_time_limit - Tidak ada user_requests sebelumnya")  # Log tidak ada request sebelumnya
        logging.info("check_time_limit - Return None")  # Log return None
        return None

def check_user_wallet_limit(all_records, user_id, wallet_address):
    logging.info(f"check_user_wallet_limit - all_records: {all_records}, user_id: {user_id}, wallet_address: {wallet_address}") # Log input (now using all_records)
    user_wallet_requests = [r for r in all_records if r["User ID"] == user_id] # Get ALL requests for this user from all_records
    logging.info(f"check_user_wallet_limit - User Wallet Requests (from all_records): {user_wallet_requests}") # Log User Wallet Requests
    if user_wallet_requests: # If user_wallet_requests is NOT empty (user has previous requests with ANY wallet address)
        first_wallet_address = user_wallet_requests[0]["Wallet Address"] # Get the first wallet address used by this user
        if wallet_address != first_wallet_address: # If the current wallet_address is DIFFERENT from the first wallet address
            error_message = "❌ Request denied! You can only use one wallet address." # Then, return error message
            logging.info(f"check_user_wallet_limit - Return error message: {error_message}") # Log error message
            return error_message
    logging.info("check_user_wallet_limit - Return None") # Log return None
    return None

def check_wallet_address_limit(all_records, user_id, wallet_address):
    wallet_address_requests = [r for r in all_records if r["Wallet Address"] == wallet_address]
    logging.info(f"check_wallet_address_limit - Wallet Address Requests: {wallet_address_requests}") # Log Wallet Address Requests
    if wallet_address_requests:
        return "❌ Wallet address limit reached. This wallet address has already been used."
    return None
