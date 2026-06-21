import sys
import traceback
import logging
from app.routes import app, traffic_manager

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    try:
        app.run(debug=True)
    except Exception as e:
        logger.critical(f"Fatal error: {str(e)}")
        logger.critical(traceback.format_exc())
        sys.exit(1)
