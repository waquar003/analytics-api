interface SDKConfig {
    publicKey: string | null;
    baseUrl: string;
    version: string;
    initialized: boolean;
    debug: boolean;
}

const config: SDKConfig = {
    publicKey: null, 
    baseUrl: 'http://localhost:8000',
    version: '1.0.0',
    initialized: false,
    debug: false
};

export default config;