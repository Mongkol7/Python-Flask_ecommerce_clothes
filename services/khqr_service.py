import logging
from config import Config

logger = logging.getLogger(__name__)

# Lazy singleton for Bakong KHQR instance
_khqr_instance = None

def get_khqr():
    """Returns or initializes the Bakong KHQR SDK client."""
    global _khqr_instance
    if _khqr_instance is None:
        try:
            from bakong_khqr import KHQR
            token = Config.BAKONG_TOKEN.strip()
            _khqr_instance = KHQR(token)
        except Exception as e:
            logger.error(f"Failed to initialize Bakong KHQR SDK: {e}")
            return None
    return _khqr_instance


def generate_bakong_khqr(amount: float, bill_number: str, currency: str = None) -> dict:
    """
    Generates a real Bakong KHQR payment code for the given order.
    Returns a dict with:
      - success: bool
      - qr_string: raw EMVCo payload string
      - base64_uri: data:image/png;base64,... URI ready for <img> tags
      - md5: transaction verification hash
      - amount: order amount
      - currency: USD / KHR
      - account_id: Bakong account identifier
      - merchant_name: merchant display title
    """
    if currency is None:
        currency = Config.BAKONG_CURRENCY
    currency = str(currency).upper().strip()

    # Clean amount: KHR uses whole integer amounts (no decimal cents in EMVCo tag 54)
    if currency == "KHR":
        clean_amount = int(round(float(amount)))
    else:
        clean_amount = round(float(amount), 2)

    if clean_amount <= 0:
        return {"success": False, "error": "Order amount must be greater than zero."}

    client = get_khqr()
    if not client:
        return {"success": False, "error": "Bakong KHQR gateway is currently unavailable."}

    try:
        res = client.create_qr(
            account_id=Config.BAKONG_ACCOUNT_ID,
            merchant_name=Config.BAKONG_MERCHANT_NAME,
            merchant_city=Config.BAKONG_MERCHANT_CITY,
            amount=clean_amount,
            currency=currency,
            store_label=Config.BAKONG_STORE_LABEL,
            phone_number=Config.BAKONG_PHONE_NUMBER,
            bill_number=bill_number,
            terminal_label=Config.BAKONG_TERMINAL_LABEL,
            static=False,
            expiration=30,  # 30 minutes dynamic QR expiration
        )

        qr_string = res.qr if hasattr(res, "qr") else str(res)
        md5_hash = getattr(res, "md5", None)
        if not md5_hash:
            md5_hash = client.generate_md5(qr_string)

        base64_uri = client.qr_image(qr_string, format="base64_uri")

        return {
            "success": True,
            "qr_string": qr_string,
            "base64_uri": base64_uri,
            "md5": md5_hash,
            "amount": clean_amount,
            "currency": currency,
            "account_id": Config.BAKONG_ACCOUNT_ID,
            "merchant_name": Config.BAKONG_MERCHANT_NAME,
            "merchant_city": Config.BAKONG_MERCHANT_CITY,
            "bill_number": bill_number,
        }
    except Exception as e:
        logger.error(f"Error generating Bakong KHQR for bill {bill_number}: {e}")
        return {
            "success": False,
            "error": str(e),
            "amount": clean_amount,
            "bill_number": bill_number,
        }


def check_bakong_payment(md5_hash: str) -> dict:
    """
    Queries the National Bank of Cambodia (NBC) Bakong API to verify
    whether a customer has completed payment for the given transaction MD5.
    Returns:
      {"success": True, "paid": True/False, "status": "PAID"|"UNPAID"|"RATE_LIMITED", "details": ...}
    """
    if not md5_hash:
        return {"success": False, "paid": False, "status": "INVALID_HASH"}

    client = get_khqr()
    if not client:
        return {"success": False, "paid": False, "status": "GATEWAY_UNAVAILABLE"}

    try:
        # Query raw response directly to access responseCode and errorCode
        raw_resp = client._KHQR__post_request("/check_transaction_by_md5", {"md5": md5_hash})
        if not isinstance(raw_resp, dict):
            raw_resp = {}

        resp_code = raw_resp.get("responseCode")
        error_code = raw_resp.get("errorCode")
        msg = str(raw_resp.get("responseMessage", ""))

        # Check for NBC Bakong Daily API Rate Limit (free developer tier is capped at 100 calls/day)
        if error_code in [17, 18, 19] or "daily request limit" in msg.lower() or "limit" in msg.lower():
            logger.warning(f"Bakong developer daily API quota exceeded: {msg} (error code {error_code})")
            return {
                "success": False,
                "paid": False,
                "rate_limited": True,
                "status": "RATE_LIMIT_EXCEEDED",
                "message": msg or "Daily request limit of 100 exceeded on Bakong Developer API.",
            }

        if resp_code == 0:
            details = raw_resp.get("data")
            return {
                "success": True,
                "paid": True,
                "status": "PAID",
                "details": details,
            }

        return {
            "success": True,
            "paid": False,
            "status": "UNPAID",
            "message": msg or "Transaction awaiting customer transfer.",
        }
    except Exception as e:
        logger.error(f"Error verifying Bakong payment for MD5 {md5_hash}: {e}")
        return {
            "success": False,
            "paid": False,
            "status": "ERROR",
            "error": str(e),
        }

