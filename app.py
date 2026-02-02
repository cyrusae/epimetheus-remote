#!/usr/bin/env python3
"""
Epimetheus Remote - Control panel for bedroom TV node
Simple Flask app to manage Epimetheus from your phone
"""

from flask import Flask, render_template, jsonify, request
from functools import wraps
import subprocess
import time
import os

app = Flask(__name__)

# Configuration
EPIMETHEUS_HOST = os.getenv('EPIMETHEUS_HOST', 'epimetheus')
SSH_KEY_PATH = os.getenv('SSH_KEY_PATH', '/root/.ssh/id_ed25519')
DASHBOARD_URL = os.getenv('DASHBOARD_URL', 'http://morning.dawnfire.casa')

# Basic auth (optional - set via env vars)
AUTH_ENABLED = os.getenv('AUTH_ENABLED', 'false').lower() == 'true'
AUTH_USERNAME = os.getenv('AUTH_USERNAME', 'admin')
AUTH_PASSWORD = os.getenv('AUTH_PASSWORD', 'changeme')

# Store last action for UI feedback
last_action = {
    'message': 'Ready',
    'timestamp': time.time(),
    'success': True
}


def check_auth():
    """Check if basic auth is required and valid"""
    if not AUTH_ENABLED:
        return True
    
    auth = request.authorization
    return auth and auth.username == AUTH_USERNAME and auth.password == AUTH_PASSWORD


def requires_auth(f):
    """Decorator for routes that need auth"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not check_auth():
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated


def ssh_command(command, timeout=10):
    """Execute command on Epimetheus via SSH"""
    try:
        result = subprocess.run(
            ['ssh', '-i', SSH_KEY_PATH, '-o', 'ConnectTimeout=5', 
             '-o', 'StrictHostKeyChecking=no', EPIMETHEUS_HOST, command],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return {
            'success': result.returncode == 0,
            'stdout': result.stdout.strip(),
            'stderr': result.stderr.strip(),
            'returncode': result.returncode
        }
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'stdout': '',
            'stderr': 'Command timed out',
            'returncode': -1
        }
    except Exception as e:
        return {
            'success': False,
            'stdout': '',
            'stderr': str(e),
            'returncode': -1
        }


def update_last_action(message, success=True):
    """Update the last action status"""
    global last_action
    last_action = {
        'message': message,
        'timestamp': time.time(),
        'success': success
    }


# ============================================================================
# Web Routes
# ============================================================================

@app.route('/')
def index():
    """Main control panel page"""
    return render_template('index.html')


# ============================================================================
# Display Control API
# ============================================================================

@app.route('/api/refresh', methods=['POST'])
@requires_auth
def refresh_dashboard():
    """Soft refresh - F5"""
    result = ssh_command('DISPLAY=:0 xdotool key F5')
    
    if result['success']:
        update_last_action('Dashboard refreshed (F5)')
        return jsonify({'status': 'ok', 'message': 'Dashboard refreshed'})
    else:
        update_last_action(f'Refresh failed: {result["stderr"]}', False)
        return jsonify({'status': 'error', 'message': result['stderr']}), 500


@app.route('/api/hard-refresh', methods=['POST'])
@requires_auth
def hard_refresh_dashboard():
    """Hard refresh - Ctrl+Shift+R"""
    result = ssh_command('DISPLAY=:0 xdotool key ctrl+shift+r')
    
    if result['success']:
        update_last_action('Hard refresh (cleared cache)')
        return jsonify({'status': 'ok', 'message': 'Hard refresh complete'})
    else:
        update_last_action(f'Hard refresh failed: {result["stderr"]}', False)
        return jsonify({'status': 'error', 'message': result['stderr']}), 500


@app.route('/api/restart-firefox', methods=['POST'])
@requires_auth
def restart_firefox():
    """Restart Firefox via systemd"""
    result = ssh_command('systemctl --user restart firefox-dashboard.service || pkill -9 firefox')
    
    if result['success']:
        update_last_action('Firefox restarted')
        return jsonify({'status': 'ok', 'message': 'Firefox restarted'})
    else:
        update_last_action(f'Firefox restart failed: {result["stderr"]}', False)
        return jsonify({'status': 'error', 'message': result['stderr']}), 500


@app.route('/api/switch-dashboard', methods=['POST'])
@requires_auth
def switch_dashboard():
    """Switch to a different dashboard URL"""
    data = request.get_json()
    url = data.get('url', DASHBOARD_URL)
    
    # Navigate Firefox to new URL using xdotool
    commands = [
        'DISPLAY=:0 xdotool key ctrl+l',  # Focus address bar
        f'DISPLAY=:0 xdotool type "{url}"',  # Type URL
        'DISPLAY=:0 xdotool key Return'  # Press Enter
    ]
    
    for cmd in commands:
        result = ssh_command(cmd)
        if not result['success']:
            update_last_action(f'Switch failed: {result["stderr"]}', False)
            return jsonify({'status': 'error', 'message': result['stderr']}), 500
        time.sleep(0.5)  # Small delay between commands
    
    update_last_action(f'Switched to {url}')
    return jsonify({'status': 'ok', 'message': f'Switched to {url}'})


# ============================================================================
# Health Check API
# ============================================================================

@app.route('/api/status')
def get_status():
    """Get overall status of Epimetheus"""
    status = {
        'epimetheus_alive': False,
        'firefox_running': False,
        'dashboard_reachable': False,
        'uptime': None,
        'wifi_signal': None,
        'cpu_temp': None,
        'firefox_pid': None
    }
    
    # Check if Epimetheus is reachable
    ping_result = ssh_command('echo "alive"', timeout=5)
    status['epimetheus_alive'] = ping_result['success']
    
    if not status['epimetheus_alive']:
        return jsonify(status)
    
    # Check Firefox
    firefox_check = ssh_command('pgrep -x firefox')
    if firefox_check['success'] and firefox_check['stdout']:
        status['firefox_running'] = True
        status['firefox_pid'] = firefox_check['stdout']
    
    # Get uptime
    uptime_result = ssh_command('uptime -p')
    if uptime_result['success']:
        status['uptime'] = uptime_result['stdout']
    
    # Get WiFi signal (if wireless)
    wifi_result = ssh_command('iwconfig wlp2s0 2>/dev/null | grep "Signal level" | awk \'{print $4}\' | cut -d= -f2')
    if wifi_result['success'] and wifi_result['stdout']:
        status['wifi_signal'] = wifi_result['stdout']
    
    # Get CPU temp
    temp_result = ssh_command('cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null')
    if temp_result['success'] and temp_result['stdout']:
        try:
            temp_c = int(temp_result['stdout']) / 1000
            status['cpu_temp'] = f"{temp_c:.1f}°C"
        except:
            pass
    
    # Check if dashboard is reachable from Epimetheus
    curl_result = ssh_command(f'curl -s -o /dev/null -w "%{{http_code}}" {DASHBOARD_URL}', timeout=10)
    if curl_result['success'] and curl_result['stdout'] == '200':
        status['dashboard_reachable'] = True
    
    return jsonify(status)


@app.route('/api/last-action')
def get_last_action():
    """Get the last action performed"""
    return jsonify(last_action)


# ============================================================================
# Advanced Controls API
# ============================================================================

@app.route('/api/logs', methods=['GET'])
@requires_auth
def get_logs():
    """Get recent Firefox logs"""
    result = ssh_command('journalctl --user -u firefox-dashboard -n 20 --no-pager')
    
    if result['success']:
        return jsonify({
            'status': 'ok',
            'logs': result['stdout'].split('\n')
        })
    else:
        return jsonify({
            'status': 'error',
            'message': result['stderr']
        }), 500


@app.route('/api/restart-k3s', methods=['POST'])
@requires_auth
def restart_k3s():
    """Restart K3s agent"""
    result = ssh_command('sudo systemctl restart k3s-agent', timeout=30)
    
    if result['success']:
        update_last_action('K3s agent restarted')
        return jsonify({'status': 'ok', 'message': 'K3s agent restarted'})
    else:
        update_last_action(f'K3s restart failed: {result["stderr"]}', False)
        return jsonify({'status': 'error', 'message': result['stderr']}), 500


@app.route('/api/reboot', methods=['POST'])
@requires_auth
def reboot_epimetheus():
    """Reboot Epimetheus (dangerous!)"""
    # Add confirmation check
    data = request.get_json()
    if not data or data.get('confirmed') != True:
        return jsonify({
            'status': 'error',
            'message': 'Reboot requires confirmation'
        }), 400
    
    # Fire and forget - system will reboot
    ssh_command('sudo reboot', timeout=5)
    
    update_last_action('Epimetheus rebooting...')
    return jsonify({'status': 'ok', 'message': 'Reboot initiated'})


# ============================================================================
# Health Check for K8s
# ============================================================================

@app.route('/health')
def health():
    """Health check endpoint for Kubernetes"""
    return jsonify({'status': 'healthy'}), 200


if __name__ == '__main__':
    # Development mode
    app.run(host='0.0.0.0', port=5000, debug=False)