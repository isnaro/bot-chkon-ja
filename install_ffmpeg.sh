#!/bin/bash
# Download the latest static build of FFmpeg for Linux
wget https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz
# Extract the archive
tar -xvf ffmpeg-release-amd64-static.tar.xz
# Create a directory to store the binaries
mkdir -p ffmpeg
# Move the binaries to the ffmpeg directory
mv ffmpeg-*-amd64-static/ffmpeg ffmpeg/
mv ffmpeg-*-amd64-static/ffprobe ffmpeg/
# Set executable permissions
chmod +x ffmpeg/ffmpeg
chmod +x ffmpeg/ffprobe
# Clean up
rm -rf ffmpeg-*-amd64-static
rm ffmpeg-release-amd64-static.tar.xz
