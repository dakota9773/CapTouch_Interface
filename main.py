import tkinter as tk
from tkinter import Canvas, ttk, simpledialog, filedialog
import serial
import threading
import collections
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import time
import csv
import datetime

# Your existing constants and global variables here

SERIAL_PORT = 'COM22'
BAUD_RATE = 9600
DELTA_THRESHOLD1 = 10
BUFFER_SIZE = 2
DATA_POINTS = 40

diff_data = [collections.deque(maxlen=DATA_POINTS) for _ in range(12)]
timestamps = collections.deque(maxlen=DATA_POINTS)

delta1_counter = 0
delta2_counter = 0
delta1_timer = 0
delta2_timer = 0
delta1_start_time = None
delta2_start_time = None
delta1_touch_detected = False
delta2_touch_detected = False

# Variables to store the latest Delta values and timestamp
latest_delta1 = 0.0
latest_delta2 = 0.0
latest_timestamp = ""
saving = False
save_thread = None
data_queue = collections.deque()

def moving_average(buffer, new_value):
    buffer.append(new_value)
    if len(buffer) > BUFFER_SIZE:
        buffer.pop(0)
    return sum(buffer) / len(buffer)

def read_from_serial(ser, canvas, delta1_text, delta2_text, circle1, circle2, ax, fig, counter1_text, counter2_text, timer1_text, timer2_text, delta1_index, delta2_index, graph_indices):
    global delta1_counter, delta2_counter, delta1_timer, delta2_timer, delta1_start_time, delta2_start_time
    global delta1_touch_detected, delta2_touch_detected, latest_delta1, latest_delta2, latest_timestamp
    buffers = [collections.deque(maxlen=BUFFER_SIZE) for _ in range(12)]
    while True:
        try:
            line = ser.readline().decode('utf-8').strip()
            values = list(map(float, line.split(',')))
            if len(values) == 24:
                deltas = []
                for i in range(0, 24, 2):
                    deltas.append(values[i] - values[i+1])
                smoothed_deltas = [moving_average(buffers[i], deltas[i]) for i in range(12)]
                delta1 = smoothed_deltas[delta1_index]
                delta2 = smoothed_deltas[delta2_index]
                canvas.itemconfig(delta1_text, text=f"Delta 1 (E{delta1_index:02}): {delta1:.2f}")
                canvas.itemconfig(delta2_text, text=f"Delta 2 (E{delta2_index:02}): {delta2:.2f}")

                # Update latest delta values and timestamp
                latest_delta1 = round(delta1, 2)
                latest_delta2 = round(delta2, 2)
                latest_timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                # Touch detection for Delta 1
                if delta1 > DELTA_THRESHOLD1:
                    canvas.itemconfig(circle1, fill='green', outline='dark green')
                    if not delta1_touch_detected:
                        delta1_touch_detected = True
                        delta1_counter += 1
                        delta1_start_time = time.time()
                elif delta1 <= DELTA_THRESHOLD1:
                    canvas.itemconfig(circle1, fill='blue', outline='dark blue')
                    if delta1_touch_detected:
                        delta1_touch_detected = False
                        delta1_timer += time.time() - delta1_start_time

                # Touch detection for Delta 2
                if delta2 > DELTA_THRESHOLD1:
                    canvas.itemconfig(circle2, fill='green', outline='dark green')
                    if not delta2_touch_detected:
                        delta2_touch_detected = True
                        delta2_counter += 1
                        delta2_start_time = time.time()
                elif delta2 <= DELTA_THRESHOLD1:
                    canvas.itemconfig(circle2, fill='orange', outline='dark orange')
                    if delta2_touch_detected:
                        delta2_touch_detected = False
                        delta2_timer += time.time() - delta2_start_time

                # Update the counters and timers on the canvas
                canvas.itemconfig(counter1_text, text=f"Object 1 Count: {delta1_counter}")
                canvas.itemconfig(counter2_text, text=f"Object 2 Count: {delta2_counter}")
                canvas.itemconfig(timer1_text, text=f"Object 1 Timer: {delta1_timer:.2f} sec")
                canvas.itemconfig(timer2_text, text=f"Object 2 Timer: {delta2_timer:.2f} sec")

                timestamps.append(time.time())
                for i in range(12):
                    diff_data[i].append(smoothed_deltas[i])
                ax.clear()
                full_colors = ['blue', 'orange', 'green', 'red', 'purple', 'brown', 'pink', 'gray', 'olive', 'cyan', 'magenta', 'black']
                color_map = {delta1_index: 'blue', delta2_index: 'orange'}
                for i in graph_indices:
                    ax.plot(timestamps, diff_data[i], color=color_map.get(i, full_colors[i]), label=f'E{i:02}')
                ax.legend(loc='upper right')
                ax.set_title("Deltas over Time")
                ax.set_ylim([-10, 10])
                ax.spines['top'].set_visible(False)
                ax.spines['right'].set_visible(False)
                ax.spines['bottom'].set_visible(False)
                ax.spines['left'].set_visible(False)
                ax.tick_params(axis='both', which='both', length=0, labelbottom=False, labelleft=False)
                fig.autofmt_xdate()
                fig.canvas.draw()
            else:
                canvas.itemconfig(delta1_text, text="Invalid data format")
                canvas.itemconfig(delta2_text, text="Invalid data format")
        except serial.SerialException as e:
            canvas.itemconfig(delta1_text, text=f"Error: {e}")
            canvas.itemconfig(delta2_text, text=f"Error: {e}")
            break
        except ValueError:
            canvas.itemconfig(delta1_text, text="Invalid data values")
        except IndexError:
            canvas.itemconfig(delta1_text, text="Index error occurred")

def start_serial_reading(canvas, delta1_text, delta2_text, circle1, circle2, ax, fig, counter1_text, counter2_text, timer1_text, timer2_text, delta1_index, delta2_index, graph_indices):
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE)
        thread = threading.Thread(target=read_from_serial, args=(ser, canvas, delta1_text, delta2_text, circle1, circle2, ax, fig, counter1_text, counter2_text, timer1_text, timer2_text, delta1_index, delta2_index, graph_indices))
        thread.daemon = True
        thread.start()
    except serial.SerialException as e:
        canvas.itemconfig(delta1_text, text=f"Error: {e}")
        canvas.itemconfig(delta2_text, text=f"Error: {e}")

def ask_electrode_indices():
    window = tk.Tk()
    window.title("Select Electrodes")

    tk.Label(window, text="Select electrode number for Object 1:").pack()
    delta1_var = tk.StringVar()
    delta1_menu = ttk.Combobox(window, textvariable=delta1_var)
    delta1_menu['values'] = [f"E{str(i).zfill(2)}" for i in range(12)]
    delta1_menu.pack()

    tk.Label(window, text="Select electrode number for Object 2:").pack()
    delta2_var = tk.StringVar()
    delta2_menu = ttk.Combobox(window, textvariable=delta2_var)
    delta2_menu['values'] = [f"E{str(i).zfill(2)}" for i in range(12)]
    delta2_menu.pack()

    def on_submit():
        delta1_index = int(delta1_var.get()[1:])
        delta2_index = int(delta2_var.get()[1:])
        window.destroy()
        main(delta1_index, delta2_index)

    tk.Button(window, text="Submit", command=on_submit).pack()
    window.mainloop()

def toggle_saving():
    global saving, save_thread, data_queue, start_time, delta1_counter, delta2_counter, delta1_timer, delta2_timer

    if saving:
        saving = False
        save_button.config(text="Start Saving")
        file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if file_path:
            with open(file_path, mode="w", newline="") as file:
                writer = csv.writer(file)
                writer.writerow(["Timestamp", "Elapsed Time (s)", "Delta 1", "Object 1 Count", "Object 1 Timer", "Delta 2", "Object 2 Count", "Object 2 Timer"])
                while data_queue:
                    writer.writerow(data_queue.popleft())
        print("Stopped saving data.")
    else:
        saving = True
        start_time = time.time()  # Record the start time
        data_queue = collections.deque()  # Clear the queue before starting
        save_button.config(text="Stop Saving")
        save_thread = threading.Thread(target=save_data_continuous)
        save_thread.start()
        print("Started saving data.")

def save_data_continuous():
    global saving, latest_timestamp, latest_delta1, latest_delta2, start_time, data_queue, delta1_counter, delta2_counter, delta1_timer, delta2_timer
    while saving:
        elapsed_time = time.time() - start_time
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data_queue.append([timestamp, f"{elapsed_time:.2f}", f"{latest_delta1:.2f}", delta1_counter, f"{delta1_timer:.2f}", f"{latest_delta2:.2f}", delta2_counter, f"{delta2_timer:.2f}"])
        time.sleep(0.1)

def initialize_gui(delta1_index, delta2_index):
    root = tk.Tk()
    root.title("Serial Data Reader")

    canvas = Canvas(root, width=1000, height=500)
    canvas.pack(padx=10, pady=10)

    circle1 = canvas.create_oval(200, 50, 450, 300, outline="dark blue", width=2, fill="blue")
    circle2 = canvas.create_oval(550, 50, 800, 300, outline="dark orange", width=2, fill="orange")

    delta1_text = canvas.create_text(325, 175, text="Delta 1: ", font=("Helvetica", 16))
    delta2_text = canvas.create_text(675, 175, text="Delta 2: ", font=("Helvetica", 16))

    counter1_text = canvas.create_text(325, 400, text="Object 1 Count: 0", font=("Helvetica", 16))
    counter2_text = canvas.create_text(675, 400, text="Object 2 Count: 0", font=("Helvetica", 16))

    timer1_text = canvas.create_text(325, 450, text="Object 1 Timer: 0.00 sec", font=("Helvetica", 16))
    timer2_text = canvas.create_text(675, 450, text="Object 2 Timer: 0.00 sec", font=("Helvetica", 16))

    # Add save button
    global save_button
    save_button = tk.Button(root, text="Start Saving", command=toggle_saving)
    save_button.pack()

    fig, ax = plt.subplots(figsize=(5, 4))
    ax.set_title("Deltas over Time")
    colors = ['blue', 'orange']
    for i, color in enumerate(colors):
        ax.plot([], [], color=color, label=f'E{i:02}')
    ax.legend(loc='upper right')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.tick_params(axis='both', which='both', length=0, labelbottom=False, labelleft=False)
    ax.set_ylim([-10, 10])

    canvas_plot = FigureCanvasTkAgg(fig, master=root)
    canvas_plot.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

    graph_indices = [delta1_index, delta2_index]

    start_serial_reading(canvas, delta1_text, delta2_text, circle1, circle2, ax, fig, counter1_text, counter2_text, timer1_text, timer2_text, delta1_index, delta2_index, graph_indices)
    return root

def main(delta1_index=None, delta2_index=None):
    if delta1_index is None or delta2_index is None:
        ask_electrode_indices()
    else:
        root = initialize_gui(delta1_index, delta2_index)
        root.mainloop()

if __name__ == "__main__":
    main()
