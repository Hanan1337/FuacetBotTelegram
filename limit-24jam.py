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
