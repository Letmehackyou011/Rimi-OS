#!/bin/bash

# AI Security Research OS - Live-Build Script
# Usage: sudo ./build.sh

set -e

echo "🚀 Building AI Security Research OS..."
echo "======================================"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
  echo "❌ This script must be run as root (use: sudo ./build.sh)"
  exit 1
fi

# Check if live-build is installed
if ! command -v lb &> /dev/null; then
  echo "📦 Installing live-build..."
  apt update
  apt install -y live-build
fi

# Create project directory
PROJECT_DIR="security-os-build"
if [ ! -d "$PROJECT_DIR" ]; then
  mkdir -p "$PROJECT_DIR"
  cd "$PROJECT_DIR"
else
  cd "$PROJECT_DIR"
fi

# Clean previous builds
echo "🧹 Cleaning previous builds..."
lb clean --all 2>/dev/null || true

# Configure
echo "⚙️ Configuring live-build..."
./auto/config

# Copy package lists
echo "📝 Adding package lists..."
mkdir -p config/package-lists

cat > config/package-lists/standard.list.chroot << 'EOF'
# Standard packages
build-essential
curl
git
wget
nano
vim
htop
net-tools
openssh-client
openssh-server

# Python development
python3
python3-dev
python3-pip
python3-venv

# Database
postgresql
postgresql-contrib

# Development tools
git
gcc
g++
make
cmake

# System tools
screen
tmux
supervisor
systemd
EOF

cat > config/package-lists/security-tools.list.chroot << 'EOF'
# Security research tools
nmap
wireshark
tcpdump
tshark
curl
wget
git
sqlmap
hydra
john
hashcat
aircrack-ng
hashlib

# Penetration testing
metasploit-framework

# Vulnerability databases
vulnhub

# Additional security tools
openssl
openssh-client
openssh-server
gnutls-bin
EOF

cat > config/package-lists/gui.list.chroot << 'EOF'
# Graphical interface
task-xfce-desktop
lightdm
xfce4
firefox
mousepad

# Browser tools
curl
wget
git
EOF

cat > config/package-lists/development.list.chroot << 'EOF'
# Development environment
git
build-essential
python3-dev
node-pre-gyp
npm

# Code editors
vim
nano
code

# Version control
git
gitk
github-cli
EOF

# Copy includes (files to add to ISO)
echo "📂 Preparing includes..."
mkdir -p config/includes.chroot/opt/security-os
mkdir -p config/includes.chroot/home

# Add welcome message
cat > config/includes.chroot/etc/issue << 'EOF'
╔════════════════════════════════════════════════╗
║  🔒 AI Security Research Operating System     ║
║                                                ║
║  Welcome to the automated security testing    ║
║  platform powered by artificial intelligence  ║
║                                                ║
║  Documentation: /opt/security-os/README.md    ║
║  Backend API: http://localhost:8000/docs      ║
║  Frontend Dashboard: http://localhost:5173    ║
╚════════════════════════════════════════════════╝

EOF

# Build the ISO
echo "🔨 Building ISO image..."
echo "This may take 15-30 minutes..."

lb build 2>&1 | tee build.log

# Check if build was successful
if [ $? -eq 0 ]; then
  echo ""
  echo "✅ Build completed successfully!"
  echo "📦 ISO image created:"
  ls -lh live-image-amd64.hybrid.iso
  echo ""
  echo "📝 Next steps:"
  echo "1. Copy ISO to USB: sudo dd if=live-image-amd64.hybrid.iso of=/dev/sdX bs=4M"
  echo "2. Or test in VM: qemu-system-x86_64 -cdrom live-image-amd64.hybrid.iso -m 4096"
  echo "3. Boot and login (username: user, no password initially)"
else
  echo ""
  echo "❌ Build failed. Check build.log for details."
  echo "Common issues:"
  echo "- Not enough disk space (need ~20GB free)"
  echo "- Network issues downloading packages"
  echo "- Missing permissions or dependencies"
  exit 1
fi

echo ""
echo "======================================"
echo "Build completed!"
echo "======================================"
