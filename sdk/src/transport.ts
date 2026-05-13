import config from "./config";
import { logger } from "./utils";

export const sendEvent = async (payload: any): Promise<void> => {
    if (!config.initialized || !config.publicKey) {
        logger.error('SDK not initialized with a Public Key.');
        return;
    }

    const endpoint = `${config.baseUrl}/track`;

    try {
        fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-API-Key': config.publicKey,
            },
            body: JSON.stringify(payload),
            keepalive: true
        }).then((response) => {
            if (response.status === 202) {
                if (config.debug) logger.info(`Event sent: ${payload.event_type}`)
            } else if (response.status === 403) {
                logger.error('CORS Error: Origin not allowed');
            } else {
                logger.error(`Server returned ${response.status}: ${response.statusText}`)
            }
        })
    } catch (error) {
        logger.error(`Network error; ${error instanceof Error ? error.message : 'Unknown Error'}`)
    }
}