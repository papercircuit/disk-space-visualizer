Disk Space Visualizer
A simple real-time disk space monitoring tool that displays your macOS disk usage over time in a graphical interface.
!Disk Space Monitor Screenshot
Prerequisites
This app requires Python 3 and a few Python packages. Here's how to get everything set up on your Mac:
1. Install Python 3
If you don't have Python 3 installed, the easiest way is to use Homebrew:

# Install Homebrew if you don't have it
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python 3
brew install python3

To verify Python 3 is installed:

python3 --version

2. Install Required Packages
Install the required Python packages using pip3:

pip3 install psutil matplotlib

Running the App
Clone or download this repository
Open Terminal
Navigate to the project directory:

cd path/to/disk-space-visualizer

4. Run the script:

python3 disk_monitor.py

Features
Real-time disk usage monitoring
Graphical display showing usage percentage over time
Auto-scaling graph
Updates every second
Stores last 100 data points
Troubleshooting
If you get any "command not found" errors:
Make sure Python 3 is installed: python3 --version
Make sure pip3 is installed: pip3 --version
Try reinstalling the required packages: pip3 install --upgrade psutil matplotlib
License
MIT License - feel free to modify and use as needed!
Contributing
Feel free to open issues or submit pull requests if you have suggestions for improvements!
