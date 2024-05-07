import matlab.engine
import numpy as np
import h5py
import sys
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QGridLayout,
    QLabel,
    QVBoxLayout,
    QPushButton,
    QFileDialog,
    QHBoxLayout,
    QSlider,
    QComboBox,
    QGraphicsView,
    QGraphicsScene,
)
from PyQt5.QtGui import QColor, QPalette, QPainter, QFont
from PyQt5.QtCore import Qt

GRAY = QColor("#808080")
WHITE = QColor("#FFFFFF")
SEIZURE = QColor("#0096c7")
SE = QColor("#ee9b00")


class ColorCell(QLabel):
    def __init__(self, color):
        super().__init__()
        self.setAutoFillBackground(True)
        self.setColor(color)
        self.clicked = False

    def setColor(self, color):
        palette = self.palette()
        palette.setColor(QPalette.Window, color)
        self.setPalette(palette)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked = not self.clicked
            self.setColor(
                QColor(255, 0, 0)
                if self.clicked
                else self.palette().color(QPalette.Window)
            )

    def enterEvent(self, event):
        if not self.clicked and self.underMouse():
            self.setColor(self.palette().color(QPalette.Window).lighter(120))

    def leaveEvent(self, event):
        if not self.clicked and not self.underMouse():
            self.setColor(self.palette().color(QPalette.Window).darker(120))


class GridWidget(QWidget):
    def __init__(self, rows, cols):
        super().__init__()
        self.rows = rows
        self.cols = cols
        self.grid = QGridLayout()
        self.grid.setSpacing(0)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.grid)
        self.cells = []
        self.createGrid()

    def createGrid(self):
        self.cells = [[None for _ in range(self.cols)] for _ in range(self.rows)]
        for i in range(self.rows):
            for j in range(self.cols):
                cell = ColorCell(GRAY)
                self.grid.addWidget(cell, i, j)
                self.cells[i][j] = cell

    def resizeEvent(self, event):
        cell_size = min(self.width() // self.cols, self.height() // self.rows)
        for i in range(self.rows):
            for j in range(self.cols):
                self.cells[i][j].setFixedSize(cell_size, cell_size)
        self.setFixedSize(self.cols * cell_size, self.rows * cell_size)


class GraphWidget(QGraphicsView):
    def __init__(self):
        super().__init__()
        self.setRenderHint(QPainter.Antialiasing)
        self.setScene(QGraphicsScene())

    def resizeEvent(self, event):
        self.fitInView(self.sceneRect(), Qt.KeepAspectRatio)


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.file_path = None
        self.tolerance = 40
        self.recording_length = None
        self.time_vector = None
        self.data = None
        self.active_channels = None

        self.eng = matlab.engine.start_matlab()
        self.eng.eval("parpool('Threads')", nargout=0)

        self.setWindowTitle("Spatial SE Viewer")
        self.main_layout = QHBoxLayout()
        self.setLayout(self.main_layout)
        self.setFixedSize(1567, 832)

        self.left_pane = QWidget()
        self.left_layout = QVBoxLayout()
        self.left_pane.setLayout(self.left_layout)
        self.main_layout.addWidget(self.left_pane)

        self.grid_widget = GridWidget(64, 64)
        self.left_layout.addWidget(self.grid_widget)

        self.right_pane = QWidget()
        self.right_layout = QVBoxLayout()
        self.right_pane.setLayout(self.right_layout)
        self.main_layout.addWidget(self.right_pane)

        self.graph_pane = QWidget()
        self.graph_layout = QVBoxLayout()  # Change to QVBoxLayout
        self.graph_pane.setLayout(self.graph_layout)
        self.right_layout.addWidget(self.graph_pane)

        self.graph_widget1 = GraphWidget()
        self.graph_layout.addWidget(self.graph_widget1)

        self.graph_widget2 = GraphWidget()
        self.graph_layout.addWidget(self.graph_widget2)

        self.graph_widget3 = GraphWidget()
        self.graph_layout.addWidget(self.graph_widget3)

        self.graph_widget4 = GraphWidget()
        self.graph_layout.addWidget(self.graph_widget4)

        self.settings_pane = QWidget()
        self.settings_layout = QVBoxLayout()
        self.settings_pane.setLayout(self.settings_layout)
        self.right_layout.addWidget(self.settings_pane)

        self.control_layout = QHBoxLayout()
        self.settings_layout.addLayout(self.control_layout)

        self.open_button = QPushButton(" Open File")
        self.open_button.clicked.connect(self.openFile)
        self.control_layout.addWidget(self.open_button)

        self.run_button = QPushButton(" Run Analysis")
        self.run_button.setEnabled(False)
        self.run_button.clicked.connect(self.run_analysis)
        self.control_layout.addWidget(self.run_button)

        self.clear_button = QPushButton("󰗨 Clear Plots")
        self.run_button.setEnabled(False)
        self.control_layout.addWidget(self.clear_button)

        self.bottom_pane = QWidget()
        self.bottom_layout = QHBoxLayout()
        self.bottom_pane.setLayout(self.bottom_layout)
        self.right_layout.addWidget(self.bottom_pane)

        self.playback_layout = QHBoxLayout()
        self.bottom_layout.addLayout(self.playback_layout)

        self.skip_backward_button = QPushButton("")
        self.skip_backward_button.clicked.connect(self.skipBackward)
        self.playback_layout.addWidget(self.skip_backward_button)

        self.prev_frame_button = QPushButton("")
        self.prev_frame_button.clicked.connect(self.prevFrame)
        self.playback_layout.addWidget(self.prev_frame_button)

        self.play_pause_button = QPushButton("")
        self.play_pause_button.clicked.connect(self.playPause)
        self.playback_layout.addWidget(self.play_pause_button)

        self.next_frame_button = QPushButton("")
        self.next_frame_button.clicked.connect(self.nextFrame)
        self.playback_layout.addWidget(self.next_frame_button)
        self.skip_forward_button = QPushButton("")

        self.skip_forward_button.clicked.connect(self.skipForward)
        self.playback_layout.addWidget(self.skip_forward_button)

        self.progress_bar = QSlider(Qt.Horizontal)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setTickPosition(QSlider.NoTicks)
        self.progress_bar.setTickInterval(0)
        self.progress_bar.valueChanged.connect(self.seekPosition)
        self.playback_layout.addWidget(self.progress_bar)

        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["0.5", "1", "1.5", "2.0"])
        self.playback_layout.addWidget(self.speed_combo)
        self.speed_combo.setCurrentIndex(1)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.adjustGridSize()

    def adjustGridSize(self):
        window_width = self.width()
        grid_size = window_width // 2
        self.left_pane.setFixedWidth(grid_size)
        cell_size = grid_size // 64
        self.grid_widget.setFixedSize(64 * cell_size, 64 * cell_size)

    def openFile(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open File",
            directory="/Users/booka66/Jake-Squared/Sz_SE_Detection/",
            filter="BRW Files (*.brw)",
        )
        if file_path:
            print("Selected file path:", file_path)
            self.file_path = file_path
            self.run_button.setEnabled(True)

    def get_channels(self):
        with h5py.File(self.file_path, "r") as f:
            recElectrodeList = f["/3BRecInfo/3BMeaStreams/Raw/Chs"]
            rows = recElectrodeList["Row"][()]
            cols = recElectrodeList["Col"][()]
        return rows, cols

    def create_grid(self):
        # Reset all cells to gray
        for row in self.grid_widget.cells:
            for cell in row:
                cell.setColor(GRAY)
        for row, col in self.active_channels:
            self.grid_widget.cells[row - 1][col - 1].setColor(WHITE)

    def update_grid(self):
        for row, col in self.active_channels:
            found_se = False
            found_seizure = False

            se_times = self.data[row - 1, col - 1]["SE_List"]
            seizure_times = self.data[row - 1, col - 1]["SzEventsTimes"]

            if se_times:
                for timerange in se_times:
                    if len(timerange) == 1:
                        start = se_times[0][0]
                        stop = se_times[1][0]
                        if start <= self.progress_bar.value() <= stop:
                            self.grid_widget.cells[row - 1][col - 1].setColor(SE)
                            found_se = True
                            break
                    else:
                        start, stop = timerange
                        if start <= self.progress_bar.value() <= stop:
                            self.grid_widget.cells[row - 1][col - 1].setColor(SE)
                            found_se = True
                            break

            if seizure_times:
                for timerange in seizure_times:
                    if len(timerange) == 1:
                        start = seizure_times[0][0]
                        stop = seizure_times[1][0]
                        if start <= self.progress_bar.value() <= stop:
                            self.grid_widget.cells[row - 1][col - 1].setColor(SEIZURE)
                            found_seizure = True
                            print(f"Seizure at {row}, {col}")
                            print(f"Start: {start}, Stop: {stop}")
                            print(f"Timerange: {timerange}")
                            print(f"Progress: {self.progress_bar.value()}")
                            break
                    else:
                        start, stop = timerange
                        if start <= self.progress_bar.value() <= stop:
                            self.grid_widget.cells[row - 1][col - 1].setColor(SEIZURE)
                            found_seizure = True
                            print(f"Seizure at {row}, {col}")
                            print(f"Start: {start}, Stop: {stop}")
                            print(f"Timerange: {timerange}")
                            print(f"Progress: {self.progress_bar.value()}")
                            break
            if not found_se and not found_seizure:
                self.grid_widget.cells[row - 1][col - 1].setColor(WHITE)

    def run_analysis(self):
        data_cell, total_channels, sampling_rate, num_rec_frames = (
            self.eng.vectorized_state_extractor(
                self.file_path, self.tolerance, nargout=4
            )
        )

        total_channels = int(total_channels)
        sampling_rate = float(sampling_rate)
        num_rec_frames = int(num_rec_frames)

        # Convert data_cell from MATLAB cell array to numpy array
        data_np = np.array(data_cell)

        # Reshape data_np to a 2D array
        self.data = data_np.reshape((64, 64))

        # Access individual elements of data_2d
        # for i in range(64):
        #     for j in range(64):
        #         signal = data_2d[i, j]["signal"]
        #         name = data_2d[i, j]["name"]
        #         sz_events_times = data_2d[i, j]["SzEventsTimes"]
        #         se_list = data_2d[i, j]["SE_List"]

        self.recording_length = (1 / sampling_rate) * (num_rec_frames - 1)
        self.time_vector = [i / sampling_rate for i in range(num_rec_frames)]
        self.progress_bar.setRange(0, int(self.recording_length))

        print("Data shape:", self.data.shape)
        print("Total channels:", total_channels)
        print("Sampling rate:", sampling_rate)
        print("Number of recording frames:", num_rec_frames)
        print("Recording length:", self.recording_length)

        rows, cols = self.get_channels()
        self.active_channels = list(zip(rows, cols))

        self.create_grid()
        self.update_grid()

    def skipBackward(self):
        print("Skip Backward")
        # Update the progress bar and timestamp label accordingly

    def prevFrame(self):
        print("Previous Frame")
        # Update the progress bar and timestamp label accordingly

    def playPause(self):
        if self.play_pause_button.text() == "":
            self.play_pause_button.setText("")
            print("Play")
            # Start updating the progress bar and timestamp label periodically
        else:
            self.play_pause_button.setText("")
            print("Pause")
            # Stop updating the progress bar and timestamp label

    def nextFrame(self):
        print("Next Frame")
        # Update the progress bar and timestamp label accordingly

    def skipForward(self):
        print("Skip Forward")
        # Update the progress bar and timestamp label accordingly

    def seekPosition(self, value):
        print(f"Seek position: {value}")
        self.update_grid()
        # Update the playback position based on the progress bar value


if __name__ == "__main__":
    app = QApplication(sys.argv)
    font = QFont("Hack Nerd Font Mono", 13)  # 10 is the font size, adjust as needed
    app.setFont(font)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
