// Tauri type declarations for the frontend
declare global {
  interface Window {
    __TAURI__?: {
      tauri: {
        invoke: (command: string, args?: any) => Promise<any>;
        event: {
          listen: (event: string, handler: (event: any) => void) => Promise<void>;
          emit: (event: string, payload?: any) => Promise<void>;
        };
      };
    };
  }
}

export {};