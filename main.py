"""
Video Editor Pro - Main Entry Point
AI-powered video editing and enhancement suite.
"""
import sys
import logging
import traceback
from pathlib import Path
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import Qt

from config import config
from services import (
    ServiceRegistry,
    BackgroundJobManager,
    ExportQueueService,
    AIService,
    AudioEnhancementService,
    MediaCacheService
)
from ui.main_app import VideoEditorApp

logger = logging.getLogger(__name__)

def setup_logging():
    """Setup logging configuration."""
    log_file = Path(config.get("export", "temp_directory")) / "video_editor.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(str(log_file)),
            logging.StreamHandler()
        ]
    )

def initialize_services():
    """Initialize and start all application services."""
    registry = ServiceRegistry()
    
    # Register services in dependency order
    registry.register(BackgroundJobManager)
    registry.register(MediaCacheService)
    registry.register(ExportQueueService)
    registry.register(AIService)
    registry.register(AudioEnhancementService)
    
    try:
        # Start all services
        registry.start_all()
        logger.info("All services started successfully")
    except Exception as e:
        logger.error(f"Failed to start services: {e}")
        QMessageBox.critical(
            None,
            "Service Error",
            f"Failed to start required services:\n{str(e)}\n\nThe application may not function correctly."
        )

def cleanup_services():
    """Clean up and stop all services."""
    try:
        ServiceRegistry().stop_all()
        logger.info("All services stopped successfully")
    except Exception as e:
        logger.error(f"Error during service cleanup: {e}")

def exception_handler(exctype, value, tb):
    """Global exception handler to log unhandled exceptions."""
    logger.critical("Unhandled exception:", exc_info=(exctype, value, tb))
    traceback.print_exception(exctype, value, tb)
    
    # Show error dialog to user
    error_msg = f"An unexpected error occurred:\n\n{str(value)}\n\nCheck the log file for details."
    QMessageBox.critical(None, "Error", error_msg)

def main():
    """Application entry point."""
    # Set up logging first
    setup_logging()
    logger.info("Starting Video Editor Pro")
    
    # Install global exception handler
    sys.excepthook = exception_handler
    
    # Create Qt application
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Use Fusion style for better dark theme support
    
    try:
        # Initialize services
        initialize_services()
        
        # Create and show main window
        window = VideoEditorApp()
        window.show()
        
        # Set up cleanup on app exit
        app.aboutToQuit.connect(cleanup_services)
        
        # Start event loop
        return app.exec_()
        
    except Exception as e:
        logger.critical(f"Failed to start application: {e}")
        QMessageBox.critical(
            None,
            "Startup Error",
            f"Failed to start the application:\n\n{str(e)}"
        )
        return 1

if __name__ == '__main__':
    sys.exit(main())


def check_crash_recovery():
    """Check for crash recovery files"""
    try:
        from core.autosave import AutoSaveManager
        autosave = AutoSaveManager()
        
        if autosave.has_recovery_files():
            reply = QMessageBox.question(
                None,
                "Crash Recovery",
                "Found auto-saved projects from a previous session.\n\n"
                "Would you like to recover them?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                recovery_files = autosave.get_recovery_files()
                if recovery_files:
                    # Show list of recovery files
                    file_list = "\n".join([f['name'] for f in recovery_files[:5]])
                    QMessageBox.information(
                        None,
                        "Recovery Files",
                        f"Found {len(recovery_files)} recovery file(s):\n\n{file_list}\n\n"
                        "Use File → Recent Projects to open them."
                    )
            else:
                # Clear recovery files if user declines
                autosave.clear_recovery_files()
    except Exception as e:
        logging.error(f"Crash recovery check failed: {str(e)}")


def main():
    """Main entry point"""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        # Set attributes BEFORE creating QApplication
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
        
        # Create application
        app = QApplication(sys.argv)
        app.setApplicationName("Video Editor Pro")
        
        # Check for crash recovery
        check_crash_recovery()
        
        # Create and show main window
        window = VideoEditorApp()
        window.show()
        
        logger.info("Application started successfully")
        
        # Run event loop
        sys.exit(app.exec_())
        
    except Exception as e:
        logger.error(f"Application failed to start: {str(e)}", exc_info=True)
        QMessageBox.critical(
            None,
            "Startup Error",
            f"Failed to start application:\n\n{str(e)}"
        )
        sys.exit(1)


if __name__ == '__main__':
    main()