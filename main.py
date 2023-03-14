
import json

from PIL import Image, ImageDraw
from pathlib import Path
from enum import Enum
from rich.console import Console
from random import random

INPUT = Path("input")
OUTPUT = Path("output")
LOGS = Path("logs")
SETTINGS_FILE = Path("settings.json")

for folder in (INPUT, OUTPUT, LOGS):
	if not folder.exists():
		folder.mkdir()

if not SETTINGS_FILE.exists():
	json.dump(
		{
			"version": "1.0",
			"output file type": "png",
		},
		open(SETTINGS_FILE, "w", encoding="utf-8"),
		indent=4
	)

SETTINGS = json.load(open(SETTINGS_FILE, "r", encoding="utf-8"))

class EventsManager:

	def __init__(self):

		self.listeners = []

	def bind(self, listener):

		self.listeners.append(listener)

	def send_event(self, event: tuple):

		for listener in self.listeners:
			listener(event)

class Event(Enum):
	start_img_process = 0 # file
	output_crop = 1 # file
	done_img_process = 2 # file

class Locator:

	def __init__(self, events: EventsManager, out: Console):

		self.events: EventsManager = events
		self.out: Console = out

class EventEcho:

	def __init__(self, locator: Locator):
		
		self.locator = locator

	def event_handler(self, event):

		match event:
			case (Event.start_img_process, file):
				self.locator.out.print(f"[yellow]>>[/yellow] Traitement de [green]{file}[/green]")

			case (Event.output_crop, file):
				self.locator.out.print(f"[red]<<[/red] Trouvé [green]{file}[/green]")

class NeighborFinder:

	def __init__(self, width, height):

		self.width = width
		self.height = height

	def get(self, x, y):

		for nx, ny in self._get(x, y):
			if 0 <= nx < self.width and 0 <= ny < self.height:
				yield nx, ny

	def _get(self, x, y):

		yield x + 1, y
		yield x - 1, y
		yield x, y + 1
		yield x, y - 1

def find_bounding_boxes(data, width, height):
	
	left = set((x, y) for x in range(width) for y in range(height))
	neighbors = NeighborFinder(width, height)

	while left:
		x, y = left.pop()

		if data[x, y]:
			bag = [(x, y)]
			stack = [(nx, ny) for nx, ny in neighbors.get(x, y) if (nx, ny) in left]
			visited = set(stack)

			while stack:
				x, y = stack.pop()
				visited.add((x, y))

				if data[x, y]:
					bag.append((x, y))

					for nx, ny in neighbors.get(x, y):
						if (nx, ny) in left and (nx, ny) not in visited:
							stack.append((nx, ny))

				try:
					left.remove((x, y))

				except:
					pass

			xs = [x for x, _ in bag]
			ys = [y for _, y in bag]
			yield min(xs), min(ys), max(xs), max(ys)

def process_image(file: Path, output_folder: Path, locator: Locator):

	locator.events.send_event((Event.start_img_process, str(file)))
	existing_files = set(file.name for file in output_folder.iterdir())
	img = Image.open(file)
	width, height = img.size
	img = img.convert("RGBA")
	ImageDraw.floodfill(img, (1, 1), (0, 0, 0, 0), thresh=100)
	pixels = img.load()
	data = {(x, y): pixels[x, y][3] > 0 for x in range(width) for y in range(height)}

	for bounding_box in find_bounding_boxes(data, width, height):
		while (name := str(int(random()*10**10)) + "." + SETTINGS["output file type"]) in existing_files: continue
		img.crop(bounding_box).save(output_folder/name)
		existing_files.add(name)
		locator.events.send_event((Event.output_crop, str(output_folder/name)))

	locator.events.send_event((Event.done_img_process, str(file)))

def main():
	
	locator = Locator(EventsManager(), Console())
	event_echo = EventEcho(locator)
	locator.events.bind(event_echo.event_handler)

	for file in INPUT.iterdir():
		process_image(file, OUTPUT, locator)

if __name__ == "__main__":
	main()
