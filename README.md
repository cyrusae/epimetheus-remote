# 🛏️ Epimetheus Remote

Control your bedroom TV node from your phone! A simple Flask app deployed to K3s that gives you remote control over Epimetheus and its Firefox dashboard.

## Features

✅ **Soft Refresh** (F5) - Quick refresh without losing state  
✅ **Hard Refresh** (Ctrl+Shift+R) - Clear cache and reload  
✅ **Restart Firefox** - When the browser gets stuck  
✅ **Switch Dashboard** - Navigate to different URLs  
✅ **Status Monitoring** - Check if everything is alive  
✅ **View Logs** - See what Firefox is doing  
✅ **Restart K3s Agent** - Fix cluster connectivity issues  
✅ **Reboot Node** - Nuclear option with confirmation  

## Setup Instructions

### Step 1: Generate SSH Key Pair

On Epimetheus:

```bash
# Generate a dedicated SSH key for the remote control
ssh-keygen -t ed25519 -f ~/epimetheus-remote-key -C "epimetheus-remote"

# This creates two files:
# - epimetheus-remote-key (private key, stays on K3s cluster)
# - epimetheus-remote-key.pub (public key, goes on Epimetheus)
```

### Step 2: Install SSH Key on Epimetheus

Cnfigure it with command restrictions:

```bash
# Copy public key to Epimetheus
ssh-copy-id -i ~/epimetheus-remote-key.pub cyrus@epimetheus

# SSH into Epimetheus
ssh epimetheus

# Install the command wrapper script
sudo curl -o /usr/local/bin/epi-remote-commands.sh \
  https://raw.githubusercontent.com/YOUR_REPO/epimetheus-remote/main/epi-remote-commands.sh
sudo chmod +x /usr/local/bin/epi-remote-commands.sh

# Edit ~/.ssh/authorized_keys to add command restriction
# Find the line with your new key and add command="" at the beginning:
nano ~/.ssh/authorized_keys

# Change this:
# ssh-ed25519 AAAA... epimetheus-remote

# To this:
# command="/usr/local/bin/epi-remote-commands.sh" ssh-ed25519 AAAA... epimetheus-remote

# Save and exit
```

**Optional: Allow passwordless sudo for k3s and reboot**

If you want to enable K3s restart and reboot commands:

```bash
# On Epimetheus, edit sudoers
sudo visudo

# Add these lines at the end:
cyrus ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart k3s-agent
cyrus ALL=(ALL) NOPASSWD: /usr/sbin/reboot
```

### Step 3: Install xdotool on Epimetheus

xdotool is needed to send keyboard commands to Firefox:

```bash
# SSH into Epimetheus
ssh epimetheus

# Install xdotool
sudo apt-get update
sudo apt-get install -y xdotool
```

### Step 4: Build and Push Docker Image

On your laptop:

```bash
# Navigate to the project directory
cd /path/to/epimetheus-remote

# Build the Docker image
docker build -t registry.dawnfire.casa/epimetheus-remote:latest .

# Push to your registry
docker push registry.dawnfire.casa/epimetheus-remote:latest
```

### Step 5: Create Kubernetes Secret with SSH Key

```bash
# Base64 encode the private key
cat ~/epimetheus-remote-key | base64 -w 0

# Copy the output, then edit k8s-deployment.yaml
# Replace REPLACE_WITH_BASE64_ENCODED_PRIVATE_KEY with your encoded key
nano k8s-deployment.yaml
```

### Step 6: Deploy to Kubernetes

```bash
# Apply the manifests
kubectl apply -f k8s-deployment.yaml

# Check deployment status
kubectl get pods -n control-panel

# Check if the pod is running
kubectl logs -n control-panel -l app=epimetheus-remote

# Check if the Ingress got a certificate
kubectl get certificate -n control-panel

# Test the service
curl https://remote.dawnfire.casa
```

### Step 7: Access from Your Phone

1. Open your phone's browser
2. Navigate to: `https://remote.dawnfire.casa`
3. Bookmark it for easy access
4. You can also "Add to Home Screen" for an app-like experience

## Usage

### From Your Phone

**Quick Actions:**
- Tap "🔄 Refresh (F5)" for a soft refresh
- Tap "🔁 Hard Refresh" to clear cache
- Tap "🔴 Restart Firefox" if the browser is stuck

**Advanced Controls:**
- Expand "Advanced Controls" section
- Change URL to switch between dashboards
- View logs to debug issues
- Restart K3s if cluster is unhappy
- Reboot Epimetheus (requires confirmation)

**Status Monitoring:**
- Status card shows if Epimetheus is online
- Green dots = healthy
- Red dots = problems
- Auto-refreshes every 30 seconds

### From Command Line (Testing)

Test the Flask app locally before deploying:

```bash
# Set up environment
export EPIMETHEUS_HOST=epimetheus
export SSH_KEY_PATH=~/epimetheus-remote-key
export DASHBOARD_URL=http://morning.dawnfire.casa

# Run the app
python app.py

# In another terminal, test the API
curl http://localhost:5000/api/status
curl -X POST http://localhost:5000/api/refresh
```

## Configuration

All configuration is via environment variables in `k8s-deployment.yaml`:

```yaml
env:
- name: EPIMETHEUS_HOST
  value: "epimetheus"  # Hostname or IP
- name: SSH_KEY_PATH
  value: "/ssh-key/id_ed25519"  # Path to mounted SSH key
- name: DASHBOARD_URL
  value: "http://morning.dawnfire.casa"  # Default dashboard
- name: AUTH_ENABLED
  value: "false"  # Set to "true" to enable basic auth
```

### Enabling Authentication

If you want to add basic auth (username/password):

1. Create a secret with your password:

```bash
kubectl create secret generic epimetheus-remote-auth \
  --namespace=control-panel \
  --from-literal=password='your-secure-password'
```

2. Uncomment the auth environment variables in `k8s-deployment.yaml`:

```yaml
- name: AUTH_ENABLED
  value: "true"
- name: AUTH_USERNAME
  value: "admin"
- name: AUTH_PASSWORD
  valueFrom:
    secretKeyRef:
      name: epimetheus-remote-auth
      key: password
```

3. Redeploy:

```bash
kubectl apply -f k8s-deployment.yaml
kubectl rollout restart deployment/epimetheus-remote -n control-panel
```

## Troubleshooting

### App won't connect to Epimetheus

```bash
# Check if the pod can reach Epimetheus
kubectl exec -it -n control-panel deployment/epimetheus-remote -- sh
ping epimetheus
ssh -i /ssh-key/id_ed25519 epimetheus "echo alive"
```

### SSH key permission denied

```bash
# Check SSH key permissions on Epimetheus
ssh epimetheus
cat ~/.ssh/authorized_keys | grep epimetheus-remote
# Should have: command="/usr/local/bin/epi-remote-commands.sh" at the start

# Test the wrapper script directly
/usr/local/bin/epi-remote-commands.sh
```

### Firefox commands not working

```bash
# Make sure xdotool is installed
ssh epimetheus
which xdotool

# Test xdotool manually
DISPLAY=:0 xdotool key F5

# Check if DISPLAY=:0 is correct
echo $DISPLAY
ps aux | grep firefox
```

### SSL certificate issues

```bash
# Check certificate status
kubectl get certificate -n control-panel
kubectl describe certificate epimetheus-remote-tls -n control-panel

# If stuck, delete and recreate
kubectl delete certificate epimetheus-remote-tls -n control-panel
kubectl delete secret epimetheus-remote-tls -n control-panel
kubectl delete ingress epimetheus-remote -n control-panel
kubectl apply -f k8s-deployment.yaml
```

## Security Notes

✅ **SSH Key Restrictions**: The SSH key can only execute whitelisted commands  
✅ **No Shell Access**: The wrapper script prevents arbitrary command execution  
✅ **Optional Auth**: Basic auth can be enabled for the web interface  
✅ **Logging**: All SSH commands are logged to `/var/log/epi-remote.log` on Epimetheus  
⚠️ **Local Network Only**: Currently accessible via Tailscale/local network  

## Future Enhancements

Ideas for future versions:

- [ ] Add more dashboard presets (morning, afternoon, evening, TV mode)
- [ ] Integration with Home Assistant for bedroom lights
- [ ] View btop/system stats from Epimetheus
- [ ] Control other services (Nextcloud restart, etc.)
- [ ] Telegram bot interface for Martin
- [ ] Auto-detect if Firefox crashed and restart it
- [ ] Schedule dashboard switches (morning→evening automatically)

## File Structure

```
epimetheus-remote/
├── app.py                      # Flask application
├── templates/
│   └── index.html              # Mobile-optimized UI
├── Dockerfile                  # Container image
├── requirements.txt            # Python dependencies
├── k8s-deployment.yaml         # Kubernetes manifests
├── epi-remote-commands.sh      # SSH command wrapper for Epimetheus
└── README.md                   # This file
```

## Contributing

This is a personal homelab project, but feel free to adapt it for your own use!

## License

MIT - Use it however you want!

---

**Author**: Cyrus  
**Node**: Epimetheus (bedroom TV display)  
**Purpose**: Because hauling out the laptop in bed is annoying
