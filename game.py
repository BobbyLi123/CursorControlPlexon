from pyopxclient import PyOPXClientAPI, OPX_ERROR_NOERROR
import tkinter as tk
import random
import time
import collections
from collections import deque
import threading

class Game:
    def __init__(self, client, num_groups, groups, up_group, down_group, time_slot_duration):
        self.root = tk.Tk()
        self.root.geometry("800x600")
        self.start_button = tk.Button(self.root, text="Start", command=self.start_game)
        self.start_button.pack()
        self.cursor = tk.Canvas(self.root, width=800, height=600, bg='white')
        self.cursor.pack()
        self.cursor_position = 300  # Set the initial cursor position to the middle of the screen
        self.target_position = None  # The target position will be set when the game starts
        self.start_time = None
        self.client = client
        self.num_groups = num_groups
        self.groups = groups
        self.up_group = up_group
        self.down_group = down_group
        self.time_slot_duration = time_slot_duration
        self.group_spike_densities = {group: deque(maxlen=10) for group in range(1, num_groups + 1)}
        self.speeds = collections.deque(maxlen=100)  # Store the last 100 speeds
        self.last_move_time = time.time()
        self.end_text = None
        self.cursor_item = None
        self.target = None
        self.running = False
        self.thread = None

    def start_game(self):
        self.running = True
        if self.cursor_item is not None:
            self.cursor.delete(self.cursor_item)
        if self.target is not None:
            self.cursor.delete(self.target)
        if self.end_text is not None:
            self.cursor.delete(self.end_text)
            self.end_text = None
        self.start_button.pack_forget()
        self.start_time = time.time()
        # Set the target position to a random position either above or below the cursor
        if random.choice([True, False]):
            self.target_position = random.randint(0, max(int(self.cursor_position - 20), 0))
        else:
            self.target_position = random.randint(int(self.cursor_position + 20), 600)
        self.cursor_item = self.cursor.create_polygon(400, self.cursor_position, 390, self.cursor_position + 20, 410, self.cursor_position + 20, fill='blue')
        self.target = self.cursor.create_oval(395, self.target_position, 405, self.target_position + 10, fill='red')
        if self.thread is not None and self.thread.is_alive():
            self.running = False
            self.thread.join()
        self.thread = threading.Thread(target=self.move_cursor_continuous)
        self.thread.start()

    def move_cursor_continuous(self):
        while self.running:
            self.move_cursor()
            # time.sleep(0.1)  # Adjust this value to control the speed of the cursor

    def move_cursor(self):
        while self.running:
            group_timestamps = {group: [] for group in range(1, self.num_groups+1)}
            group_channels = {group: set() for group in range(1, self.num_groups+1)}
            avg_spike_density = {group: 0 for group in range(1, self.num_groups+1)}
            time.sleep(self.time_slot_duration/1000.0)
            new_data = self.client.get_new_data(timestamps_only=True)
            for i in range(new_data.num_timestamps):
                unit = new_data.unit[i]
                for group, units in self.groups.items():
                    if unit in units:
                        group_timestamps[group].append(new_data.timestamp[i])
                        group_channels[group].add(new_data.channel[i])
            for group, timestamps in group_timestamps.items():
                duration = self.time_slot_duration / 1000.0
                num_channels = max(len(group_channels[group]), 1)
                # print("Number of group_channels: ", num_channels)
                spike_density = len(timestamps) / (num_channels * duration)
                # print ("Spike density for group {}: {} Hz".format(group, spike_density))
                self.group_spike_densities[group].append(spike_density)
                avg_spike_density[group] = sum(self.group_spike_densities[group]) / len(self.group_spike_densities[group])
            # print("Group Spike Densities: ", self.group_spike_densities)
            # print("Up Group: ", self.up_group)
            density_difference = avg_spike_density[self.up_group] - avg_spike_density[self.down_group]
            speed = abs(density_difference) * 10  # Calculate the speed
            self.speeds.append(speed)  # Add the speed to the deque
            average_speed = sum(self.speeds) / len(self.speeds)  # Calculate the average speed
            speed_scaling_factor = 10 / average_speed if average_speed != 0 else 1  # Adjust the scaling factor based on the average speed
            print("current time:", time.time()-self.start_time)
            print("spike density for up group: ", avg_spike_density[self.up_group])
            print("spike density for down group: ", avg_spike_density[self.down_group])
            if density_difference > 0:
                self.cursor_position = max(self.cursor_position - speed * speed_scaling_factor, 0)  # Move up
                print("Moving up with speed: ", speed)
            else:
                self.cursor_position = min(self.cursor_position + speed * speed_scaling_factor, 600)  # Move down
                print("Moving down with speed: ", speed)
            self.cursor.delete(self.cursor_item)
            self.cursor_item = self.cursor.create_polygon(400, self.cursor_position, 390, self.cursor_position + 20, 410, self.cursor_position + 20, fill='blue')
            if abs(self.cursor_position - self.target_position) <= 10:
                self.end_game()
                self.running = False
                time.sleep(1)  # Wait for 1 second


    def end_game(self):
        self.running = False
        end_time = time.time()
        time_spent = end_time - self.start_time
        self.cursor.delete(self.target)
        self.end_text = self.cursor.create_text(400, 300, text=f"Target Reached! You spent {time_spent} seconds!", fill='green')
        self.root.after(1000, self.start_game)  # Schedule start_game to be called after 1 second

if __name__ == "__main__":
    client = PyOPXClientAPI()
    client.connect()
    if not client.connected:
        print ("Client isn't connected, exiting.\n")
        print ("Error code: {}\n".format(client.last_result))
        exit()
    num_groups = int(input("Enter the number of groups: "))
    groups = {}
    for i in range(num_groups):
        units = input("Enter the units for group {}, separated by commas: ".format(i+1)).split(',')
        units = [int(unit) for unit in units]
        groups[i+1] = units
    up_group = int(input("Enter the group number that controls moving up: "))
    down_group = int(input("Enter the group number that controls moving down: "))
    time_slot_duration = 1000  
    # print(up_group, down_group)
    game = Game(client, num_groups, groups, up_group, down_group, time_slot_duration)
    game.root.mainloop()