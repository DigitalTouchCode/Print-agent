import base64
import logging

from flask import Flask, jsonify, request
from flask_cors import CORS

from . import config, printer
from .version import __version__

logger = logging.getLogger("dt_print_agent")


def create_app() -> Flask:
    app = Flask(__name__)
    CORS(app, origins=config.ALLOWED_ORIGINS)

    @app.get("/health")
    def health():
        return jsonify({"status": "ok", "version": __version__})

    @app.get("/devices")
    def devices():
        try:
            return jsonify({"devices": printer.list_devices()})
        except Exception as e:
            logger.exception("Failed to list USB devices")
            return jsonify({"error": str(e)}), 500

    @app.post("/print")
    def print_job():
        body = request.get_json(silent=True) or {}
        vendor_id, product_id, data_b64 = body.get("vendorId"), body.get("productId"), body.get("data")
        if vendor_id is None or product_id is None or not data_b64:
            return jsonify({"error": "vendorId, productId and data are required"}), 400
        try:
            data = base64.b64decode(data_b64)
        except Exception:
            return jsonify({"error": "data must be base64-encoded"}), 400
        try:
            printer.send_raw(int(vendor_id), int(product_id), data)
            return jsonify({"status": "ok"})
        except printer.PrinterNotFound as e:
            return jsonify({"error": str(e)}), 503
        except printer.PrinterWriteError as e:
            logger.warning("Print failed: %s", e)
            return jsonify({"error": str(e)}), 502
        except Exception as e:
            logger.exception("Unexpected print failure")
            return jsonify({"error": f"Unexpected error: {e}"}), 500

    return app


def run():
    app = create_app()
    # threaded=True so a slow print job doesn't block a concurrent /health poll
    app.run(host=config.HOST, port=config.PORT, threaded=True)
