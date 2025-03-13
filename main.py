
import tkinter as tk
from tkinter import Canvas
import serial
import threading
import collections
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import time

SERIAL_PORT = 'COM22'
BAUD_RATE = 9600
DELTA_THRESHOLD1 = 10
BUFFER_SIZE = 2
DATA_POINTS = 40

delta1_data = collections.deque(maxlen=DATA_POINTS)
delta2_data = collections.deque(maxlen=DATA_POINTS)
timestamps = collections.deque(maxlen=DATA_POINTS)

delta1_counter = 0
delta2_counter = 0
delta1_timer = 0
delta2_timer = 0
delta1_start_time = None
delta2_start_time = None
delta1_touch_detected = False
delta2_touch_detected = False

def moving_average(buffer, new_value):
    buffer.append(new_value)
    if len(buffer) > BUFFER_SIZE:
        buffer.pop(0)
    return sum(buffer) / len(buffer)

def read_from_serial(ser, canvas, delta1_text, delta2_text, circle1, circle2, ax, fig, counter1_text, counter2_text, timer1_text, timer2_text):
    global delta1_counter, delta2_counter, delta1_timer, delta2_timer, delta1_start_time, delta2_start_time
    global delta1_touch_detected, delta2_touch_detected
    buffer1 = collections.deque(maxlen=BUFFER_SIZE)
    buffer2 = collections.deque(maxlen=BUFFER_SIZE)

    while True:
        try:
            line = ser.readline().decode('utf-8').strip()
            values = line.split(',')

            if len(values) == 4:
                value1 = float(values[0])
                value2 = float(values[1])
                value3 = float(values[2])
                value4 = float(values[3])
                delta1 = value1 - value2
                delta2 = value3 - value4

                smoothed_delta1 = moving_average(buffer1, delta1)
                smoothed_delta2 = moving_average(buffer2, delta2)

                canvas.itemconfig(delta1_text, text=f"Delta 1: {smoothed_delta1:.2f}")
                canvas.itemconfig(delta2_text, text=f"Delta 2: {smoothed_delta2:.2f}")

                if smoothed_delta1 >= DELTA_THRESHOLD1:
                    canvas.itemconfig(circle1, fill="green")
                    if not delta1_touch_detected:
                        delta1_counter += 1
                        delta1_touch_detected = True
                        if delta1_start_time is None:
                            delta1_start_time = time.time()
                else:
                    canvas.itemconfig(circle1, fill="orange")
                    if delta1_touch_detected:
                        delta1_timer += time.time() - delta1_start_time
                        delta1_start_time = None
                        delta1_touch_detected = False

                if smoothed_delta2 >= DELTA_THRESHOLD1:
                    canvas.itemconfig(circle2, fill="green")
                    if not delta2_touch_detected:
                        delta2_counter += 1
                        delta2_touch_detected = True
                        if delta2_start_time is None:
                            delta2_start_time = time.time()
                else:
                    canvas.itemconfig(circle2, fill="blue")
                    if delta2_touch_detected:
                        delta2_timer += time.time() - delta2_start_time
                        delta2_start_time = None
                        delta2_touch_detected = False

                canvas.itemconfig(counter1_text, text=f"Object 1 Count: {delta1_counter}")
                canvas.itemconfig(counter2_text, text=f"Object 2 Count: {delta2_counter}")
                canvas.itemconfig(timer1_text, text=f"Object 1 Timer: {delta1_timer:.2f} sec")
                canvas.itemconfig(timer2_text, text=f"Object 2 Timer: {delta2_timer:.2f} sec")

                timestamps.append(time.time())
                delta1_data.append(smoothed_delta1)
                delta2_data.append(smoothed_delta2)

                ax.clear()
                ax.plot(timestamps, delta1_data, color='orange', label='Delta1')
                ax.plot(timestamps, delta2_data, color='blue', label='Delta2')
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
            canvas.itemconfig(delta2_text, text="Invalid data values")

def start_serial_reading(canvas, delta1_text, delta2_text, circle1, circle2, ax, fig, counter1_text, counter2_text, timer1_text, timer2_text):
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE)
        thread = threading.Thread(target=read_from_serial, args=(ser, canvas, delta1_text, delta2_text, circle1, circle2, ax, fig, counter1_text, counter2_text, timer1_text, timer2_text))
        thread.daemon = True
        thread.start()
    except serial.SerialException as e:
        canvas.itemconfig(delta1_text, text=f"Error: {e}")
        canvas.itemconfig(delta2_text, text=f"Error: {e}")

def initialize_gui():
    root = tk.Tk()
    root.title("Serial Data Reader")
    canvas = Canvas(root, width=1000, height=500)
    canvas.pack(padx=10, pady=10)

    circle1 = canvas.create_oval(200, 50, 450, 300, outline="dark orange", width=2, fill="orange")
    circle2 = canvas.create_oval(550, 50, 800, 300, outline="dark blue", width=2, fill="blue")

    delta1_text = canvas.create_text(325, 175, text="Delta 1: ", font=("Helvetica", 16))
    delta2_text = canvas.create_text(675, 175, text="Delta 2: ", font=("Helvetica", 16))
    counter1_text = canvas.create_text(325, 400, text="Object 1 Count: 0", font=("Helvetica", 16))
    counter2_text = canvas.create_text(675, 400, text="Object 2 Count: 0", font=("Helvetica", 16))
    timer1_text = canvas.create_text(325, 450, text="Object 1 Timer: 0.00 sec", font=("Helvetica", 16))
    timer2_text = canvas.create_text(675, 450, text="Object 2 Timer: 0.00 sec", font=("Helvetica", 16))

    fig, ax = plt.subplots(figsize=(5, 4))
    ax.set_title("Deltas over Time")
    ax.plot(delta1_data, color='orange', label='Delta1')
    ax.plot(delta2_data, color='blue', label='Delta2')
    ax.legend(loc='upper right')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.tick_params(axis='both', which='both', length=0, labelbottom=False, labelleft=False)
    ax.set_ylim([-10, 10])

    canvas_plot = FigureCanvasTkAgg(fig, master=root)
    canvas_plot.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

    start_serial_reading(canvas, delta1_text, delta2_text, circle1, circle2, ax, fig, counter1_text, counter2_text, timer1_text, timer2_text)

    return root

def main():
    root = initialize_gui()
    root.mainloop()

if __name__ == "__main__":
    main()

