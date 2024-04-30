import tkinter as tk
from tkinter import filedialog


class DataProcessingGUI:
    def __init__(self, process_data_callback):
        self.process_data_callback = process_data_callback
        self.window = tk.Tk()
        self.window.title("Data Processing")

        # File path input
        self.file_path = tk.StringVar()
        file_button = tk.Button(
            self.window, text="Select File", command=self.select_file
        )
        file_button.pack()
        self.file_label = tk.Label(self.window, textvariable=self.file_path)
        self.file_label.pack()

        # Sampling rate and recording length labels
        self.sampling_rate_label = tk.Label(self.window, text="")
        self.sampling_rate_label.pack()
        self.recording_length_label = tk.Label(self.window, text="")
        self.recording_length_label.pack()

        # Channel input
        channel_label = tk.Label(
            self.window,
            text="Enter the channels as comma-separated pairs (row, column):",
        )
        channel_label.pack()
        self.channel_input = tk.Entry(self.window)
        self.channel_input.pack()

        # Channel verification
        channel_verify_label = tk.Label(
            self.window, text="Verify the channels (row, column):"
        )
        channel_verify_label.pack()
        self.channel_verify = tk.Entry(self.window)
        self.channel_verify.pack()

        # Downsampling input
        downsample_label = tk.Label(
            self.window,
            text="Enter the downsampling frequency (or 'n' for no downsampling):",
        )
        downsample_label.pack()
        self.downsample_input = tk.Entry(self.window)
        self.downsample_input.pack()

        # Recorder name input
        recorder_label = tk.Label(self.window, text="Enter your name:")
        recorder_label.pack()
        self.recorder_name = tk.Entry(self.window)
        self.recorder_name.pack()

        # Paradigm input
        paradigm_label = tk.Label(self.window, text="Enter the paradigm:")
        paradigm_label.pack()
        self.paradigm_input = tk.Entry(self.window)
        self.paradigm_input.pack()

        # Brain region input
        brain_region_label = tk.Label(self.window, text="Enter the brain region:")
        brain_region_label.pack()
        self.brain_region = tk.Entry(self.window)
        self.brain_region.pack()

        # Process button
        process_button = tk.Button(
            self.window, text="Process Data", command=self.process_data
        )
        process_button.pack()

        # Result label
        self.result_label = tk.Label(self.window, text="")
        self.result_label.pack()

    def select_file(self):
        self.file_path.set(filedialog.askopenfilename())
        self.process_data_callback("file_selected", self.file_path.get())

    def process_data(self):
        data = {
            "file_path": self.file_path.get(),
            "channel_input": self.channel_input.get(),
            "channel_verify": self.channel_verify.get(),
            "downsample_input": self.downsample_input.get(),
            "recorder_name": self.recorder_name.get(),
            "paradigm": self.paradigm_input.get(),
            "brain_region": self.brain_region.get(),
        }
        self.process_data_callback("process_data", data)

    def update_labels(self, sampling_rate, recording_length):
        self.sampling_rate_label.config(text=f"Original Sampling Rate: {sampling_rate}")
        self.recording_length_label.config(
            text=f"Recording Length: {recording_length} seconds"
        )

    def show_result(self, result):
        self.result_label.config(text=result)

    def run(self):
        self.window.mainloop()


def process_data_callback(event, data):
    if event == "file_selected":
        print(f"File selected: {data}")
    elif event == "process_data":
        print(f"Processing data: {data}")


DataProcessingGUI(process_data_callback).run()
