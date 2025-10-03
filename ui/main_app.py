"""
Main application window integrating all panels
"""
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                            QMenuBar, QMenu, QAction, QFileDialog, QMessageBox,
                            QSplitter, QStatusBar, QApplication, QInputDialog)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QKeySequence
import os
import tempfile
from typing import List, Optional

from core.segment import Segment
from core.video_engine import VideoEngine, ProcessingOptions, ProcessingResult
from core.undo_manager import (UndoManager, AddSegmentCommand, RemoveSegmentCommand,
                               ModifySegmentCommand)
from core.preset_manager import PresetManager
from core.audio_processor import AudioProcessor
from core.recent_projects import RecentProjectsManager
from core.autosave import AutoSaveManager
from core.filename_templates import FilenameTemplate
from ui.themes.dark_theme import PortfolioTheme
from ui.panels.control_panel import ControlPanel
from ui.panels.timeline_panel import TimelinePanel
from ui.panels.preview_panel import VideoPreview
from ui.panels.parts_panel import PartsPanel
from ui.dialogs.batch_dialog import BatchDialog
from ui.dialogs.scene_dialog import SceneDetectionDialog
from ui.dialogs.advanced_dialogs import (
    VideoInfoDialog, TimeInputDialog, 
    ColorPickerDialog, AudioProcessingDialog
)


class ProcessingThread(QThread):
    """Background thread for video processing"""
    
    progress = pyqtSignal(int, int, str)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)
    
    def __init__(self, engine, segments, output_dir, options):
        super().__init__()
        self.engine = engine
        self.segments = segments
        self.output_dir = output_dir
        self.options = options
    
    def run(self):
        try:
            results = self.engine.process_segments(
                self.segments,
                self.output_dir,
                self.options,
                progress_callback=self.progress.emit
            )
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))


class VideoEditorApp(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        
        # Phase 1-4 components
        self.engine = VideoEngine()
        self.undo_manager = UndoManager()
        self.preset_manager = PresetManager()
        self.segments = []
        self.current_video = None
        self.processing_thread = None
        
        # Phase 5 components
        self.audio_processor = AudioProcessor()
        self.recent_projects = RecentProjectsManager()
        self.autosave = AutoSaveManager()
        self.filename_template = FilenameTemplate()
        
        # Setup auto-save
        self.autosave.set_save_callback(self._autosave_project)
        self.autosave.start()
        
        self.setWindowTitle("Video Editor Pro")
        self.setMinimumSize(1400, 900)
        
        self._setup_ui()
        self._setup_menu()
        self._connect_signals()
        self._apply_theme()
        
        self.statusBar().showMessage("Ready")
    
    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        
        layout = QHBoxLayout(central)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        self.control_panel = ControlPanel()
        layout.addWidget(self.control_panel)
        
        right_splitter = QSplitter(Qt.Vertical)
        
        self.preview_panel = VideoPreview()
        right_splitter.addWidget(self.preview_panel)
        
        self.timeline_panel = TimelinePanel()
        right_splitter.addWidget(self.timeline_panel)
        
        self.parts_panel = PartsPanel()
        right_splitter.addWidget(self.parts_panel)
        
        right_splitter.setSizes([500, 150, 250])
        
        layout.addWidget(right_splitter, stretch=1)
    
    def _setup_menu(self):
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        open_action = QAction("Open Video", self)
        open_action.setShortcut(QKeySequence.Open)
        open_action.triggered.connect(self._open_video)
        file_menu.addAction(open_action)
        
        file_menu.addSeparator()
        
        save_action = QAction("Save Project", self)
        save_action.setShortcut(QKeySequence.Save)
        save_action.triggered.connect(self._save_project)
        file_menu.addAction(save_action)
        
        load_action = QAction("Load Project", self)
        load_action.triggered.connect(self._load_project)
        file_menu.addAction(load_action)
        
        file_menu.addSeparator()
        
        # Recent projects submenu
        self.recent_menu = file_menu.addMenu("Recent Projects")
        self._update_recent_menu()
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.setShortcut(QKeySequence.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Edit menu
        edit_menu = menubar.addMenu("Edit")
        
        self.undo_action = QAction("Undo", self)
        self.undo_action.setShortcut(QKeySequence.Undo)
        self.undo_action.triggered.connect(self._undo)
        self.undo_action.setEnabled(False)
        edit_menu.addAction(self.undo_action)
        
        self.redo_action = QAction("Redo", self)
        self.redo_action.setShortcut(QKeySequence.Redo)
        self.redo_action.triggered.connect(self._redo)
        self.redo_action.setEnabled(False)
        edit_menu.addAction(self.redo_action)
        
        # Tools menu
        tools_menu = menubar.addMenu("Tools")
        
        batch_action = QAction("Batch Processing...", self)
        batch_action.triggered.connect(self._open_batch_dialog)
        tools_menu.addAction(batch_action)
        
        scene_action = QAction("Auto-Detect Segments...", self)
        scene_action.triggered.connect(self._open_scene_dialog)
        scene_action.setShortcut("Ctrl+D")
        tools_menu.addAction(scene_action)
        
        tools_menu.addSeparator()
        
        presets_action = QAction("Manage Presets...", self)
        presets_action.triggered.connect(self._manage_presets)
        tools_menu.addAction(presets_action)
        
        tools_menu.addSeparator()
        
        # Phase 5: Audio processing
        audio_action = QAction("Audio Processing...", self)
        audio_action.triggered.connect(self._open_audio_dialog)
        audio_action.setShortcut("Ctrl+Shift+A")
        tools_menu.addAction(audio_action)
        
        # Phase 5: Video info
        info_action = QAction("Video Information...", self)
        info_action.triggered.connect(self._show_video_info)
        info_action.setShortcut("Ctrl+I")
        tools_menu.addAction(info_action)
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        
        about_action = QAction("About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    def _connect_signals(self):
        self.control_panel.export_requested.connect(self._start_export)
        self.preview_panel.position_changed.connect(self.timeline_panel.set_current_time)
        self.preview_panel.add_segment_button.clicked.connect(self._add_segment_from_preview)
        self.timeline_panel.segment_clicked.connect(self._on_segment_clicked)
        self.timeline_panel.segment_modified.connect(self._on_segment_modified_timeline)
        self.parts_panel.segment_clicked.connect(self._on_segment_clicked)
        self.parts_panel.segment_modified.connect(self._on_segment_modified_table)
        self.parts_panel.segment_deleted.connect(self._delete_segment)
        self.parts_panel.clear_all_requested.connect(self._clear_all_segments)
        self.undo_manager.add_callback(self._update_undo_actions)
    
    def _apply_theme(self):
        self.setStyleSheet(PortfolioTheme.get_stylesheet())
        
        self.menuBar().setStyleSheet(f"""
            QMenuBar {{
                background: {PortfolioTheme.SECONDARY};
                color: {PortfolioTheme.WHITE};
                border-bottom: 1px solid {PortfolioTheme.BORDER};
            }}
            QMenuBar::item:selected {{
                background: {PortfolioTheme.TERTIARY};
            }}
            QMenu {{
                background: {PortfolioTheme.TERTIARY};
                color: {PortfolioTheme.WHITE};
                border: 1px solid {PortfolioTheme.BORDER};
            }}
            QMenu::item:selected {{
                background: {PortfolioTheme.ACCENT};
            }}
        """)
        
        self.statusBar().setStyleSheet(f"""
            QStatusBar {{
                background: {PortfolioTheme.SECONDARY};
                color: {PortfolioTheme.GRAY_LIGHTER};
                border-top: 1px solid {PortfolioTheme.BORDER};
            }}
        """)
    
    def _open_video(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Video",
            "",
            "Video Files (*.mp4 *.mkv *.avi *.mov *.wmv);;All Files (*)"
        )
        
        if not file_path:
            return
        
        try:
            self.statusBar().showMessage("Loading video...")
            QApplication.processEvents()
            
            info = self.engine.load_video(file_path)
            self.current_video = file_path
            
            self.preview_panel.load_video(file_path)
            self.timeline_panel.set_duration(info['duration'])
            
            self.segments.clear()
            self.undo_manager.clear()
            self._update_ui()
            
            duration = info['duration']
            minutes = int(duration // 60)
            seconds = int(duration % 60)
            self.statusBar().showMessage(
                f"Loaded: {os.path.basename(file_path)} ({minutes}:{seconds:02d})"
            )
            
            # Skip waveform for long videos
            if duration < 3600:
                QTimer.singleShot(500, self._generate_waveform)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load video:\n{str(e)}")
    
    def _generate_waveform(self):
        if not self.current_video:
            return
        
        try:
            temp_path = os.path.join(tempfile.gettempdir(), "waveform.png")
            if self.engine.generate_waveform(temp_path):
                self.timeline_panel.set_waveform(temp_path)
        except:
            pass
    
    def _add_segment_from_preview(self):
        start, end = self.preview_panel.get_segment_range()
        
        if end <= start:
            return
        
        segment = Segment(
            start=start,
            end=end,
            label=f"Part {len(self.segments) + 1}"
        )
        
        cmd = AddSegmentCommand(self.segments, segment)
        self.undo_manager.execute(cmd)
        
        self.preview_panel.clear_markers()
        self._update_ui()
        self.statusBar().showMessage(f"Added segment: {segment.label}")
    
    def _delete_segment(self, index):
        if 0 <= index < len(self.segments):
            segment = self.segments[index]
            cmd = RemoveSegmentCommand(self.segments, segment)
            self.undo_manager.execute(cmd)
            self._update_ui()
    
    def _clear_all_segments(self):
        if not self.segments:
            return
        
        reply = QMessageBox.question(
            self,
            "Clear All",
            "Delete all segments?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.segments.clear()
            self.undo_manager.clear()
            self._update_ui()
    
    def _on_segment_clicked(self, index):
        if 0 <= index < len(self.segments):
            segment = self.segments[index]
            self.preview_panel.seek_to(segment.start)
            self.parts_panel.select_segment(index)
    
    def _on_segment_modified_timeline(self, index, new_start, new_end):
        if 0 <= index < len(self.segments):
            self.segments[index].start = new_start
            self.segments[index].end = new_end
            self._update_ui()
    
    def _on_segment_modified_table(self, index, segment):
        if 0 <= index < len(self.segments):
            self.segments[index] = segment
            self._update_ui()
    
    def _update_ui(self):
        self.timeline_panel.set_segments(self.segments)
        self.parts_panel.set_segments(self.segments)
        self.control_panel.set_export_enabled(len(self.segments) > 0)
    
    def _undo(self):
        if self.undo_manager.undo():
            self._update_ui()
    
    def _redo(self):
        if self.undo_manager.redo():
            self._update_ui()
    
    def _update_undo_actions(self):
        self.undo_action.setEnabled(self.undo_manager.can_undo())
        self.redo_action.setEnabled(self.undo_manager.can_redo())
    
    def _start_export(self, output_dir, options):
        if not self.segments:
            QMessageBox.warning(self, "No Segments", "Add segments before exporting.")
            return
        
        errors = self.engine.validate_segments(self.segments)
        if errors:
            QMessageBox.critical(self, "Error", "\n".join(errors))
            return
        
        self.processing_thread = ProcessingThread(
            self.engine, self.segments, output_dir, options
        )
        
        self.processing_thread.progress.connect(self._on_export_progress)
        self.processing_thread.finished.connect(self._on_export_finished)
        self.processing_thread.error.connect(self._on_export_error)
        
        self.processing_thread.start()
        self.control_panel.set_export_enabled(False)
    
    def _on_export_progress(self, current, total, message):
        self.control_panel.show_progress(current, total, message)
    
    def _on_export_finished(self, results):
        self.control_panel.hide_progress()
        self.control_panel.set_export_enabled(True)
        
        successes = sum(1 for r in results if r.success)
        QMessageBox.information(self, "Complete", f"Exported {successes} segments!")
    
    def _on_export_error(self, error):
        self.control_panel.hide_progress()
        self.control_panel.set_export_enabled(True)
        QMessageBox.critical(self, "Error", error)
    
    # Phase 4 methods
    def _open_batch_dialog(self):
        """Open batch processing dialog"""
        if not self.segments:
            QMessageBox.warning(
                self,
                "No Segments",
                "Please create segments first before batch processing."
            )
            return
        
        dialog = BatchDialog(self.segments, self)
        dialog.exec_()
    
    def _open_scene_dialog(self):
        """Open scene detection dialog"""
        if not self.current_video:
            QMessageBox.warning(
                self,
                "No Video",
                "Please load a video first."
            )
            return
        
        dialog = SceneDetectionDialog(self.current_video, self)
        dialog.segments_detected.connect(self._add_detected_segments)
        dialog.exec_()
    
    def _add_detected_segments(self, segments):
        """Add detected segments to timeline"""
        for segment in segments:
            cmd = AddSegmentCommand(self.segments, segment)
            self.undo_manager.execute(cmd)
        
        self._update_ui()
        self.statusBar().showMessage(f"Added {len(segments)} detected segments")
    
    def _manage_presets(self):
        """Show preset management dialog"""
        presets = self.preset_manager.list_presets()
        
        preset, ok = QInputDialog.getItem(
            self,
            "Load Preset",
            "Select preset:",
            presets,
            0,
            False
        )
        
        if ok and preset:
            options = self.preset_manager.load_preset(preset)
            if options:
                self._apply_preset_to_ui(options)
                self.statusBar().showMessage(f"Loaded preset: {preset}")
    
    def _apply_preset_to_ui(self, options):
        """Apply preset options to UI"""
        control = self.control_panel
        
        # Audio
        audio_map = {None: 0, 'mono': 1, 'stereo': 2}
        control.audio_combo.setCurrentIndex(audio_map.get(options.audio_channels, 0))
        
        # Settings
        quality_map = {0: 0, 5: 1, 9: 2}
        control.mp3_quality_combo.setCurrentIndex(quality_map.get(options.mp3_quality, 1))
        control.codec_copy.setChecked(options.codec_copy)
        control.use_gpu.setChecked(options.use_gpu)
        control.video_format_combo.setCurrentText(options.output_format)
        control.parallel_processing.setChecked(options.parallel_processing)
        control.max_workers.setValue(options.max_workers)
    
    # Phase 5 methods
    def _update_recent_menu(self):
        """Update recent projects menu"""
        self.recent_menu.clear()
        recent = self.recent_projects.get_recent()
        
        if not recent:
            no_action = self.recent_menu.addAction("No Recent Projects")
            no_action.setEnabled(False)
            return
        
        for project in recent[:10]:
            action = self.recent_menu.addAction(project['name'])
            action.triggered.connect(
                lambda checked, p=project['path']: self._open_recent_project(p)
            )
        
        self.recent_menu.addSeparator()
        clear_action = self.recent_menu.addAction("Clear Recent")
        clear_action.triggered.connect(self._clear_recent)
    
    def _open_recent_project(self, path):
        """Open recent project"""
        if os.path.exists(path):
            try:
                import json
                with open(path, 'r') as f:
                    data = json.load(f)
                
                if data.get('video') and os.path.exists(data['video']):
                    info = self.engine.load_video(data['video'])
                    self.current_video = data['video']
                    self.preview_panel.load_video(data['video'])
                    self.timeline_panel.set_duration(info['duration'])
                
                self.segments = [Segment.from_dict(s) for s in data.get('segments', [])]
                self._update_ui()
                
                self.statusBar().showMessage(f"Loaded: {os.path.basename(path)}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load:\n{str(e)}")
        else:
            QMessageBox.warning(self, "Not Found", "Project file no longer exists")
    
    def _clear_recent(self):
        """Clear recent projects"""
        self.recent_projects.clear()
        self._update_recent_menu()
    
    def _autosave_project(self, backup_path):
        """Auto-save callback"""
        if not self.segments:
            return
        
        try:
            import json
            with open(backup_path, 'w') as f:
                json.dump({
                    'video': self.current_video,
                    'segments': [s.to_dict() for s in self.segments]
                }, f)
        except:
            pass
    
    def _show_video_info(self):
        """Show video information dialog"""
        if not self.current_video or not self.engine.video_info:
            QMessageBox.warning(self, "No Video", "Please load a video first.")
            return
        
        dialog = VideoInfoDialog(self.engine.video_info, self)
        dialog.exec_()
    
    def _open_audio_dialog(self):
        """Open audio processing dialog"""
        if not self.current_video:
            QMessageBox.warning(self, "No Video", "Please load a video first.")
            return
        
        dialog = AudioProcessingDialog(self)
        dialog.processing_requested.connect(self._process_audio)
        dialog.exec_()
    
    def _process_audio(self, operation, params):
        """Process audio for current video"""
        if not self.current_video:
            return
        
        output_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Processed Video",
            "",
            "Video Files (*.mp4 *.mkv)"
        )
        
        if not output_path:
            return
        
        try:
            self.statusBar().showMessage(f"Processing audio ({operation})...")
            QApplication.processEvents()
            
            success = self.audio_processor.process_video_audio(
                self.current_video,
                output_path,
                operation,
                **params
            )
            
            if success:
                QMessageBox.information(
                    self,
                    "Success",
                    f"Audio processed successfully!\nSaved to: {output_path}"
                )
            else:
                QMessageBox.warning(self, "Failed", "Audio processing failed")
            
            self.statusBar().showMessage("Ready")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Processing failed:\n{str(e)}")
            self.statusBar().showMessage("Ready")
    
    def _save_project(self):
        if not self.segments:
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Project", "", "Project Files (*.vedproj)"
        )
        
        if not file_path:
            return
        
        try:
            import json
            with open(file_path, 'w') as f:
                json.dump({
                    'video': self.current_video,
                    'segments': [s.to_dict() for s in self.segments]
                }, f, indent=2)
            
            # Add to recent projects
            self.recent_projects.add_project(file_path, self.current_video)
            self._update_recent_menu()
            
            self.statusBar().showMessage(f"Saved: {os.path.basename(file_path)}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save:\n{str(e)}")
    
    def _load_project(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Project", "", "Project Files (*.vedproj)"
        )
        
        if not file_path:
            return
        
        try:
            import json
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            if data.get('video') and os.path.exists(data['video']):
                info = self.engine.load_video(data['video'])
                self.current_video = data['video']
                self.preview_panel.load_video(data['video'])
                self.timeline_panel.set_duration(info['duration'])
            
            self.segments = [Segment.from_dict(s) for s in data.get('segments', [])]
            self._update_ui()
            
            # Add to recent
            self.recent_projects.add_project(file_path, data.get('video'))
            self._update_recent_menu()
            
            self.statusBar().showMessage(f"Loaded: {os.path.basename(file_path)}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load:\n{str(e)}")
    
    def _show_about(self):
        QMessageBox.about(self, "About", "Video Editor Pro\n\nProfessional video editor with advanced features")