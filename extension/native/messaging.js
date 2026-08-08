/**
 * Extension Native Messaging Client
 * Connects to downloader-agent via Chrome/Edge Native Messaging port
 */

const NATIVE_HOST_NAME = "com.omikalix.ytdownloader";

export class NativeMessagingClient {
  constructor() {
    this.port = null;
    this.callbacks = new Map();
    this.eventListeners = new Set();
    this.isConnected = false;
    this.requestCounter = 0;
  }

  connect() {
    if (this.port) {
      return this.port;
    }

    try {
      this.port = chrome.runtime.connectNative(NATIVE_HOST_NAME);
      this.isConnected = true;

      this.port.onMessage.addListener((message) => {
        this.handleMessage(message);
      });

      this.port.onDisconnect.addListener(() => {
        const error = chrome.runtime.lastError;
        const reason = error ? error.message : "Native agent host disconnected";
        this.isConnected = false;
        this.port = null;
        this.notifyDisconnect(reason);
      });
    } catch (err) {
      this.isConnected = false;
      this.port = null;
      this.notifyDisconnect(err.message || "Connection failed");
    }
    return this.port;
  }

  sendRequest(action, payload = {}, timeoutMs = 60000) {
    if (!this.port) {
      this.connect();
    }

    if (!this.port) {
      return Promise.reject(new Error("Native agent host unavailable"));
    }

    const reqId = `req_${++this.requestCounter}_${Date.now()}`;
    const message = {
      id: reqId,
      action: action,
      payload: payload,
    };

    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        if (this.callbacks.has(reqId)) {
          this.callbacks.delete(reqId);
          reject(new Error(`Native messaging request for '${action}' timed out`));
        }
      }, timeoutMs);

      this.callbacks.set(reqId, {
        action: action,
        resolve: (data) => {
          clearTimeout(timer);
          resolve(data);
        },
        reject: (err) => {
          clearTimeout(timer);
          reject(err);
        }
      });

      try {
        this.port.postMessage(message);
      } catch (err) {
        clearTimeout(timer);
        this.callbacks.delete(reqId);
        this.port = null;
        this.isConnected = false;
        reject(err);
      }
    });
  }

  handleMessage(message) {
    if (!message) return;

    const reqId = message.id;
    const event = message.event;
    const payload = message.payload || {};

    // Broadcast streaming event updates (e.g. progress)
    this.eventListeners.forEach((listener) => {
      try {
        listener(message);
      } catch (e) {}
    });

    if (reqId && this.callbacks.has(reqId)) {
      const cb = this.callbacks.get(reqId);

      if (event === "error") {
        cb.reject(new Error(payload.message || payload.code || "Operation failed"));
        this.callbacks.delete(reqId);
      } else if (event === "download_started" || event === "status" || event === "formats" || event === "pong" || event === "cancelled") {
        // Resolve request promise on confirmation events
        cb.resolve(payload);
        this.callbacks.delete(reqId);
      }
    }
  }

  addEventListener(listener) {
    this.eventListeners.add(listener);
  }

  removeEventListener(listener) {
    this.eventListeners.delete(listener);
  }

  notifyDisconnect(reason) {
    for (const [reqId, { reject }] of this.callbacks.entries()) {
      try {
        reject(new Error(reason || "Native agent disconnected"));
      } catch (e) {}
    }
    this.callbacks.clear();

    this.eventListeners.forEach((listener) => {
      try {
        listener({ event: "disconnected", payload: { reason } });
      } catch (e) {}
    });
  }
}

export const nativeClient = new NativeMessagingClient();
