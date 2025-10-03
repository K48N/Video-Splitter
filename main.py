"""
Video Editor Pro - Main Entry Point
"""
import sys
import logging
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import Qt

from ui.main_app import VideoEditorApp


def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('video_editor.log'),
            logging.StreamHandler()
        ]
    )


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