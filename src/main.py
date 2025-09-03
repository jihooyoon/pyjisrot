DEFAULT_OUTPUT_DIR_NAME = "jisrot_output"

import os, sys, orjson
import analyze_events_history
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QLabel, QCheckBox, QFileDialog, QMessageBox

log = False
# Init output directory
base_dir = os.getcwd()
output_dir = os.getcwd() + os.sep + DEFAULT_OUTPUT_DIR_NAME

def analyze_history(input_file_paths, output_dir):
    if input_file_paths is None or len(input_file_paths) == 0:
        return (1, "No input files provided.")

    """Analyze the event history data from the given files."""
    for file_path in input_file_paths:
        file_path = os.path.abspath(file_path)   
        if log:
            print(f"Analyzing file: {file_path}")
        
        # Call the analysis function from analyze_event module
        total_data, merchant_data, total_data_sub = analyze_events_history.count_all_stats(file_path, log=log)
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
                                       total_data["start_time_str"] + "_" +
                                       total_data["end_time_str"] +
                                       ".json"),
            "merchant_data": os.path.join(output_dir, f"merchant_data_" +
                                       total_data["start_time_str"] + "_" +
                                       total_data["end_time_str"] +
                                       ".json"),
            "total_data_sub": os.path.join(output_dir, f"total_data_sub_" +
                                       total_data["start_time_str"] + "_" +
                                       total_data["end_time_str"] + 
                                       ".json"),
        }

        
        if log:
            with open(out_file_path["total_data_sub"], 'wb') as fo:
                fo.write(orjson.dumps(total_data_sub, option=orjson.OPT_INDENT_2))
            print(f"Total sub data saved to: {out_file_path["total_data_sub"]}")
        
            with open(out_file_path["merchant_data"], 'wb') as fo:
                fo.write(orjson.dumps(merchant_data, option=orjson.OPT_INDENT_2))
            print(f"Merchant data saved to: {out_file_path["merchant_data"]}")
        
        with open(out_file_path["total_data"], 'wb') as fo:
            fo.write(orjson.dumps(total_data, option=orjson.OPT_INDENT_2))
        if log:
            print(f"Total data saved to: {out_file_path["total_data"]}")
        
    return (0, f"Analysis completed and output files saved to directory:\n {output_dir}!")




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
            QMessageBox.information(self, "Success", exit_message)
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
    
    exec_path = sys.executable
    # Modify path for macOS
    if sys.platform == "darwin":
        if ".app" in exec_path: # If running from a bundled app, set base directory to the directory containing bundled app file
            base_dir = os.path.abspath(os.path.join(exec_path, "..", "..", "..",".."))
        else: 
            base_dir = os.path.dirname(exec_path)

    output_dir = os.path.join(base_dir, DEFAULT_OUTPUT_DIR_NAME)

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
