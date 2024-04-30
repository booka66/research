import tkinter as tk


class ChannelGrid:
    def __init__(self, parent):
        self.parent = parent
        self.window = tk.Toplevel(parent.window)
        self.window.title("Channel Selection")
        self.selected_channels = []

        # Create a canvas for drawing the selection shape
        self.canvas = tk.Canvas(self.window, width=640, height=640)
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self.start_selection)
        self.canvas.bind("<B1-Motion>", self.update_selection)
        self.canvas.bind("<ButtonRelease-1>", self.end_selection)
        self.window.bind(
            "<KeyPress-r>", self.reset_selection
        )  # Bind the "r" key event to the window

        # Draw the grid lines
        for i in range(64):
            self.canvas.create_line(i * 10, 0, i * 10, 640, fill="gray")
            self.canvas.create_line(0, i * 10, 640, i * 10, fill="gray")

        # Confirm button
        confirm_button = tk.Button(
            self.window, text="Confirm", command=self.confirm_selection
        )
        confirm_button.pack(pady=10)

    def start_selection(self, event):
        self.selection_points = [(event.x, event.y)]

    def reset_selection(self, event):
        self.canvas.delete("selection")
        self.canvas.delete("highlight")
        self.selection_points = []
        self.selected_channels = []

    def update_selection(self, event):
        self.selection_points.append((event.x, event.y))
        self.canvas.delete("selection")
        self.canvas.create_polygon(
            self.selection_points, fill="", outline="red", tags="selection"
        )

    def end_selection(self, event):
        self.selection_points.append((event.x, event.y))
        self.select_channels()

    def select_channels(self):
        self.canvas.delete("highlight")
        self.selected_channels = []
        for i in range(64):
            for j in range(64):
                if self.is_cell_enclosed(j * 10 + 5, i * 10 + 5):
                    self.selected_channels.append((i, j))
                    self.canvas.create_rectangle(
                        j * 10,
                        i * 10,
                        (j + 1) * 10,
                        (i + 1) * 10,
                        fill="red",
                        outline="",
                        tags="highlight",
                    )

    def is_cell_enclosed(self, x, y):
        polygon = self.selection_points
        inside = False
        j = len(polygon) - 1
        for i in range(len(polygon)):
            if ((polygon[i][1] > y) != (polygon[j][1] > y)) and (
                x
                < (polygon[j][0] - polygon[i][0])
                * (y - polygon[i][1])
                / (polygon[j][1] - polygon[i][1])
                + polygon[i][0]
            ):
                inside = not inside
            j = i
        return inside

    def confirm_selection(self):
        channels = [f"({i}, {j})" for i, j in self.selected_channels]
        self.parent.channel_input.set(", ".join(channels))
        self.window.destroy()
