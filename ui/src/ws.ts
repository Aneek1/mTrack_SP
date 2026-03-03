import type { ClientControlMessage, ServerState } from "./types";

type OnState = (state: ServerState) => void;
type OnStatus = (status: { connected: boolean; message?: string }) => void;

export class BackendWS {
  private ws: WebSocket | null = null;
  private url: string;
  private onState: OnState;
  private onStatus: OnStatus;
  private reconnectTimer: number | null = null;
  private shouldReconnect = true;

  constructor(opts: { url: string; onState: OnState; onStatus: OnStatus }) {
    this.url = opts.url;
    this.onState = opts.onState;
    this.onStatus = opts.onStatus;
  }

  connect(): void {
    this.shouldReconnect = true;
    this._connectOnce();
  }

  close(): void {
    this.shouldReconnect = false;
    if (this.reconnectTimer !== null) {
      window.clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.ws?.close();
    this.ws = null;
  }

  send(msg: ClientControlMessage): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;
    this.ws.send(JSON.stringify(msg));
  }

  private _connectOnce(): void {
    this.onStatus({ connected: false, message: `Connecting to ${this.url}...` });
    const ws = new WebSocket(this.url);
    this.ws = ws;

    ws.onopen = () => {
      this.onStatus({ connected: true, message: "Connected" });
    };

    ws.onmessage = (evt) => {
      try {
        const data = JSON.parse(String(evt.data)) as ServerState;
        if (data && data.type === "state") this.onState(data);
      } catch {
        // ignore malformed messages
      }
    };

    ws.onclose = () => {
      this.onStatus({ connected: false, message: "Disconnected" });
      this.ws = null;
      if (!this.shouldReconnect) return;
      this.reconnectTimer = window.setTimeout(() => this._connectOnce(), 800);
    };

    ws.onerror = () => {
      this.onStatus({ connected: false, message: "WebSocket error" });
    };
  }
}

