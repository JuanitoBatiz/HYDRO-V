/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_MQTT_BROKER_URL: string;
  readonly VITE_MQTT_USER: string;
  readonly VITE_MQTT_PASS: string;
  readonly VITE_MQTT_TOPIC: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
