# Epimetheus Remote - Setup Checklist

Quick reference for setting up the remote control panel.

## Pre-Deployment Checklist

### On Your Laptop

- [ ] Generate SSH key pair
  ```bash
  ssh-keygen -t ed25519 -f ~/epimetheus-remote-key -C "epimetheus-remote"
  ```

### On Epimetheus

- [ ] Copy public key to Epimetheus
  ```bash
  ssh-copy-id -i ~/epimetheus-remote-key.pub cyrus@epimetheus
  ```

- [ ] Install command wrapper script
  ```bash
  # On Epimetheus
  sudo nano /usr/local/bin/epi-remote-commands.sh
  # Paste contents of epi-remote-commands.sh
  sudo chmod +x /usr/local/bin/epi-remote-commands.sh
  ```

- [ ] Configure SSH key restriction
  ```bash
  nano ~/.ssh/authorized_keys
  # Add command="/usr/local/bin/epi-remote-commands.sh" before the key
  # Example:
  # command="/usr/local/bin/epi-remote-commands.sh" ssh-ed25519 AAAA... epimetheus-remote
  ```

- [ ] Install xdotool
  ```bash
  sudo apt-get update && sudo apt-get install -y xdotool
  ```

- [ ] (Optional) Configure passwordless sudo
  ```bash
  sudo visudo
  # Add at end:
  # cyrus ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart k3s-agent
  # cyrus ALL=(ALL) NOPASSWD: /usr/sbin/reboot
  ```

- [ ] Test SSH connection from laptop
  ```bash
  ssh -i ~/epimetheus-remote-key cyrus@epimetheus "echo alive"
  # Should see: alive
  ```

### Build and Deploy

- [ ] Edit k8s-deployment.yaml with base64-encoded SSH private key
  ```bash
  cat ~/epimetheus-remote-key | base64 -w 0
  # Copy output and paste into k8s-deployment.yaml
  ```

- [ ] Build and push Docker image
  ```bash
  docker build -t registry.dawnfire.casa/epimetheus-remote:latest .
  docker push registry.dawnfire.casa/epimetheus-remote:latest
  ```

- [ ] Deploy to Kubernetes
  ```bash
  kubectl apply -f k8s-deployment.yaml
  ```

- [ ] Wait for certificate to be issued
  ```bash
  kubectl get certificate -n control-panel
  # Wait for READY = True
  ```

- [ ] Test the service
  ```bash
  curl https://remote.dawnfire.casa
  # Should see HTML
  ```

## Testing Checklist

- [ ] Status page loads
- [ ] Epimetheus shows as Online
- [ ] Firefox shows as Running
- [ ] "Refresh (F5)" button works
- [ ] "Hard Refresh" button works
- [ ] "Restart Firefox" works (TV goes blank briefly)
- [ ] "View Logs" shows Firefox logs
- [ ] Status auto-refreshes every 30 seconds

## Troubleshooting Steps

### Pod won't start
```bash
kubectl logs -n control-panel -l app=epimetheus-remote
kubectl describe pod -n control-panel -l app=epimetheus-remote
```

### SSH connection fails
```bash
# Exec into pod and test SSH
kubectl exec -it -n control-panel deployment/epimetheus-remote -- sh
ssh -i /ssh-key/id_ed25519 cyrus@epimetheus "echo test"
```

### xdotool doesn't work
```bash
# On Epimetheus, test directly
DISPLAY=:0 xdotool key F5
# Check Firefox is on DISPLAY :0
echo $DISPLAY
ps aux | grep firefox
```

### Certificate won't issue
```bash
# Check certificate status
kubectl describe certificate epimetheus-remote-tls -n control-panel
# Check cert-manager logs
kubectl logs -n cert-manager -l app=cert-manager
# Delete and recreate
kubectl delete certificate epimetheus-remote-tls -n control-panel
kubectl apply -f k8s-deployment.yaml
```

## Quick Commands

```bash
# View logs
kubectl logs -n control-panel -l app=epimetheus-remote -f

# Restart deployment
kubectl rollout restart deployment/epimetheus-remote -n control-panel

# Check status
kubectl get pods,svc,ingress,certificate -n control-panel

# Delete everything
kubectl delete namespace control-panel

# Redeploy from scratch
kubectl apply -f k8s-deployment.yaml
```

## Success Criteria

✅ Can access https://remote.dawnfire.casa from phone  
✅ Status shows Epimetheus online  
✅ Refresh button makes Firefox reload  
✅ Hard refresh clears cache  
✅ Restart Firefox works  
✅ Logs are viewable  
✅ Status auto-refreshes  

## Post-Deployment

- [ ] Bookmark on phone
- [ ] Add to home screen for app-like experience
- [ ] Test from bed (the real use case!)
- [ ] Show Martin how to use it
- [ ] Update GLOBAL - Current State docs