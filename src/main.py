DEFAULT_OUTPUT_DIR = "jisrot_output"

import os, sys, json
import analyze_events_history
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QLabel, QCheckBox, QFileDialog, QMessageBox

log = False
output_dir = DEFAULT_OUTPUT_DIR

def analyze_history(input_file_paths, output_dir):
    if input_file_paths is None or len(input_file_paths) == 0:
        return (1, "No input files provided.")

    """Analyze the event history data from the given files."""
    for file_path in input_file_paths:
        if log:
            print(f"Analyzing file: {file_path}")
        
        # Call the analysis function from analyze_event module
        total_data, merchant_data = analyze_events_history.count_all_stats(file_path, log=log)
        try:
            os.makedirs(output_dir)
            if log:
                print(f"Created output directory: {output_dir}")
        except FileExistsError:
            if log:
                print(f"Output directory already exists: {output_dir}")
        except OSError as e:
            if log:
                print(f"Error creating output directory {output_dir}: {e}")
        
        out_file_path = {
            "total_data": os.path.join(output_dir, f"total_data_" +
                                       total_data["start_time"].replace(" ", "_").replace(":","-") + "_" +
                                       total_data["end_time"].replace(" ", "_").replace(":","-") +
                                       ".json"),
            "merchant_data": os.path.join(output_dir, f"merchant_data_" +
                                       total_data["start_time"].replace(" ", "_").replace(":","-") + "_" +
                                       total_data["end_time"].replace(" ", "_").replace(":","-") +
                                       ".json"),
        }

        with open(out_file_path["total_data"], 'w', encoding="utf-8") as fo:
            json.dump(total_data, fo, ensure_ascii=False, indent=4)
        if log:
            print(f"Total data saved to: {out_file_path["total_data"]}")
        
        if log:
            with open(out_file_path["merchant_data"], 'w', encoding="utf-8") as fo:
                json.dump(merchant_data, fo, ensure_ascii=False, indent=4)
            print(f"Merchant data saved to: {out_file_path["merchant_data"]}")
        
    return (0, "Analysis completed successfully.")




class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Jisrot - Event Analyzer")
        
        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)        

        self.label = QLabel("Open event history data file(s) to analyze", self)
        layout.addWidget(self.label)

        self.select_csv_button = QPushButton("Browse file(s)", self)
        self.select_csv_button.clicked.connect(self.on_select_csv_btn_clicked)
        layout.addWidget(self.select_csv_button)

        self.debug_log_checkbox = QCheckBox("Enable debug logging", self)
        self.debug_log_checkbox.stateChanged.connect(self.toggle_debug_logging)
        layout.addWidget(self.debug_log_checkbox)
        
        self.setCentralWidget(central_widget)

    def on_select_csv_btn_clicked(self):
        file_paths, _ = QFileDialog.getOpenFileNames(self, "Select event history data file(s)", "", "CSV Files (*.csv);;All Files (*)")
        if log:
            print("Selected File(s):\n", file_paths)
        
        (exit_code, exit_message) = analyze_history(file_paths, output_dir)
        if exit_code == 0:
            QMessageBox.information(self, "Success", f"Analysis completed and output files saved to directory:\n {output_dir}!")
        else:
            if log:
                print(f"Error: {exit_message}")

    def toggle_debug_logging(self):
        global log
        log = self.debug_log_checkbox.isChecked()


if __name__ == "__main__":
    if "--debug" in sys.argv:
        log = True
        print("Debug mode is ON")
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
