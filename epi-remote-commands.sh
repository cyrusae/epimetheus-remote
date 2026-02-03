#!/bin/bash
#
# Epimetheus Remote Command Wrapper
# This script restricts SSH commands to only safe operations
# Install on Epimetheus at: /usr/local/bin/epi-remote-commands.sh
#
# Usage:
#   1. Copy this script to Epimetheus: /usr/local/bin/epi-remote-commands.sh
#   2. Make it executable: chmod +x /usr/local/bin/epi-remote-commands.sh
#   3. Add to ~/.ssh/authorized_keys with command= restriction:
#      command="/usr/local/bin/epi-remote-commands.sh" ssh-ed25519 AAAA...
#

# Log all commands (optional, useful for debugging)
LOG_FILE="/var/log/epi-remote.log"
echo "$(date '+%Y-%m-%d %H:%M:%S') - Command: $SSH_ORIGINAL_COMMAND" >> "$LOG_FILE" 2>/dev/null

# Parse the command
case "$SSH_ORIGINAL_COMMAND" in
    # Soft refresh (F5) - quick reload without losing state
    "DISPLAY=:0 xdotool key F5")
        DISPLAY=:0 xdotool key F5
        ;;
    
    # Hard refresh (Ctrl+Shift+R) - clear cache
    "DISPLAY=:0 xdotool key ctrl+shift+r")
        DISPLAY=:0 xdotool key ctrl+shift+r
        ;;
    
    # Kiosk management (using existing ~/tv scripts)
    "bash ~/tv/restart-kiosk.sh")
        bash ~/tv/restart-kiosk.sh
        ;;
    
    "bash ~/tv/kiosk-status.sh")
        bash ~/tv/kiosk-status.sh
        ;;
    
    # Dashboard switching
    "bash ~/tv/switch-dashboard.sh morning")
        bash ~/tv/switch-dashboard.sh morning
        ;;
    
    "bash ~/tv/switch-dashboard.sh afternoon")
        bash ~/tv/switch-dashboard.sh afternoon
        ;;
    
    "bash ~/tv/switch-dashboard.sh evening")
        bash ~/tv/switch-dashboard.sh evening
        ;;
    
    "bash ~/tv/switch-dashboard.sh tv")
        bash ~/tv/switch-dashboard.sh tv
        ;;
    
    # TV control
    "bash ~/tv/tv-on.sh")
        bash ~/tv/tv-on.sh
        ;;
    
    "bash ~/tv/tv-off.sh")
        bash ~/tv/tv-off.sh
        ;;
    
    "bash ~/tv/dashboard-mode.sh")
        bash ~/tv/dashboard-mode.sh
        ;;
    
    # Firefox check
    "pgrep -x firefox")
        pgrep -x firefox
        ;;
    
    # Status checks
    'echo "alive"')
        echo "alive"
        ;;
    
    "uptime -p")
        uptime -p
        ;;
    
    "iwconfig wlp2s0 2>/dev/null | grep \"Signal level\" | awk '{print \$4}' | cut -d= -f2")
        iwconfig wlp2s0 2>/dev/null | grep "Signal level" | awk '{print $4}' | cut -d= -f2
        ;;
    
    "cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null")
        cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null
        ;;
    
    curl\ -s\ -o\ /dev/null\ -w\ *\ http*)
        # Allow curl health checks to local services
        eval "$SSH_ORIGINAL_COMMAND"
        ;;
    
    # K3s control (requires sudo to be configured)
    "sudo systemctl restart k3s-agent")
        sudo systemctl restart k3s-agent
        ;;
    
    # Reboot (requires sudo to be configured)
    "sudo reboot")
        sudo reboot
        ;;
    
    # Deny everything else
    *)
        echo "ERROR: Command not allowed: $SSH_ORIGINAL_COMMAND" >&2
        exit 1
        ;;
esac

exit $?