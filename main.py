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
    QSizePolicy,
    QGraphicsView,
    QGraphicsScene,
)
from PyQt5.QtGui import QColor, QPalette, QPainter, QFont, QPen
from PyQt5.QtCore import Qt, QTimer, QSize, pyqtSignal

import matplotlib

matplotlib.use("Qt5Agg")
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT
from matplotlib.figure import Figure

BLACK = QColor("#000000")
GRAY = QColor("#808080")
WHITE = QColor("#FFFFFF")

GREEN = QColor("#00ff00")

SEIZURE = QColor("#0096c7")
SE = QColor("#ee9b00")


class ColorCell(QLabel):
    clicked = pyqtSignal(int, int)

    def __init__(self, row, col, color):
        super().__init__()
        self.setAutoFillBackground(True)
        self.setColor(color)
        self.clicked_state = False
        self.hover_color = BLACK
        self.selected_color = GREEN
        self.hover_width = 2
        self.selected_width = 2
        self.row = row
        self.col = col

    def setColor(self, color):
        palette = self.palette()
        palette.setColor(QPalette.Window, color)
        self.setPalette(palette)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked_state = not self.clicked_state
            self.clicked.emit(self.row, self.col)
            self.update()

    def enterEvent(self, event):
        if not self.clicked_state and self.underMouse():
            self.setColor(self.palette().color(QPalette.Window))
            self.update()

    def leaveEvent(self, event):
        if not self.clicked_state and not self.underMouse():
            self.setColor(self.palette().color(QPalette.Window))
            self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.underMouse() and not self.clicked_state:
            painter = QPainter(self)
            painter.setPen(QPen(self.hover_color, self.hover_width))
            painter.drawRect(
                self.rect().adjusted(
                    self.hover_width // 2,
                    self.hover_width // 2,
                    -self.hover_width // 2,
                    -self.hover_width // 2,
                )
            )
        elif self.clicked_state:
            painter = QPainter(self)
            painter.setPen(QPen(self.selected_color, self.selected_width))
            painter.drawRect(
                self.rect().adjusted(
                    self.selected_width // 2,
                    self.selected_width // 2,
                    -self.selected_width // 2,
                    -self.selected_width // 2,
                )
            )


class GridWidget(QWidget):
    cell_clicked = pyqtSignal(int, int)

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
        self.selected_cell = None

    def createGrid(self):
        self.cells = [[None for _ in range(self.cols)] for _ in range(self.rows)]
        for i in range(self.rows):
            for j in range(self.cols):
                cell = ColorCell(i, j, GRAY)
                cell.clicked.connect(self.on_cell_clicked)  # Connect the clicked signal
                self.grid.addWidget(cell, i, j)
                self.cells[i][j] = cell

    def resizeEvent(self, event):
        cell_size = min(self.width() // self.cols, self.height() // self.rows)
        for i in range(self.rows):
            for j in range(self.cols):
                self.cells[i][j].setFixedSize(cell_size, cell_size)
        self.setFixedSize(self.cols * cell_size, self.rows * cell_size)

    def on_cell_clicked(self, row, col):
        if self.selected_cell:
            prev_row, prev_col = self.selected_cell
            self.cells[prev_row][prev_col].clicked_state = False
            self.cells[prev_row][prev_col].update()

        cell = self.cells[row][col]
        cell.clicked_state = True
        cell.update()
        self.selected_cell = (row, col)
        self.cell_clicked.emit(row, col)


class CustomToolbar(NavigationToolbar2QT):
    def __init__(self, canvas, parent):
        super().__init__(canvas, parent)
        self.setIconSize(QSize(16, 16))
        # Set the icon color to white
        self.setStyleSheet("QToolButton { background-color: #ffffff; }")
        self.setStyleSheet("QToolBar { padding: 2px; }")


class GraphWidget(QWidget):
    subplot_clicked = pyqtSignal(int)

    def __init__(self, parent=None, width=5, height=4, dpi=100):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)

        self.figure = Figure(figsize=(width, height), dpi=dpi)
        self.canvas = FigureCanvas(self.figure)

        self.layout.addWidget(self.canvas)

        self.axes1 = self.figure.add_subplot(411)
        self.axes2 = self.figure.add_subplot(412, sharex=self.axes1)
        self.axes3 = self.figure.add_subplot(413, sharex=self.axes1)
        self.axes4 = self.figure.add_subplot(414, sharex=self.axes1)

        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.canvas.updateGeometry()

    def plot(self, x, y, title, xlabel, ylabel, axes):
        axes.clear()
        axes.plot(x, y)
        axes.set_title(title)
        axes.set_xlabel(xlabel)
        axes.set_ylabel(ylabel)
        axes.grid(True)
        self.canvas.draw()

    def set_xlim(self, left, right):
        self.axes1.set_xlim(left, right)
        self.canvas.draw()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.figure.tight_layout()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            print("Mouse clicked in plot")
            if event.y() < self.height() / 4:
                self.subplot_clicked.emit(0)
            elif event.y() < self.height() / 2:
                self.subplot_clicked.emit(1)
            elif event.y() < 3 * self.height() / 4:
                self.subplot_clicked.emit(2)
            else:
                self.subplot_clicked.emit(3)


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.file_path = None
        self.tolerance = 40
        self.recording_length = None
        self.time_vector = None
        self.data = None
        self.active_channels = None
        self.selected_channel = None
        self.selected_subplot = None

        self.setWindowTitle("Spatial SE Viewer")
        self.main_layout = QHBoxLayout()
        self.setLayout(self.main_layout)
        self.setFixedSize(1567, 832)

        self.left_pane = QWidget()
        self.left_layout = QVBoxLayout()
        self.left_pane.setLayout(self.left_layout)
        self.main_layout.addWidget(self.left_pane)

        self.grid_widget = GridWidget(64, 64)
        self.grid_widget.cell_clicked.connect(self.on_cell_clicked)
        self.left_layout.addWidget(self.grid_widget)

        self.right_pane = QWidget()
        self.right_layout = QVBoxLayout()
        self.right_pane.setLayout(self.right_layout)
        self.main_layout.addWidget(self.right_pane)

        self.graph_pane = QWidget()
        self.graph_layout = QVBoxLayout()
        self.graph_pane.setLayout(self.graph_layout)
        self.right_layout.addWidget(self.graph_pane)

        self.graph_widget = GraphWidget()
        self.graph_widget.subplot_clicked.connect(self.on_subplot_clicked)
        self.graph_layout.addWidget(self.graph_widget)

        self.toolbar = CustomToolbar(self.graph_widget.canvas, self)
        self.graph_layout.addWidget(self.toolbar)

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
        self.run_button.clicked.connect(self.run_analysis)
        self.control_layout.addWidget(self.run_button)

        self.clear_button = QPushButton("󰗨 Clear Plots")
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

        self.playback_timer = QTimer()
        self.playback_timer.timeout.connect(self.updatePlayback)

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
        self.progress_bar.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #999999;
                height: 8px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #B1B1B1, stop:1 #c4c4c4);
                margin: 2px 0;
            }

            QSlider::handle:horizontal {
                background: #ffffff;
                border: 1px solid #5c5c5c;
                width: 18px;
                margin: -2px 0;
                border-radius: 3px;
            }
        """)

        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["0.25", "0.5", "1", "2.0", "4.0", "8.0", "16.0"])
        self.playback_layout.addWidget(self.speed_combo)
        self.speed_combo.setCurrentIndex(2)
        self.speed_combo.currentIndexChanged.connect(self.setPlaybackSpeed)

        self.setWidgetsEnabled()

        # Start MATLAB engine
        self.eng = matlab.engine.start_matlab()
        self.eng.eval("parpool('Threads')", nargout=0)

    def keyPressEvent(self, event):
        if event.key() in [Qt.Key_1, Qt.Key_2, Qt.Key_3, Qt.Key_4]:
            if self.selected_channel is not None:
                row, col = self.selected_channel
                if self.data is not None:
                    if event.key() == Qt.Key_1:
                        self.graph_widget.plot(
                            self.time_vector,
                            self.data[row, col]["signal"],
                            f"Channel ({row + 1}, {col + 1})",
                            "",
                            "Amplitude",
                            self.graph_widget.axes1,
                        )
                    elif event.key() == Qt.Key_2:
                        self.graph_widget.plot(
                            self.time_vector,
                            self.data[row, col]["signal"],
                            f"Channel ({row + 1}, {col + 1})",
                            "",
                            "Amplitude",
                            self.graph_widget.axes2,
                        )
                    elif event.key() == Qt.Key_3:
                        self.graph_widget.plot(
                            self.time_vector,
                            self.data[row, col]["signal"],
                            f"Channel ({row + 1}, {col + 1})",
                            "",
                            "Amplitude",
                            self.graph_widget.axes3,
                        )
                    elif event.key() == Qt.Key_4:
                        self.graph_widget.plot(
                            self.time_vector,
                            self.data[row, col]["signal"],
                            f"Channel ({row + 1}, {col + 1})",
                            "Time (s)",
                            "Amplitude",
                            self.graph_widget.axes4,
                        )

                # Unselect the cell
                self.grid_widget.cells[row][col].clicked_state = False
                self.grid_widget.cells[row][col].update()
                self.selected_channel = None

    def on_cell_clicked(self, row, col):
        print(f"Cell clicked: ({row}, {col})")
        self.selected_channel = (row, col)

    def on_subplot_clicked(self, index):
        self.selected_subplot = index
        print(f"Subplot clicked: {index}")
        self.update_selected_subplot()

    def update_selected_subplot(self):
        print("Updating selected subplot")
        if self.selected_cell is not None and self.selected_subplot is not None:
            print(f"Selected cell: {self.selected_cell}")
            row, col = self.selected_cell
            if self.data is not None:
                if self.selected_subplot == 0:
                    self.graph_widget.plot(
                        self.time_vector,
                        self.data[row, col]["signal"],
                        f"Channel ({row + 1}, {col + 1})",
                        "",
                        "Amplitude",
                        self.graph_widget.axes1,
                    )
                elif self.selected_subplot == 1:
                    self.graph_widget.plot(
                        self.time_vector,
                        self.data[row, col]["signal"],
                        f"Channel ({row + 1}, {col + 1})",
                        "",
                        "Amplitude",
                        self.graph_widget.axes2,
                    )
                elif self.selected_subplot == 2:
                    self.graph_widget.plot(
                        self.time_vector,
                        self.data[row, col]["signal"],
                        f"Channel ({row + 1}, {col + 1})",
                        "",
                        "Amplitude",
                        self.graph_widget.axes3,
                    )
                elif self.selected_subplot == 3:
                    self.graph_widget.plot(
                        self.time_vector,
                        self.data[row, col]["signal"],
                        f"Channel ({row + 1}, {col + 1})",
                        "Time (s)",
                        "Amplitude",
                        self.graph_widget.axes4,
                    )

    def setWidgetsEnabled(self):
        if self.file_path is not None:
            self.run_button.setEnabled(True)
        else:
            self.run_button.setEnabled(False)

        if self.data is not None:
            self.clear_button.setEnabled(True)
            self.skip_backward_button.setEnabled(True)
            self.prev_frame_button.setEnabled(True)
            self.play_pause_button.setEnabled(True)
            self.next_frame_button.setEnabled(True)
            self.skip_forward_button.setEnabled(True)
            self.progress_bar.setEnabled(True)
            self.speed_combo.setEnabled(True)
        else:
            self.clear_button.setEnabled(False)
            self.skip_backward_button.setEnabled(False)
            self.prev_frame_button.setEnabled(False)
            self.play_pause_button.setEnabled(False)
            self.next_frame_button.setEnabled(False)
            self.skip_forward_button.setEnabled(False)
            self.progress_bar.setEnabled(False)
            self.speed_combo.setEnabled(False)

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

        self.setWidgetsEnabled()

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

            current_time = self.progress_bar.value() / 4

            if se_times:
                for timerange in se_times:
                    if len(timerange) == 1:
                        start = se_times[0][0]
                        stop = se_times[1][0]
                        if start <= current_time <= stop:
                            self.grid_widget.cells[row - 1][col - 1].setColor(SE)
                            found_se = True
                            break
                    else:
                        start, stop = timerange
                        if start <= current_time <= stop:
                            self.grid_widget.cells[row - 1][col - 1].setColor(SE)
                            found_se = True
                            break

            if found_se:
                continue

            if seizure_times:
                for timerange in seizure_times:
                    if len(timerange) == 1:
                        start = seizure_times[0][0]
                        stop = seizure_times[1][0]
                        if start <= current_time <= stop:
                            self.grid_widget.cells[row - 1][col - 1].setColor(SEIZURE)
                            found_seizure = True
                            break
                    else:
                        start, stop = timerange
                        if start <= current_time <= stop:
                            self.grid_widget.cells[row - 1][col - 1].setColor(SEIZURE)
                            found_seizure = True
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
        self.progress_bar.setRange(0, int(self.recording_length) * 4)

        print("Data shape:", self.data.shape)
        print("Total channels:", total_channels)
        print("Sampling rate:", sampling_rate)
        print("Number of recording frames:", num_rec_frames)
        print("Recording length:", self.recording_length)

        rows, cols = self.get_channels()
        self.active_channels = list(zip(rows, cols))

        self.create_grid()
        self.update_grid()

        # Plot graphs using Matplotlib
        self.graph_widget.plot(
            self.time_vector,
            self.data[60, 24]["signal"],
            "Channel (61, 25)",
            "",
            "Amplitude",
            self.graph_widget.axes1,
        )
        self.graph_widget.plot(
            self.time_vector,
            self.data[0, 1]["signal"],
            "Channel (1, 2)",
            "",
            "Amplitude",
            self.graph_widget.axes2,
        )
        self.graph_widget.plot(
            self.time_vector,
            self.data[1, 0]["signal"],
            "Channel (2, 1)",
            "",
            "Amplitude",
            self.graph_widget.axes3,
        )
        self.graph_widget.plot(
            self.time_vector,
            self.data[1, 1]["signal"],
            "Channel (2, 2)",
            "Time (s)",
            "Amplitude",
            self.graph_widget.axes4,
        )

        # Set x-axis limits
        self.graph_widget.set_xlim(0, self.recording_length)

        self.setWidgetsEnabled()

    def skipBackward(self):
        print("Skip Backward")
        next_index = self.progress_bar.value() - int(self.recording_length * 4 / 10)
        if next_index < 0:
            next_index = 0
        self.progress_bar.setValue(next_index)

    def prevFrame(self):
        print("Previous Frame")
        if self.progress_bar.value() > 0:
            self.progress_bar.setValue(self.progress_bar.value() - 1)
            self.update_grid()

    def playPause(self):
        if self.play_pause_button.text() == "":
            self.play_pause_button.setText("")
            print("Play")
            self.playback_timer.start(100)
        else:
            self.play_pause_button.setText("")
            print("Pause")
            self.playback_timer.stop()

    def updatePlayback(self):
        speed = float(self.speed_combo.currentText())
        skip_frames = int(
            speed * 4
        )  # Multiply speed by 4 to get the number of frames to skip

        current_value = self.progress_bar.value()
        next_value = current_value + skip_frames

        if next_value <= self.progress_bar.maximum():
            self.progress_bar.setValue(next_value)
        else:
            self.progress_bar.setValue(self.progress_bar.maximum())
            self.playback_timer.stop()
            self.play_pause_button.setText("")

    def nextFrame(self):
        print("Next Frame")
        if self.progress_bar.value() < self.progress_bar.maximum():
            self.progress_bar.setValue(self.progress_bar.value() + 1)
            self.update_grid()

    def skipForward(self):
        print("Skip Forward")
        next_index = self.progress_bar.value() + int(self.recording_length * 4 / 10)
        if next_index > self.progress_bar.maximum():
            next_index = self.progress_bar.maximum()
        self.progress_bar.setValue(next_index)

    def setPlaybackSpeed(self, index):
        interval = 100
        self.playback_timer.setInterval(interval)

    def seekPosition(self, value):
        print(f"Seek position: {value / 4}")  # Convert slider value to seconds
        self.update_grid()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    font = QFont("Hack Nerd Font Mono", 13)  # 10 is the font size, adjust as needed
    app.setFont(font)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
