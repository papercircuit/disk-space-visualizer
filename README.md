# Disk Space Visualizer

A real-time disk space monitoring tool that displays your macOS disk usage over time in a graphical interface.

## Prerequisites

This app requires Python 3 and a few Python packages. Here's how to get everything set up on your Mac:

### 1. Install Python 3
If you don't have Python 3 installed, the easiest way is to use Homebrew:

Install Homebrew if you don't have it:
`/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"`

Install Python 3:
`brew install python3`

Verify Python 3 is installed:
`python3 --version`

### 2. Install Required Packages
Install the required Python packages using pip3:
`pip3 install psutil pyqtgraph PyQt6`

### 3. Docker Setup (Optional)
If you want to monitor Docker containers, make sure Docker Desktop for Mac is installed and running.

## Running the App

1. Clone or download this repository
2. Open Terminal
3. Navigate to the project directory:
   `cd path/to/disk-space-visualizer`
4. Run the script:
   `python3 disk_monitor.py`

## Usage

- Click anywhere on the graph to add a reference point (up to 5)
- Click existing reference points to remove them
- Hover over the graph to see exact values
- Use the Reset button or File menu to clear all data
- Mac users can use Cmd+Q to quit

## Troubleshooting

If you get any "command not found" errors:
- Make sure Python 3 is installed: `python3 --version`
- Make sure pip3 is installed: `pip3 --version`
- Try reinstalling the required packages: `pip3 install --upgrade psutil matplotlib`
- For Docker monitoring issues, ensure Docker Desktop is running

## License

MIT License - feel free to modify and use as needed!

## Contributing

Feel free to open issues or submit pull requests if you have suggestions for improvements!
