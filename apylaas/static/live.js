const host = `${window.location.protocol}//${window.location.hostname}`;
const socketUrl = `ws://${window.location.hostname}:5678`;
const webSocket = new WebSocket(socketUrl);

webSocket.onmessage = () => {
  window.location.reload();
};
