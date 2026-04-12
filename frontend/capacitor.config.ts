import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.sapastats.app',
  appName: 'SAPA Stats',
  webDir: 'dist',
  server: {
    // En produccion, Capacitor carga desde el bundle local.
    // Si querés apuntar a un server remoto durante desarrollo:
    // url: 'http://192.168.x.x:5173',
    androidScheme: 'https',
  },
  android: {
    allowMixedContent: false,
  },
  plugins: {
    SplashScreen: {
      launchAutoHide: true,
      launchShowDuration: 1500,
      backgroundColor: '#2563EB',
    },
    StatusBar: {
      style: 'LIGHT',
      backgroundColor: '#FFFFFF',
    },
  },
};

export default config;
