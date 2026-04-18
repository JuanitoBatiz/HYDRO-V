type MessageCallback = (data: any) => void;

export class WebSocketService {
  private ws: WebSocket | null = null;
  private url: string;
  private onMessage: MessageCallback | null = null;
  private reconnectInterval = 5000;
  private shouldReconnect = true;

  constructor(deviceCode: string) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = (window.location.hostname === 'localhost' || window.location.hostname === '192.168.68.67') ? '192.168.68.67:8000' : window.location.host;
    this.url = `${protocol}//${host}/api/v1/telemetry/ws/${deviceCode}`;
  }

  connect(token?: string) {
    this.shouldReconnect = true;
    const urlWithAuth = token ? `${this.url}?token=${token}` : this.url;
    
    this.ws = new WebSocket(urlWithAuth);

    this.ws.onopen = () => {
      console.log('✅ WebSocket Backend Connected');
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (this.onMessage) this.onMessage(data);
      } catch (e) {
        console.error('Error parsing WS message', e);
      }
    };

    this.ws.onclose = () => {
      console.warn('🔌 WebSocket Closed');
      if (this.shouldReconnect) {
        setTimeout(() => this.connect(token), this.reconnectInterval);
      }
    };

    this.ws.onerror = (err) => {
      console.error('🚨 WebSocket Error:', err);
    };
  }

  setMessageHandler(handler: MessageCallback) {
    this.onMessage = handler;
  }

  disconnect() {
    this.shouldReconnect = false;
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}
